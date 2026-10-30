# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""FingerVision 型センサの合成と、公開基準/力学ベース読み取りの小さな比較器。

合成の真値は :class:`Truth` にだけ置き、推定器へ渡すのは RGB 像と較正値だけである。
Hertz と Cattaneo--Mindlin は既存 ``tacsim`` / ``tacslip`` を利用する。カメラは
180 degree 等距離射影を平面格子へ適用した近似で、実画像の再現器ではない。
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math

import numpy as np

import tacsim
import tacslip

WIDTH, HEIGHT, FPS = 320, 240, 30.0
E_GEL, NU, THICKNESS = 0.18e6, 0.48, 4e-3
R_INDENTER, MU = 12e-3, 0.65
MM_PER_PX = 35.0 / WIDTH
MARKER_PITCH_PX = 5.0 / MM_PER_PX
MARKER_RADIUS_PX = 0.5 / MM_PER_PX


@dataclass(frozen=True)
class Truth:
    """評価専用の真値。推定 API はこの型を受け取らない。"""

    force_N: tuple[float, float, float]
    torque_Nm: float = 0.0
    slip: bool = False
    slip_dir: tuple[float, float] = (0.0, 0.0)
    proximity: bool = False
    angle_deg: float = 0.0


@dataclass
class Calibration:
    reference: np.ndarray
    marker_reference: np.ndarray
    baseline_coef: np.ndarray = field(default_factory=lambda: np.ones(3))
    physics_coef: np.ndarray = field(default_factory=lambda: np.ones(4))
    previous: np.ndarray | None = None
    baseline_bg: np.ndarray | None = None
    mog2: object | None = None
    hs_hist: np.ndarray | None = None
    use_cv2: bool = True
    marker_dark: float = 0.78
    marker_radius_px: float = MARKER_RADIUS_PX
    marker_pitch_px: float = MARKER_PITCH_PX


def _fisheye_points() -> np.ndarray:
    xs = np.arange(23.0, WIDTH - 20.0, MARKER_PITCH_PX)
    ys = np.arange(20.0, HEIGHT - 18.0, MARKER_PITCH_PX)
    xx, yy = np.meshgrid(xs, ys)
    p = np.column_stack([xx.ravel(), yy.ravel()])
    c = np.array([(WIDTH - 1) / 2, (HEIGHT - 1) / 2])
    q = p - c
    r = np.linalg.norm(q, axis=1)
    # equidistant: r = f theta; the mild radial term is the planar inverse approximation.
    scale = np.sinc(np.minimum(r / 205.0, 0.88))
    return c + q * scale[:, None]


MARKERS = _fisheye_points()


def _background(color: str, brightness: float, phase: float, deform: bool, moving_bg: bool) -> np.ndarray:
    yy, xx = np.mgrid[:HEIGHT, :WIDTH]
    phase_bg = phase * 13.0 if moving_bg else 0.0
    bg = np.stack([
        0.55 + 0.12 * np.sin((xx + phase_bg) / 21),
        0.62 + 0.10 * np.cos((yy + phase_bg) / 17),
        0.68 + 0.08 * np.sin((xx + yy) / 29),
    ], -1)
    palette = {"black": (0.025, 0.025, 0.025), "skin": (0.78, 0.55, 0.42), "bright": (0.95, 0.72, 0.12)}
    cx = 160 + 7 * phase
    rx = 74 * (1 + (0.12 * math.sin(phase) if deform else 0))
    mask = ((xx - cx) / rx) ** 2 + ((yy - 120) / 64) ** 2 < 1
    texture = 0.06 * np.sin((xx - phase * 9) / 8) * np.cos(yy / 11)
    obj = np.asarray(palette[color])[None, None, :] + texture[..., None]
    return np.clip(np.where(mask[..., None], obj, bg) * brightness, 0, 1)


