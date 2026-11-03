"""New ops found missing by the coverage recipes (2026-11-03): closed-form truths.

* ``fit_circle_xld`` (shape2d) — circle per XLD contour: points exactly on a circle give the centre and
  radius to machine precision; the per-contour order is kept; short contours are skipped and counted.
* ``wave_dominant_frequency`` (math) — strongest non-DC 2-D FFT peak: a grating
  ``cos(2π(x cosθ + y sinθ)/p)`` returns (θ, p); with ``window="none"`` and an integer number of
  periods across the image the answer is exact.
* ``find_surface_pose`` (3d) — PPF + ICP registered as a ledger op: ``fs.ledger`` returns the pose
  canon ``(R, t)`` and recovers a known rigid motion of a non-symmetric part.
"""
from __future__ import annotations

import math
import os

import numpy as np
import pytest

os.environ.setdefault("FULLSEYE_DEVICE", "cpu")

import fullseye as fs  # noqa: E402
import fourierdesc  # noqa: E402
import mathops  # noqa: E402


# ------------------------------------------------------------------ fit_circle_xld
def _circle(cy, cx, r, n=90, a0=0.0, a1=360.0):
    t = np.radians(np.linspace(a0, a1, n, endpoint=False))
    return np.c_[cy + r * np.sin(t), cx + r * np.cos(t)]


@pytest.mark.parametrize("method", ["geometric", "algebraic"])
def test_fit_circle_xld_exact_on_circle_points(method):
    xld = {"shape": (100, 100), "cs": [_circle(40.25, 61.5, 17.75), _circle(10.0, 12.0, 4.0, n=30)]}
    out = fourierdesc.fit_circle_xld(xld, method=method)
    assert out["n_contours"] == 2 and out["n_skipped"] == 0 and out["method"] == method
    np.testing.assert_allclose(out["row"], [40.25, 10.0], atol=1e-9)
    np.testing.assert_allclose(out["col"], [61.5, 12.0], atol=1e-9)
    np.testing.assert_allclose(out["radius"], [17.75, 4.0], atol=1e-9)
    assert max(out["rms"]) < 1e-9 and out["n_points"] == [90, 30]


def test_fit_circle_xld_geometric_beats_algebraic_on_a_noisy_short_arc():
    rng = np.random.default_rng(3)
    errs = {"geometric": [], "algebraic": []}
    for _ in range(20):
        arc = _circle(0.0, 0.0, 50.0, n=60, a0=0.0, a1=50.0) + 0.3 * rng.standard_normal((60, 2))
        for m in errs:
            errs[m].append(fourierdesc.fit_circle_xld({"shape": (1, 1), "cs": [arc]}, method=m)["radius"][0] - 50.0)
    # Kåsa's algebraic fit is biased low on short noisy arcs (Chernov 2010, ch. 5); the geometric fit is not
    assert abs(np.mean(errs["geometric"])) < abs(np.mean(errs["algebraic"]))


def test_fit_circle_xld_skips_short_contours_and_rejects_bad_input():
    xld = {"shape": (50, 50), "cs": [np.array([[1.0, 1.0], [2.0, 2.0]]), _circle(20.0, 20.0, 8.0)]}
    out = fs.ledger.fit_circle_xld(xld)
    assert out["n_contours"] == 1 and out["n_skipped"] == 1
    assert abs(out["radius"][0] - 8.0) < 1e-9
    with pytest.raises(ValueError, match="empty"):
        fourierdesc.fit_circle_xld({"shape": (5, 5), "cs": []})
    with pytest.raises(ValueError, match="XLD"):
        fourierdesc.fit_circle_xld(np.zeros((5, 2)))
    with pytest.raises(ValueError, match="method"):
        fourierdesc.fit_circle_xld(xld, method="huber")
    with pytest.raises(ValueError, match="at least 3"):
        fourierdesc.fit_circle_xld({"shape": (5, 5), "cs": [np.zeros((2, 2))]})
    line = np.c_[np.arange(10.0), 2.0 * np.arange(10.0)]
    with pytest.raises(ValueError):
        fourierdesc.fit_circle_xld({"shape": (30, 30), "cs": [line]}, method="algebraic")


# ------------------------------------------------------------------ wave_dominant_frequency
def _grating(theta_deg, period, shape=(64, 64)):
    th = math.radians(theta_deg)
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return 0.5 + 0.4 * np.cos(2 * np.pi * (xx * math.cos(th) + yy * math.sin(th)) / period)


