"""Tote-picking benchmark gates that remain meaningful without MuJoCo assets."""
from __future__ import annotations

import numpy as np

import totepick as T


def test_deterministic_and_paired_seeds():
    a = T.run_benchmark(30, seed=7)
    b = T.run_benchmark(30, seed=7)
    assert a == b
    for trial in range(30):
        rows = [r for r in a["rows"] if r["trial"] == trial]
        assert len(rows) == 3
        assert len({r["scene_seed"] for r in rows}) == 1
        assert {r["method"] for r in rows} == set(T.METHODS)


def test_success_is_truth_inside_and_still_not_attachment():
    r = T.run_benchmark(40, seed=9)
    assert r["contact"]["adhesion"] is False
    assert "weld" not in repr(r).lower()
    successes = [a for row in r["rows"] for a in row["attempts"] if a["success"]]
    assert successes
    assert all(a["truth_inside"] and a["truth_speed_m_s"] < .03 for a in successes)


def test_tactile_is_one_replaceable_boundary_and_detects_slip():
    safe = T.read_fingertip_tactile(10, 1, .5, (0, 0))
    slip = T.read_fingertip_tactile(2, 2, .2, (0, 0))
    assert not safe.slipping and slip.slipping


def test_retry_curves_wilson_and_nontrivial_difficulty():
    s = T.summarize(T.run_benchmark(300, seed=20261030))
    for m in T.METHODS:
        rates = [x["rate"] for x in s["curves"][m]]
        assert rates == sorted(rates)
        assert rates[-1] < 1
        assert all(lo <= x["rate"] <= hi for x in s["curves"][m] for lo, hi in [x["wilson95"]])
    assert len(set(round(s["by_product"][T.METHODS[0]][p.name]["rate"], 3) for p in T.PRODUCTS)) > 2


def test_depth_candidate_uses_existing_blob_op():
    depth = np.ones((40, 50))
    depth[5:13, 7:17] = .4
    depth[20:33, 28:43] = .6
    candidates = T.depth_grasp_candidates(depth)
    assert len(candidates) == 2
    assert candidates[0]["score"] >= candidates[1]["score"]


def test_missing_menagerie_is_an_explicit_skip_not_benchmark_pass(tmp_path):
    status = T.validate_mujoco_asset(tmp_path)
    assert status["skipped"] is True
    # The asset-independent benchmark still has substantive gates and outcomes.
    r = T.run_benchmark(12)
    assert any(a["failure"] for row in r["rows"] for a in row["attempts"])