def synthesize(truth: Truth, *, color: str = "bright", brightness: float = 1.0,
               phase: float = 0.0, deform: bool = False, moving_bg: bool = False,
               seed: int = 0) -> np.ndarray:
    """真値から 320x240 RGB 像を作る。XP-565 相当 E=0.18 MPa は Smooth-On の
    XP-565 technical bulletin (Shore A 16, tensile modulus 0.18 MPa) による近似値。"""
    fx, fy, fz = truth.force_N
    bg = _background(color, brightness, phase if (truth.proximity or truth.slip or deform) else 0.0, deform, moving_bg)
    pts = MARKERS.copy()
    centre = np.array([(WIDTH - 1) / 2, (HEIGHT - 1) / 2])
    q = pts - centre
    r = np.linalg.norm(q, axis=1)
    if fz > 0:
        hz = tacsim.hertz_sphere(fz, R_INDENTER, tacsim.combined_modulus(E_GEL, NU))
        a_px = hz["a"] / (MM_PER_PX * 1e-3)
        w = np.exp(-(r / max(1.0, 1.7 * a_px)) ** 2)
        pts += q * (0.00075 * fz * w)[:, None]
        qtan = math.hypot(fx, fy)
        if qtan > 0:
            mp = tacslip.mindlin_partial_slip(min(qtan, MU * fz), hz, MU, E_GEL / (2 * (1 + NU)), NU)
            stick = mp["c"] / hz["a"]
            shear_w = np.where(r < a_px * stick, 1.0, np.clip(1 - (r - a_px * stick) / max(a_px * (1-stick), 1), 0, 1))
            pts += 0.42 * np.array([fx, fy])[None, :] * shear_w[:, None]
    ang = math.radians(truth.angle_deg) + truth.torque_Nm * 8.0
    rot_w = np.exp(-(r / 63.0) ** 2)
    pts += ang * np.column_stack([-q[:, 1], q[:, 0]]) * rot_w[:, None]
    if truth.slip:
        sd = np.asarray(truth.slip_dir, float)
        if np.linalg.norm(sd) > 0:
            sd /= np.linalg.norm(sd)
            # Cattaneo--Mindlin の固着域が縮んだ後の環状な相対運動。
            annulus = np.clip((r - 25.0) / 55.0, 0, 1)
            pts += 1.8 * annulus[:, None] * sd[None, :]
    out = tacslip.membrane_render_markers(bg, pts, MARKER_RADIUS_PX, 0.82, sub=4)
    rng = np.random.default_rng(seed)
    return np.clip(out + rng.normal(0, 0.006 + 0.012 * (1 - brightness), out.shape), 0, 1)


def _marker_map(image: np.ndarray) -> np.ndarray:
    g = np.asarray(image, float).mean(-1)
    local = np.maximum(np.percentile(g, 78), 0.04)
    return np.clip(1.0 - g / local, 0, 1)


def _track(image: np.ndarray, calib: Calibration) -> dict:
    d0 = tacslip.marker_detect(_marker_map(calib.reference), calib.marker_dark, calib.marker_radius_px)["weighted"]
    d1 = tacslip.marker_detect(_marker_map(image), calib.marker_dark, calib.marker_radius_px)["weighted"]
    if len(d0) == 0 or len(d1) == 0:
        return {"p0": np.zeros((0, 2)), "p1": np.zeros((0, 2)), "u": np.zeros((0, 2)),
                "matched": 0, "n0": len(d0), "n1": len(d1)}
    from scipy.optimize import linear_sum_assignment
    dist = np.linalg.norm(d0[:, None, :] - d1[None, :, :], axis=2)
    i0, i1 = linear_sum_assignment(dist)
    keep = dist[i0, i1] < 0.45 * calib.marker_pitch_px
    i0, i1 = i0[keep], i1[keep]
    return {"p0": d0[i0], "p1": d1[i1], "u": d1[i1] - d0[i0], "matched": len(i0),
            "n0": len(d0), "n1": len(d1)}


def _features(image: np.ndarray, calib: Calibration) -> tuple[np.ndarray, dict]:
    tr = _track(image, calib)
    if tr["matched"] < 6:
        return np.zeros(7), tr
    p, u = tr["p0"], tr["u"]
    c = p.mean(0); q = p - c
    rr = np.maximum(np.linalg.norm(q, axis=1), 1)
    radial = np.sum(u * q, axis=1) / rr
    omega = np.sum(q[:, 0] * u[:, 1] - q[:, 1] * u[:, 0]) / np.sum(q * q)
    mag = np.linalg.norm(u, axis=1)
    # marker size change proxy is dark-pixel area difference, as in the public method.
    ds = float((_marker_map(image) > 0.45).sum() - (_marker_map(calib.reference) > 0.45).sum()) / len(p)
    return np.array([np.mean(u[:, 0]), np.mean(u[:, 1]), np.mean(radial), ds,
                     omega, np.percentile(mag, 80), np.std(mag)]), tr


def _motion_score(prev: np.ndarray, image: np.ndarray) -> tuple[float, np.ndarray]:
    d = np.mean(np.abs(np.asarray(image, float) - np.asarray(prev, float)), axis=2)
    mask = np.asarray(image).mean(2) > 0.08
    ys, xs = np.nonzero((d > 0.07) & mask)
    direction = np.array([0.0, 0.0]) if len(xs) == 0 else np.array([xs.mean() - WIDTH/2, ys.mean() - HEIGHT/2])
    return float(((d > 0.07) & mask).sum()), direction


