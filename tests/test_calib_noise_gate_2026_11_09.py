"""Regression tests for the noise-aware degeneracy gate of calib.camera_calibration
(2026-11-09 op audit g2_calib_ct).

The rank-ratio gate (``sv[-2]/sv[0] <= 1e-8``) only fires on noise-free data.
With 0.05 px of observation noise and no distortion, ten fronto-parallel views
gave a ratio of 1.7e-7, passed the gate, and returned fx 33 times the truth
(+3222 %) without an exception. The op now re-solves with the image points
perturbed by the measured residual and refuses when K is not determined."""
import numpy as np
import pytest

import calib
import calib_lm
import camera

Kt = np.array([[1000.0, 0, 640.3], [0, 1010.0, 478.7], [0, 0, 1]])
_gx, _gy = np.meshgrid(np.arange(9), np.arange(6))
OBJ2 = np.stack([_gx.ravel(), _gy.ravel()], 1).astype(float) * 30.0
OBJ3 = np.hstack([OBJ2, np.zeros((len(OBJ2), 1))])
DIST = [-0.18, 0.03, 0.0005, -0.0003, 0.0]


def _views(n, tilt_deg, dist=None, noise=0.0, seed=0):
    r = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        ax = r.normal(size=3)
        ax[2] *= 0.2
        ax /= np.linalg.norm(ax)
        ang = np.deg2rad(tilt_deg) * (0.6 + 0.4 * r.random())
        R = camera.rodrigues(ax * ang)
        t = np.array([-120 + 40 * r.normal(), -75 + 30 * r.normal(), 600 + 50 * r.random()])
        uv, _ = camera.project_points(OBJ3, Kt, R, t)
        if dist is not None:
            uv = camera.distort_points(uv, Kt, dist)
        out.append(uv + r.normal(scale=noise, size=uv.shape))
    return out


def _rc(vs):
    return [v[:, ::-1] for v in vs]                 # (x, y) -> (row, col)


def test_fronto_parallel_with_noise_is_refused():
    vs = _views(10, 0.0, None, 0.05)
    with pytest.raises(ValueError, match="do not determine K"):
        calib.camera_calibration(OBJ2, _rc(vs))


def test_two_degree_tilt_with_more_noise_is_refused():
    # 0.2 px, 2 degrees: fx +28 % before the fix (returned silently), relative std ~55 %
    with pytest.raises(ValueError, match="do not determine K"):
        calib.camera_calibration(OBJ2, _rc(_views(10, 2.0, None, 0.2)))


def test_good_tilt_passes_and_is_accurate():
    o = calib.camera_calibration(OBJ2, _rc(_views(10, 30.0, None, 0.05)))
    assert abs(o["fx"] / Kt[0, 0] - 1) < 0.002
    assert abs(o["fy"] / Kt[1, 1] - 1) < 0.002
    rel = o["intrinsics_rel_std"]
    assert set(rel) == {"fx", "fy", "cx", "cy"}
    assert 0 < max(rel.values()) < 0.01


def test_rel_std_tracks_actual_error():
    # 5 degrees, 0.05 px: passes; the reported spread is the size of the error
    o = calib.camera_calibration(OBJ2, _rc(_views(10, 5.0, None, 0.05)))
    err = abs(o["fx"] / Kt[0, 0] - 1)
    assert err < 3 * o["intrinsics_rel_std"]["fx"] + 1e-3


def test_noise_free_small_tilt_still_passes():
    o = calib.camera_calibration(OBJ2, _rc(_views(10, 0.5, None, 0.0)))
    assert abs(o["fx"] / Kt[0, 0] - 1) < 1e-6


def test_deterministic_decision():
    vs = _rc(_views(10, 5.0, None, 0.2))
    a = calib.camera_calibration(OBJ2, vs)["intrinsics_rel_std"]
    b = calib.camera_calibration(OBJ2, vs)["intrinsics_rel_std"]
    assert a == b


def test_lm_still_starts_from_the_closed_form_when_the_public_gate_refuses():
    # 5 degrees with real distortion: the public op refuses (relative std > 5 %),
    # but camera_calibration_lm only needs a start and must keep using Zhang.
    vs = _views(10, 5.0, DIST, 0.05)
    with pytest.raises(ValueError, match="do not determine K"):
        calib.camera_calibration(OBJ2, _rc(vs))
    res = calib_lm.camera_calibration_lm(OBJ2, _rc(vs))
    assert res["init"]["method"] == "zhang"


def test_zero_skew_route_for_distorted_lens():
    # skew is free in the closed form and soaks up distortion (cx +8 px at 30 deg);
    # the documented cv2-like route is calib_lm.camera_calibration_lm.
    vs = _views(10, 30.0, DIST, 0.05)
    o = calib.camera_calibration(OBJ2, _rc(vs))
    assert abs(o["skew"]) > 3.0                     # the leak documented in the docstring
    res = calib_lm.camera_calibration_lm(OBJ2, _rc(vs))
    K = np.asarray(res["K"])
    assert K[0, 1] == 0.0
    assert abs(K[0, 2] - Kt[0, 2]) < 3.0 and abs(K[1, 2] - Kt[1, 2]) < 3.0
    assert "camera_calibration_lm" in calib.camera_calibration.__doc__
