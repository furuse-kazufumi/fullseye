#!/usr/bin/env python3
"""Phase-measuring deflectometry field-sweep viewer for ViEW 2026 (ja/en)."""
from __future__ import annotations

import argparse
import functools
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import map_coordinates

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fringe  # noqa: E402
import fullseye as fs  # noqa: E402
import photometric  # noqa: E402
import pocviewer as pv  # noqa: E402

T = pv.viewer_text
ANIM3D_I18N_LANGS = ("ja", "en")
LANGS = ANIM3D_I18N_LANGS
OUT_HTML = ROOT / "docs" / "view2026" / "viewers" / "phase_measuring_deflectometry_anim3d.html"
N = 161
PANEL = 256
PERIOD = 10.0
COARSE = 160.0
NOISE = 0.004
BITS = 8
SIGMA_PX = 1.0
DISTANCE_ERRORS = np.linspace(-5.0, 5.0, 21)
DIFFUSE = np.linspace(0.0, 0.95, 20)
DIMPLE_A = (-8.0, -5.0, 3.0e-3, 1.2)
DIMPLE_B = (9.0, 7.0, 1.0e-3, 1.0)
WAVE = (0.8e-3, 12.0)
POLISH = (6.0, -11.0, 0.12e-3, 0.9)
CURVATURE_RANGE = 0.0035


def _e(value):
    return "< 1e-12" if abs(float(value)) < 1e-12 else "%.4g" % float(value)


def surface(xx, yy):
    """Analytic painted panel height [mm] and slopes."""
    h = np.zeros_like(xx); p = np.zeros_like(xx); q = np.zeros_like(xx)
    for x0, y0, dep, sigma in (DIMPLE_A, DIMPLE_B):
        g = np.exp(-((xx - x0) ** 2 + (yy - y0) ** 2) / (2 * sigma ** 2))
        h -= dep * g; p += dep * (xx - x0) / sigma ** 2 * g; q += dep * (yy - y0) / sigma ** 2 * g
    amp, lam = WAVE; k = 2 * np.pi / lam; phase = k * (0.8 * xx + 0.6 * yy)
    h += amp * np.sin(phase); p += amp * k * 0.8 * np.cos(phase); q += amp * k * 0.6 * np.cos(phase)
    x0, y0, amp, lam = POLISH; k = 2 * np.pi / lam
    env = np.exp(-((xx - x0) ** 2 / (2 * 4.0 ** 2) + (yy - y0) ** 2 / (2 * 2.0 ** 2)))
    phase = k * (0.3 * (xx - x0) + 0.95 * (yy - y0)); co, si = np.cos(phase), np.sin(phase)
    h += amp * env * co
    p += amp * (-((xx - x0) / 16.0) * env * co - env * si * k * 0.3)
    q += amp * (-((yy - y0) / 4.0) * env * co - env * si * k * 0.95)
    return h, p, q


def _measure_phase(h, p, q, rig, **kwargs):
    out = {}
    for direction in ("x", "y"):
        fine = fs.ledger.deflectometry_render(h, rig, PERIOD, 4, direction, slope_x=p, slope_y=q, **kwargs)
        coarse = fs.ledger.deflectometry_render(
            h, rig, COARSE, 4, direction, slope_x=p, slope_y=q,
            **dict(kwargs, seed=kwargs.get("seed", 0) + 101))
        wrapped = fringe.wrapped_phase(fine)
        out[direction] = fringe.absolute_phase(wrapped, fringe.wrapped_phase(coarse) * (COARSE / PERIOD))
        out["w" + direction] = wrapped
        out["mod" + direction] = fringe.modulation(fine)
        out["img" + direction] = fine
    return out


def _normal_from_phase(phases, rig):
    return fs.ledger.deflectometry_phase_to_slope(phases["x"], phases["y"], rig, PERIOD)


def _integrate(normals, spacing):
    safe = np.where(np.isfinite(normals), normals, [0.0, 0.0, 1.0])
    return fs.ledger.sfp_height(safe) * spacing


def _depth(z, xx, yy, dimple):
    x0, y0, _dep, sigma = dimple; dx, dy = xx - x0, yy - y0; r2 = dx * dx + dy * dy
    ring = (r2 > (3 * sigma) ** 2) & (r2 < (4 * sigma) ** 2) & np.isfinite(z)
    core = (r2 < (0.25 * sigma) ** 2) & np.isfinite(z)
    def basis(mask):
        return np.stack([np.ones(mask.sum()), dx[mask], dy[mask], dx[mask] ** 2, dx[mask] * dy[mask], dy[mask] ** 2], 1)
    coef = np.linalg.lstsq(basis(ring), z[ring], rcond=None)[0]
    return float(np.mean(basis(core) @ coef - z[core]))


