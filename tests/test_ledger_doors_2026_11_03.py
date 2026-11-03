# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Ledger doors that now take their DECLARED input in the first slot (recipe e2e findings, 2026-11-03).

The coverage recipes found four declaration lies: the typed ledger declared an input sort that the
function could not take in the first positional slot, so the typed chain producer -> op could not be
built (``fs.ledger.<op>(value)`` raised TypeError):

* ``text_lines``            declared ``table`` (the ``text_candidates`` output) but read an (N, 4) array;
* ``sun_position``          declared ``signal`` (UNIX times) but the signature starts with ``lat_deg``;
* ``pose_error`` / ``rotation_translation_error`` declared ``[pose, pose]`` but took 4 arrays / 4x4 matrices;
* ``rss_*`` (8 ops)         declared ``table`` (``rss_params``) but the table is the 3rd / 4th parameter.

Each fix keeps the raw function's public signature and the old call forms (fail-closed where a form is
ambiguous). The truths here are closed forms, not the op's own output.
"""
from __future__ import annotations

import inspect
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import fullseye as fs  # noqa: E402


def _rz(deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _first_param(fn):
    return next(iter(inspect.signature(fn).parameters))


# --------------------------------------------------------------------------- text_lines
def _swt_lines(n_lines):
    m = np.zeros((8 + 28 * n_lines, 96))
    for li in range(n_lines):
        for g in range(4):
            m[8 + 28 * li:24 + 28 * li, 6 + 14 * g:14 + 14 * g] = 3.0
    return m


@pytest.mark.parametrize("n_lines", [1, 2, 3])
def test_text_lines_takes_the_candidates_table(n_lines):
    cand = fs.ledger.text_candidates(_swt_lines(n_lines), min_area=8)
    got = fs.ledger.text_lines(cand)
    assert len(got["lines"]) == n_lines                       # truth: the painted layout
    for li, box in enumerate(got["lines"]):
        assert list(box) == [8 + 28 * li, 6, 24 + 28 * li, 6 + 14 * 3 + 8]
    assert all(len(m) == 4 for m in got["members"])
    # the table form is the array form with the table's own stroke widths
    import textregion
    ref = textregion.text_lines(cand["boxes"], cand["stroke_width"])
    assert np.array_equal(got["lines"], ref["lines"]) and got["members"] == ref["members"]


def test_text_lines_table_uses_its_stroke_width():
    # two boxes on one row, stroke widths 1 and 10 (> width_ratio 3): split only if the widths are read
    table = {"boxes": np.array([[0, 0, 10, 8], [0, 10, 10, 18]]), "stroke_width": np.array([1.0, 10.0])}
    assert len(fs.ledger.text_lines(table)["lines"]) == 2
    assert len(fs.ledger.text_lines(table["boxes"])["lines"]) == 1


def test_text_lines_table_is_fail_closed():
    with pytest.raises(ValueError, match="boxes"):
        fs.ledger.text_lines({"lines": np.zeros((1, 4))})
    with pytest.raises(ValueError, match="both"):
        fs.ledger.text_lines({"boxes": np.zeros((1, 4), int), "stroke_width": np.ones(1)}, np.ones(1))


# --------------------------------------------------------------------------- sun_position
T_EQUINOX = 1710892800.0 + np.arange(0.0, 86400.0, 300.0)    # 2024-03-20, every 5 min (UTC)


@pytest.mark.parametrize("lat,lon", [(35.68, 139.77), (-33.87, 151.21), (-37.81, 144.96)])
def test_sun_position_ledger_takes_the_time_series_first(lat, lon):
    import geocam
    r = fs.ledger.sun_position(T_EQUINOX, lat, lon)
    # closed form: the March equinox is 2024-03-20 03:06 UTC and these sites have their solar noon within ~1 h of
    # it, so |delta| < 0.02 deg at noon (delta moves ~0.39 deg/day) -> the max true elevation is 90 - |lat|
    assert abs(float(np.max(r["elevation_true_deg"])) - (90.0 - abs(lat))) < 0.05
    ref = geocam.sun_position(lat, lon, T_EQUINOX)
    for k in ("azimuth_deg", "elevation_deg"):
        assert np.array_equal(r[k], ref[k])
    assert np.array_equal(fs.ledger.sun_position(T_EQUINOX, lat_deg=lat, lon_deg=lon)["elevation_deg"],
                          ref["elevation_deg"])


def test_sun_position_ledger_still_reads_the_old_order_and_refuses_ambiguity():
    import geocam
    ref = geocam.sun_position(35.68, 139.77, T_EQUINOX)
    old = fs.ledger.sun_position(35.68, 139.77, T_EQUINOX)       # old positional order (times last)
    assert np.array_equal(old["elevation_deg"], ref["elevation_deg"])
    with pytest.raises(ValueError):                              # old order with a scalar time: never guessed
        fs.ledger.sun_position(35.68, 139.77, 1710900000.0)
    with pytest.raises(ValueError):
        fs.ledger.sun_position(T_EQUINOX, np.array([35.0, 36.0]), 139.77)


def test_sun_position_ledger_signature_and_identity():
    import geocam
    fn = fs.ledger.sun_position.raw
    assert list(inspect.signature(fn).parameters) == ["unix_times", "lat_deg", "lon_deg"]
    assert inspect.unwrap(fn) is geocam.sun_position              # one op behind every door
    assert list(inspect.signature(geocam.sun_position).parameters)[0] == "lat_deg"   # raw API unchanged


# --------------------------------------------------------------------------- pose_error / RRE-RTE
@pytest.mark.parametrize("deg,t", [(0.0, (0.0, 0.0, 0.0)), (10.0, (1.0, 2.0, 2.0)), (90.0, (0.3, 0.4, 0.0))])
def test_pose_error_takes_two_poses(deg, t):
    est = (_rz(deg), np.array(t))
    gt = (np.eye(3), np.zeros(3))
    want_t = float(np.linalg.norm(t))
    r = fs.ledger.pose_error(est, gt)
    assert abs(r["rotation_deg"] - deg) < 1e-9 and abs(r["translation"] - want_t) < 1e-12
    # (R, t, info) triples (ICP / FPFH / spin) and 4x4 transforms are poses too
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = _rz(deg), t
    for e in ((est[0], est[1], {"rms": 0.0}), T, {"R": est[0], "t": est[1]}):
        r2 = fs.ledger.pose_error(e, gt)
        assert abs(r2["rotation_deg"] - deg) < 1e-9 and abs(r2["translation"] - want_t) < 1e-12
    # the old 4-argument form is unchanged
    r4 = fs.ledger.pose_error(est[0], est[1], gt[0], gt[1])
    assert r4 == r


def test_pose_error_chains_from_icp():
    rng = np.random.default_rng(3)
    src = rng.uniform(-1, 1, (400, 3)) * [1.0, 0.6, 0.3]
    R, t = _rz(5.0), np.array([0.05, -0.02, 0.01])
    dst = src @ R.T + t
    pose = fs.ledger.icp_point2point_3d(src, dst, iters=60)
    r = fs.ledger.pose_error(pose, (R, t))
    assert r["rotation_deg"] < 1e-4 and r["translation"] < 1e-5


@pytest.mark.parametrize("bad", [np.ones((3, 3)), (np.eye(3), np.zeros(2)), np.diag([1.0, 1.0, 1.0, 2.0]),
                                 (np.eye(3), np.array([np.nan, 0.0, 0.0])), "pose"])
def test_pose_error_is_fail_closed(bad):
    with pytest.raises(ValueError):
        fs.ledger.pose_error(bad, (np.eye(3), np.zeros(3)))


def test_rotation_translation_error_is_a_named_table_and_takes_poses():
    import registration_eval
    R, t = _rz(25.0), np.array([0.1, -0.05, 4.0])
    T = registration_eval.make_transform(R, t)
    want = {"rre_deg": 25.0, "rte": float(np.linalg.norm(t))}
    for gt, est in ((np.eye(4), T), ((np.eye(3), np.zeros(3)), (R, t, {})), (np.eye(4).tolist(), T.tolist())):
        r = fs.ledger.rotation_translation_error(gt, est)
        assert set(r) == {"rre_deg", "rte"}
        assert abs(r["rre_deg"] - want["rre_deg"]) < 1e-9 and abs(r["rte"] - want["rte"]) < 1e-12
    # the raw function keeps its tuple return
    assert isinstance(registration_eval.rotation_translation_error(np.eye(4), T), tuple)
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz as cf
    import ops3d
    assert ops3d.OPS3D["rotation_translation_error"]["out"] == "table"
    assert cf.TYPE_CHECKS["table"](ops3d.call("rotation_translation_error", np.eye(4), T))


def test_pose_doors_keep_one_identity():
    import metrics3d
    import ops3d
    import registration_eval
    assert inspect.unwrap(ops3d.OPS3D["pose_error"]["func"]) is metrics3d.pose_error
    assert inspect.unwrap(ops3d.OPS3D["rotation_translation_error"]["func"]) is registration_eval.rotation_translation_error
    assert list(inspect.signature(ops3d.OPS3D["pose_error"]["func"]).parameters) == ["pose_est", "pose_gt"]


# --------------------------------------------------------------------------- RSS
def _lemma2(v_r, v_f, rho=1.0, a=3.5, bmin=4.0, bmax=8.0):
    return max(v_r * rho + 0.5 * a * rho ** 2 + (v_r + a * rho) ** 2 / (2 * bmin) - v_f ** 2 / (2 * bmax), 0.0)


@pytest.mark.parametrize("v_r,v_f", [(20.0, 15.0), (25.0, 10.0), (5.0, 30.0)])
def test_rss_same_takes_the_table_first(v_r, v_f):
    p = fs.ledger.rss_params()
    want = _lemma2(v_r, v_f)                                     # Shalev-Shwartz 2017, Lemma 2
    assert abs(fs.ledger.rss_longitudinal_same(p, v_rear=v_r, v_front=v_f) - want) < 1e-9
    assert abs(fs.ledger.rss_longitudinal_same(p, v_r, v_f) - want) < 1e-9
    assert abs(fs.ledger.rss_longitudinal_same(v_r, v_f, p) - want) < 1e-9          # old order
    chk = fs.ledger.rss_longitudinal_check(p, d=50.0, v_rear=v_r, v_front=v_f)
    assert abs(chk["safe_distance"] - want) < 1e-9 and abs(chk["margin"] - (50.0 - want)) < 1e-9
    assert chk["dangerous"] == (not 50.0 > want)


_RSS_CALLS = {
    "rss_longitudinal_same": ((20.0, 15.0), "p"), "rss_longitudinal_opposite": ((20.0, -15.0), "p1"),
    "rss_lateral": ((0.5, -0.3), "p1"), "rss_longitudinal_check": ((50.0, 20.0, 15.0), "p"),
    "rss_lateral_check": ((1.5, 0.5, -0.3), "p1"), "rss_worst_case_gap": ((50.0, 20.0, 15.0), "p"),
    "rss_worst_case_gap_opposite": ((200.0, 20.0, -15.0), "p1"),
    "rss_worst_case_gap_lateral": ((1.5, 0.5, -0.3), "p1"),
}


@pytest.mark.parametrize("name", sorted(_RSS_CALLS))
def test_every_rss_table_op_takes_the_table_first(name):
    import rsssafety
    args, pname = _RSS_CALLS[name]
    p = fs.ledger.rss_params()
    raw = getattr(rsssafety, name)(*args, **{pname: p})
    new = fs.ledger[name](p, *args)
    old = fs.ledger[name](*args, **{pname: p})
    assert repr(new) == repr(raw) and repr(old) == repr(raw)
    fn = fs.ledger[name].raw
    assert _first_param(fn) == pname and inspect.unwrap(fn) is getattr(rsssafety, name)
    with pytest.raises(TypeError, match="both"):
        fs.ledger[name](p, *args, **{pname: p})


def test_rss_raw_functions_are_unchanged():
    import rsssafety
    assert _first_param(rsssafety.rss_longitudinal_same) == "v_rear"
    assert _first_param(rsssafety.rss_longitudinal_check) == "d"