def read_baseline(image: np.ndarray, calib: Calibration) -> dict:
    """2016/2017 公開式の基準: 線形力、80 percentile、MOG2+HS相当の動体数。"""
    f, _ = _features(image, calib)
    force = calib.baseline_coef * np.array([f[0], f[5], f[3]])
    prev = calib.previous if calib.previous is not None else calib.reference
    score, _ = _motion_score(prev, image)
    backend = "numpy-gaussian"
    if calib.use_cv2:
        try:
            import cv2
            if calib.mog2 is None:
                calib.mog2 = cv2.createBackgroundSubtractorMOG2(history=40, varThreshold=12, detectShadows=False)
                calib.mog2.apply((np.clip(calib.reference, 0, 1) * 255).astype(np.uint8), learningRate=1.0)
            bgr = (np.clip(image[..., ::-1], 0, 1) * 255).astype(np.uint8)
            fg = calib.mog2.apply(bgr, learningRate=0.02) > 0
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            bp = cv2.calcBackProject([hsv], [0, 1], calib.hs_hist, [0, 180, 0, 256], 1)
            score = float((fg & (bp > 12)).sum())
            backend = "cv2-mog2+hs-backprojection"
        except (ImportError, AttributeError):
            pass
    calib.previous = np.asarray(image).copy()
    proximity = float(np.mean(np.abs(image - calib.reference))) > 0.025
    return {"force_N": force, "torque": 0.0, "slip": score > 1150,
            "slip_dir": None, "proximity": proximity, "angle_deg": 0.0,
            "motion_pixels": score, "method": "public-linear+" + backend}


def read_tactile(image: np.ndarray, calib: Calibration) -> dict:
    """画像だけから力・トルク・滑り前兆/方向・近接を返す公開 API。"""
    f, tr = _features(image, calib)
    force = calib.physics_coef[:3] * np.array([f[0], f[1], f[5]])
    torque = calib.physics_coef[3] * f[4]
    slip_index = f[6] / max(f[5], 1e-6)
    mean_u = np.array([f[0], f[1]])
    n = np.linalg.norm(mean_u)
    direction = mean_u / n if n > 1e-6 else np.zeros(2)
    # marker field is deliberately independent of object colour mask.
    marker_visible = tr.get("matched", 0) >= 6
    proximity = float(np.mean(np.abs(image - calib.reference))) > 0.018
    return {"force_N": force, "torque": torque, "slip": bool(marker_visible and slip_index > 0.19),
            "slip_precursor": bool(marker_visible and slip_index > 0.13), "slip_dir": direction,
            "proximity": proximity, "angle_deg": math.degrees(f[4]), "matched": tr.get("matched", 0),
            "method": "marker-field-contact-mechanics"}


def calibrate(samples: list[tuple[np.ndarray, tuple[float, float, float], float]], reference: np.ndarray) -> Calibration:
    """両手法を同じ較正画像で原点通過最小二乗較正する。"""
    c = Calibration(reference=np.asarray(reference), marker_reference=_marker_map(reference))
    try:
        import cv2
        bgr = (np.clip(reference[..., ::-1], 0, 1) * 255).astype(np.uint8)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        yy, xx = np.mgrid[:HEIGHT, :WIDTH]
        central_object = ((((xx - WIDTH/2) / 74) ** 2 + ((yy - HEIGHT/2) / 64) ** 2) < 1).astype(np.uint8)
        c.hs_hist = cv2.calcHist([hsv], [0, 1], central_object, [100, 10], [0, 180, 0, 256])
        cv2.normalize(c.hs_hist, c.hs_hist, 0, 255, cv2.NORM_MINMAX)
    except (ImportError, AttributeError):
        c.use_cv2 = False
    feats = np.array([_features(im, c)[0] for im, _, _ in samples])
    truth = np.array([force for _, force, _ in samples])
    torque = np.array([tau for _, _, tau in samples])
    def slope(x, y):
        return float(np.dot(x, y) / max(np.dot(x, x), 1e-12))
    c.baseline_coef = np.array([slope(feats[:, 0], truth[:, 0]), slope(feats[:, 5], truth[:, 1]), slope(feats[:, 3], truth[:, 2])])
    c.physics_coef = np.array([slope(feats[:, 0], truth[:, 0]), slope(feats[:, 1], truth[:, 1]),
                               slope(feats[:, 5], truth[:, 2]), slope(feats[:, 4], torque)])
    return c
