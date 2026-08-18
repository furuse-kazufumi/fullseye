"""evis 歩行知覚パイプライン(Fullseye terrain/locomotion 連鎖)の回帰テスト。"""
from __future__ import annotations

import warnings

import numpy as np

warnings.simplefilter("ignore")
import spikes.evis_walk_perception as W  # noqa: E402


def test_terrain_and_perception_chain():
    cloud = W.evis_terrain(seed=0)
    assert cloud.shape[1] == 3 and len(cloud) > 5000
    P = W.perceive(cloud)
    assert P["grid"].ndim == 2
    assert 0.0 <= float(np.asarray(P["trav"]).mean()) <= 1.0
    assert 0.0 <= float(np.nanmax(P["score"])) <= 1.0
    assert len(P["cands"]) > 0                      # 踏み場が見つかる
    for c in P["cands"]:
        assert 0 <= c["score"] <= 1 and len(c["xy"]) == 2


def test_footholds_avoid_obstacle():
    """踏み場候補は障害物(0.55,1.5 付近)を避ける。"""
    P = W.perceive(W.evis_terrain(seed=0))
    for c in P["cands"]:
        d = np.hypot(c["xy"][0] - 0.55, c["xy"][1] - 1.5)
        assert d > 0.12                             # 障害物の近くには踏まない


def test_stance_stability():
    """4 足立脚の COM 余裕が計算でき、選ばれた立脚は安定(margin>0)。"""
    P = W.perceive(W.evis_terrain(seed=0))
    stance = W.plan_stance(P["cands"])
    assert stance is not None
    assert stance["support"]["area"] > 0
    assert stance["margin"] > 0                     # 重心が支持多角形内=静的安定


def test_export_plan(tmp_path):
    P = W.perceive(W.evis_terrain(seed=0))
    stance = W.plan_stance(P["cands"])
    out = tmp_path / "plan.json"
    W.export_plan(P, stance, out)
    import json
    plan = json.load(open(out, encoding="utf-8"))
    assert "footholds" in plan and len(plan["footholds"]) > 0
    assert plan["stance"]["stable"] is True