def test_wave_dominant_frequency_exact_on_bin_centred_grating():
    # 64 px wide, period 8 along x -> exactly 8 cycles: the peak sits on a bin and the answer is exact
    r = mathops.wave_dominant_frequency(_grating(0.0, 8.0), window="none")
    assert r["fx"] == pytest.approx(1 / 8, abs=1e-12) and r["fy"] == pytest.approx(0.0, abs=1e-12)
    assert r["period_px"] == pytest.approx(8.0, abs=1e-9) and r["angle_deg"] == pytest.approx(0.0, abs=1e-9)
    assert r["peak_fraction"] == pytest.approx(1.0, abs=1e-9)        # a pure cosine: all power in the pair


@pytest.mark.parametrize("theta,period", [(30.0, 8.0), (60.0, 8.0), (120.0, 11.0), (90.0, 5.0), (15.0, 13.0)])
def test_wave_dominant_frequency_recovers_angle_and_period(theta, period):
    r = fs.ledger.wave_dominant_frequency(_grating(theta, period))
    assert r["period_px"] == pytest.approx(period, rel=0.01)
    d = abs(r["angle_deg"] - theta) % 180.0
    assert min(d, 180.0 - d) < 0.3
    assert 0.0 <= r["angle_deg"] < 180.0 and r["fx"] >= 0.0
    assert r["freq_cpp"] == pytest.approx(math.hypot(r["fx"], r["fy"]))


def test_wave_dominant_frequency_rectangular_image_and_rejections():
    r = mathops.wave_dominant_frequency(_grating(45.0, 10.0, shape=(48, 80)))
    assert r["period_px"] == pytest.approx(10.0, rel=0.02)
    with pytest.raises(ValueError, match="empty"):
        mathops.wave_dominant_frequency(np.zeros((0, 0)))
    with pytest.raises(ValueError, match="flat"):
        mathops.wave_dominant_frequency(np.full((16, 16), 0.3))
    with pytest.raises(ValueError, match="8 px"):
        mathops.wave_dominant_frequency(np.random.default_rng(0).random((4, 32)))
    with pytest.raises(ValueError, match="window"):
        mathops.wave_dominant_frequency(_grating(0.0, 8.0), window="blackman")
    bad = _grating(0.0, 8.0)
    bad[3, 3] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        mathops.wave_dominant_frequency(bad)


def test_wave_dominant_frequency_is_on_the_facade_and_math_ledger():
    import opsmath
    assert opsmath.OPSMATH["wave_dominant_frequency"]["out"] == "table"
    assert fs.wave_dominant_frequency is mathops.wave_dominant_frequency


# ------------------------------------------------------------------ find_surface_pose
def _rot(axis, deg):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    t = math.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * K @ K


def _bracket():
    g = np.linspace(0.0, 1.0, 7)
    base = np.array([[x * 3.0, y * 2.0, 0.0] for x in g for y in g])
    wall = np.array([[0.0, y * 2.0, z * 1.5] for y in g for z in g[1:]])
    th = np.linspace(0.0, 2 * np.pi, 16, endpoint=False)
    boss = np.array([[2.2 + 0.35 * math.cos(a), 0.6 + 0.35 * math.sin(a), z] for a in th for z in (0.3, 0.6, 0.9)])
    return np.vstack([base, wall, boss])


def test_find_surface_pose_ledger_returns_pose_canon_and_recovers_motion():
    import ops3d
    assert ops3d.OPS3D["find_surface_pose"]["in"] == ["points", "points"]
    assert ops3d.OPS3D["find_surface_pose"]["out"] == "pose"
    M = _bracket()
    rng = np.random.default_rng(5)
    R_gt, t_gt = _rot((0.2, 1.0, 0.4), 50.0), np.array([-0.3, 0.7, 0.15])
    keep = rng.permutation(len(M))[: int(0.9 * len(M))]
    S = M[keep] @ R_gt.T + t_gt + 0.005 * rng.standard_normal((len(keep), 3))
    pose = fs.ledger.find_surface_pose(M, S)
    assert isinstance(pose, tuple) and len(pose) == 2
    R, t = pose
    ang = math.degrees(math.acos(np.clip((np.trace(R.T @ R_gt) - 1.0) / 2.0, -1.0, 1.0)))
    assert ang < 1.0 and np.linalg.norm(t - t_gt) < 0.02
    raw = fs.ledger.find_surface_pose.raw(M, S)
    assert set(raw) >= {"R", "t", "rmse", "votes", "inlier_fraction"} and raw["inlier_fraction"] > 0.9


def test_find_surface_pose_rejects_empty_clouds():
    import ppf
    with pytest.raises(ValueError, match="model_points is empty"):
        ppf.find_surface_pose(np.zeros((0, 3)), np.ones((10, 3)))
    with pytest.raises(ValueError, match="scene_points is empty"):
        ppf.find_surface_pose(_bracket(), np.zeros((0, 3)))