def _align_height(z, truth):
    edge = np.zeros_like(z, bool); edge[:8] = edge[-8:] = True; edge[:, :8] = edge[:, -8:] = True
    return z - float(np.mean((z - truth)[edge]))


def _grid_faces(n):
    ids = np.arange(n * n).reshape(n, n); faces = []
    for r in range(n - 1):
        for c in range(n - 1):
            q = ids[r:r + 2, c:c + 2]
            faces.extend(((q[0, 0], q[0, 1], q[1, 1]), (q[0, 0], q[1, 1], q[1, 0])))
    return np.asarray(faces, int)


def _colour(curvature):
    u = np.clip((np.asarray(curvature) + CURVATURE_RANGE) / (2 * CURVATURE_RANGE), 0, 1)
    r = np.clip(2 * u, 0, 1); b = np.clip(2 * (1 - u), 0, 1); g = 1 - np.abs(2 * u - 1)
    return np.uint8(np.stack([255 * r, 255 * g, 255 * b], -1))


def _resize_gray(image):
    a = np.asarray(image, float); lo, hi = np.percentile(a, (1, 99))
    g = np.uint8(255 * np.clip((a - lo) / max(hi - lo, 1e-12), 0, 1))
    return np.asarray(Image.fromarray(g, "L").resize((PANEL, PANEL), Image.Resampling.BILINEAR).convert("RGB"))


def _curvature_panel(curvature):
    return np.asarray(Image.fromarray(_colour(curvature), "RGB").resize((PANEL, PANEL), Image.Resampling.BILINEAR))


def _path_profile(field, x, y, count=180):
    x0, y0 = DIMPLE_A[:2]; x1, y1 = DIMPLE_B[:2]
    xp = np.linspace(x0 - 4.0, x1 + 4.0, count); yp = np.linspace(y0 - 3.0, y1 + 3.0, count)
    col = (xp - x[0]) / (x[-1] - x[0]) * (len(x) - 1); row = (yp - y[0]) / (y[-1] - y[0]) * (len(y) - 1)
    return map_coordinates(np.asarray(field, float), [row, col], order=1, mode="nearest")


def _profile_panel(truth, recovered):
    truth = np.asarray(truth) * 1000.0; recovered = np.asarray(recovered) * 1000.0
    im = Image.new("RGB", (PANEL, PANEL), (12, 16, 21)); d = ImageDraw.Draw(im)
    left, right, top, bottom = 38, 246, 28, 222
    lo = min(float(truth.min()), float(recovered.min())); hi = max(float(truth.max()), float(recovered.max()))
    xx = np.linspace(left, right, len(truth))
    def pts(values):
        yy = bottom - (values - lo) / max(hi - lo, 1e-12) * (bottom - top)
        return list(zip(xx, yy))
    d.line(pts(truth), fill=(90, 195, 255), width=5); d.line(pts(recovered), fill=(255, 180, 70), width=2)
    d.text((8, 7), "blue truth | orange recovered", fill=(235, 239, 243)); d.text((5, 30), "um", fill=(180, 190, 200))
    d.text((70, 232), "section through both dents", fill=(180, 190, 200))
    return np.asarray(im)


def _motion(frames, bodies=1):
    xyz = np.zeros((frames, bodies, 3)); quat = np.zeros((frames, bodies, 4)); quat[..., 0] = 1.0
    return xyz, quat


def _decode_series(phases, rigs, h, spacing):
    curvatures, heights, normals = [], [], []
    for rig in rigs:
        n = _normal_from_phase(phases, rig)
        normals.append(n)
        curvatures.append(fs.ledger.slope_to_curvature(n, spacing, "mean", SIGMA_PX))
        heights.append(_align_height(_integrate(n, spacing), h))
    return np.asarray(curvatures), np.asarray(heights), normals


def _caption_distance_gate():
    """The full PoC grid reproduces its published +2% distance caption."""
    n = 320; rig = fs.ledger.deflectometry_rig(); x = (np.arange(n) - (n - 1) / 2) * rig["field_mm"] / (n - 1)
    xx, yy = np.meshgrid(x, x); spacing = float(x[1] - x[0]); h, p, q = surface(xx, yy)
    phases = _measure_phase(h, p, q, rig)
    wrong = fs.ledger.deflectometry_rig(screen_distance_mm=rig["screen_distance_mm"] * 1.02)
    z = _integrate(_normal_from_phase(phases, wrong), spacing)
    return 100 * (_depth(z, xx, yy, DIMPLE_A) / _depth(h, xx, yy, DIMPLE_A) - 1)


@functools.lru_cache(maxsize=1)
def compute():
    rig = fs.ledger.deflectometry_rig(); x = (np.arange(N) - (N - 1) / 2) * rig["field_mm"] / (N - 1)
    xx, yy = np.meshgrid(x, x); spacing = float(x[1] - x[0]); h, p, q = surface(xx, yy)
    true_n = np.dstack([-p, -q, np.ones_like(p)]); true_n /= np.linalg.norm(true_n, axis=-1, keepdims=True)
    true_curvature = fs.ledger.slope_to_curvature(true_n, spacing, "mean", SIGMA_PX)
    photo = fs.ledger.deflectometry_render(h, rig, kind="softbox", slope_x=p, slope_y=q,
                                            noise_sigma=NOISE, bits=BITS, seed=7)[0]
    clean_phase = _measure_phase(h, p, q, rig, noise_sigma=NOISE, bits=BITS, seed=1)

    distance_rigs = [fs.ledger.deflectometry_rig(screen_distance_mm=rig["screen_distance_mm"] * (1 + e / 100.0))
                     for e in DISTANCE_ERRORS]
    dcurv, dheights, dnormals = _decode_series(clean_phase, distance_rigs, h, spacing)
    ddepth = np.asarray([_depth(z, xx, yy, DIMPLE_A) for z in dheights]) * 1000.0

    kcurv, kheights, fringe_frames, jump_rates, modulation = [], [], [], [], []
    clean_p, clean_q = photometric.normals_to_gradients(dnormals[np.argmin(np.abs(DISTANCE_ERRORS))])
    for kd in DIFFUSE:
        phases = _measure_phase(h, p, q, rig, diffuse_fraction=float(kd), noise_sigma=NOISE, bits=BITS, seed=3)
        nrm = _normal_from_phase(phases, rig)
        pk, qk = photometric.normals_to_gradients(nrm)
        jump = np.hypot(pk - clean_p, qk - clean_q) > 0.5 * PERIOD / (2 * rig["screen_distance_mm"])
        jump_rates.append(float(np.mean(jump)))
        modulation.append(float(np.nanmedian(phases["modx"])))
        kcurv.append(fs.ledger.slope_to_curvature(nrm, spacing, "mean", SIGMA_PX))
        kheights.append(_align_height(_integrate(nrm, spacing), h))
        fringe_frames.append(phases["imgx"][0])
    kcurv, kheights = np.asarray(kcurv), np.asarray(kheights)
    kdepth = np.asarray([_depth(z, xx, yy, DIMPLE_A) for z in kheights]) * 1000.0
    first_jump = float(DIFFUSE[next((i for i, v in enumerate(jump_rates) if v > 0.001), len(DIFFUSE) - 1)])

    photo_signal = fs.ledger.deflectometry_render(h, rig, kind="softbox", slope_x=p, slope_y=q)[0]
    photo_flat = fs.ledger.deflectometry_render(np.zeros_like(h), rig, kind="softbox")[0]
    photo_snr = float(np.max(np.abs(photo_signal - photo_flat)) / NOISE)
    caption_error = float(_caption_distance_gate())
    sens = [fs.ledger.deflectometry_sensitivity(rig, PERIOD, 4, NOISE, bits=BITS, diffuse_fraction=float(kd))
            for kd in DIFFUSE]
    return {"rig": rig, "x": x, "xx": xx, "yy": yy, "spacing": spacing, "h": h, "true_curvature": true_curvature,
            "photo": photo, "fringe_clean": clean_phase["imgx"][0], "distance_curvature": dcurv,
            "distance_height": dheights, "distance_depth": ddepth, "diffuse_curvature": kcurv,
            "diffuse_height": kheights, "diffuse_depth": kdepth, "diffuse_fringe": fringe_frames,
            "jump_rates": np.asarray(jump_rates), "modulation": np.asarray(modulation), "first_jump": first_jump,
            "caption_error_pct": caption_error, "photo_snr": photo_snr, "sensitivity": sens}


def _tab(data, kind):
    if kind == "distance":
        values = DISTANCE_ERRORS; curv = data["distance_curvature"]; heights = data["distance_height"]
        depths = data["distance_depth"]; fringes = [data["fringe_clean"]] * len(values)
        label = T("① 画面までの距離の誤差", "① Screen-distance error")
        text = T("距離の思い込みを±5%動かす。+2%では凹みを2.3%浅く読む。",
                 "Sweep the assumed distance by ±5%; at +2% the dent reads 2.3% shallower.")
        axis = {"values": values, "segments": [{"k": 0, "label": T("画面距離の誤差", "screen-distance error"), "unit": "%", "decimals": 1}]}
        checks = [{"what": T("+2%での凹みAの深さ誤差", "dent A depth error at +2%"),
                   "criterion": T("PoC captionの−2.3%に0.2%以内", "within 0.2% of the PoC caption −2.3%"),
                   "result": "%+.3f%%" % data["caption_error_pct"],
                   "ok": abs(data["caption_error_pct"] + 2.3) < 0.2}]
        extra_series = []
    else:
        values = DIFFUSE; curv = data["diffuse_curvature"]; heights = data["diffuse_height"]
        depths = data["diffuse_depth"]; fringes = data["diffuse_fringe"]
        label = T("② 拡散成分で縞が消える", "② Diffuse component erases fringes")
        text = T("k_dを0から0.95へ上げると縞振幅が落ち、0.9付近から次数が飛んで曲率が雑音へ埋もれる。",
                 "Raise k_d from 0 to 0.95: fringe amplitude falls and order jumps near 0.9 bury curvature in noise.")
        axis = {"values": values, "segments": [{"k": 0, "label": T("拡散成分 k_d", "diffuse fraction k_d"), "unit": "", "decimals": 2}]}
        checks = [{"what": T("次数が飛び始めるk_d", "k_d where order jumps begin"),
                   "criterion": T("0.85〜0.95", "0.85 to 0.95"), "result": "%.2f" % data["first_jump"],
                   "ok": 0.85 <= data["first_jump"] <= 0.95},
                  {"what": T("縞振幅と閉形式(1−k_d)", "fringe amplitude and closed form (1-k_d)"),
                   "criterion": "< 1e-12", "result": _e(np.max(np.abs(
                       np.asarray([s["fringe_amplitude"] for s in data["sensitivity"]]) /
                       np.asarray([s["fringe_amplitude"] for s in data["sensitivity"]])[0] - (1 - DIFFUSE)))),
                   "ok": np.max(np.abs(np.asarray([s["fringe_amplitude"] for s in data["sensitivity"]]) /
                                         data["sensitivity"][0]["fringe_amplitude"] - (1 - DIFFUSE))) < 1e-12}]
        extra_series = [{"label": T("次数飛び", "order jumps"), "values": 100 * data["jump_rates"],
                         "unit": "%", "color": "#ef5350"}]

    rgb = np.asarray([_colour(k) for k in curv])
    xx, yy = data["xx"], data["yy"]
    pos = np.c_[xx.ravel(), yy.ravel(), np.zeros(xx.size)]
    body = {"name": "painted_panel_height", "pos": pos, "faces": _grid_faces(N), "rgb": rgb.reshape(len(values), -1, 3),
            "val": data["h"].ravel() * 1000.0, "relief_default": 1.0,
            "label": T("塗装パネル: 色=平均曲率、起伏=高さ", "painted panel: colour=mean curvature, relief=height")}
    xyz, quat = _motion(len(values))
    photo_frames = np.repeat(_resize_gray(data["photo"])[None], len(values), 0)
    fringe_panels = np.asarray([_resize_gray(f) for f in fringes])
    curvature_panels = np.asarray([_curvature_panel(k) for k in curv])
    truth_profile = _path_profile(data["h"], data["x"], data["x"])
    profile_panels = np.asarray([_profile_panel(truth_profile, _path_profile(z, data["x"], data["x"])) for z in heights])
    colour_ptp = float(np.ptp(rgb[-1].astype(float) - rgb[0].astype(float)))
    checks.insert(0, {"what": T("掃引の両端で3-Dの色が変わる", "3-D colour changes between endpoints"),
                      "criterion": "ptp > 0", "result": "%.0f RGB levels" % colour_ptp, "ok": colour_ptp > 0})
    panes = [
        {"label": T("(a) 写真: 凹みは見えない", "(a) Photograph: dents invisible"), "frames": photo_frames, "png": True},
        {"label": T("(b) 縞の鏡像", "(b) Mirror image of fringes"), "frames": fringe_panels, "png": True},
        {"label": T("(c) 平均曲率の地図", "(c) Mean-curvature map"), "frames": curvature_panels, "png": True},
        {"label": T("(d) 2つの凹みを通る断面: 復元 / 真値", "(d) Section through both dents: recovered / truth"),
         "frames": profile_panels, "png": True, "data": heights * 1000.0, "data_unit": "µm"},
    ]
    exaggeration = (0.25 * math.hypot(40.0, 40.0) / 2) / float(np.ptp(data["h"]))
    series = [{"label": T("凹みAの読取深さ", "read depth of dent A"), "values": depths, "unit": "µm", "color": "#ffb74d"},
              *extra_series]
    tab = pv.viewer_anim3d_tab(
        kind, label, "passed", text, np.arange(len(values)) / 8.0, [body], xyz, quat,
        series=series, panes=panes, cbar={"lo": -CURVATURE_RANGE, "hi": CURVATURE_RANGE, "unit": "1/mm",
                                          "cmap": "div", "label": T("平均曲率", "mean curvature")},
        numbers=[pv.viewer_number(T("起伏×1の誇張率", "exaggeration at relief ×1"), "×%.0f" % exaggeration),
                 pv.viewer_number(T("真の凹み", "true dents"), "3 µm / 1 µm")],
        axis=axis, checks=checks, view={"az": -0.8, "el": 0.58, "dist": 1.04})
    return tab, {"colour_ptp": colour_ptp, "depth_endpoints": depths[[0, -1]], "exaggeration_x1": exaggeration}


def build_spec():
    data = compute(); distance, da = _tab(data, "distance"); diffuse, ka = _tab(data, "diffuse")
    spec = pv.viewer_spec(
        "phase_measuring_deflectometry", T("写真に写らないµmの凹み", "Micron dents invisible in a photograph"),
        T("塗装パネルの起伏と平均曲率を3-Dに載せ、縞から読む形状の壊れ方まで見る。",
          "A 3-D painted panel carries height and mean curvature, including how stripe-based recovery fails."),
        T("距離誤差またはk_dを掃引し、起伏つまみでµm形状の誇張率を変える。",
          "Sweep distance error or k_d; use Relief to change the exaggeration of the micron-scale shape."),
        [distance, diffuse],
        credit=T("合成塗装パネル。計算: deflectometry_rig, deflectometry_render, deflectometry_phase_to_slope, slope_to_curvature, sfp_height, deflectometry_sensitivity。",
                 "Synthetic painted panel. Computation: deflectometry_rig, deflectometry_render, deflectometry_phase_to_slope, slope_to_curvature, sfp_height, deflectometry_sensitivity."))
    spec["generated"] = "2026-11-01"
    spec["_acceptance"] = {"frames": {"distance": len(DISTANCE_ERRORS), "diffuse": len(DIFFUSE)},
                            "distance": da, "diffuse": ka, "distance_2pct_error": data["caption_error_pct"],
                            "first_order_jump_kd": data["first_jump"], "photo_snr": data["photo_snr"],
                            "ops": ["deflectometry_rig", "deflectometry_render", "deflectometry_phase_to_slope",
                                    "slope_to_curvature", "sfp_height", "deflectometry_sensitivity"]}
    return spec


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, default=OUT_HTML); ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv); spec = build_spec(); a = spec["_acceptance"]
    print("CHECK distance colour_ptp=%.0f depth=%.3f->%.3f um +2%%=%+.3f%%" % (
        a["distance"]["colour_ptp"], *a["distance"]["depth_endpoints"], a["distance_2pct_error"]))
    print("CHECK diffuse colour_ptp=%.0f depth=%.3f->%.3f um first_jump=%.2f" % (
        a["diffuse"]["colour_ptp"], *a["diffuse"]["depth_endpoints"], a["first_order_jump_kd"]))
    if args.check:
        pv._build_html(spec, list(LANGS), detect_lang=True)
    else:
        pv.write_viewer(spec, str(args.out), list(LANGS), detect_lang=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
