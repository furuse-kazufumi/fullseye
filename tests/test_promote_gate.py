# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""昇格ゲート(tools/promote_gate)の契約テスト。

合成 op を語彙へ足す判断は**一方通行**に近い: 悪い op が 1 本入ると、それを引く
将来の探索すべてが汚染される。だからゲートは厳しい側へ倒してあり、その厳しさ
自体を回帰テストで固定する。

判定の 3 本柱(いずれも先行研究由来。詳細は tools/promote_gate の docstring):
  1. counterfactual utility — 「強い」ではなく「**既存語彙では届かない**」ことを問う
  2. 振る舞いによる重複排除 — 同義 op の乱立を防ぐ
  3. capacity bound — 無制限の昇格は一般化保証を壊す
"""
import sys

import numpy as np
import pytest

pytest.importorskip("scipy")

sys.path.insert(0, "tools")

import ops                                    # noqa: E402
from promote_gate import (DNA_CAPACITY, MIN_RELATIVE_GAIN, _probe_inputs,  # noqa: E402
                          _same_behaviour, decide, find_behavioural_duplicate)


def _util(evaluated=10, improved=1, best=0.05):
    return {"problems_evaluated": evaluated, "problems_improved": improved,
            "best_relative_gain": best, "mean_relative_gain": best / 2,
            "per_problem": [], "utility_method": "test", "split": "locked"}


# --------------------------------------------------------------------------- #
# 1. 判定ロジック(decide)— 却下条件が全部効いていること                        #
# --------------------------------------------------------------------------- #
def test_promotes_when_it_reaches_where_existing_ops_cannot():
    ok, reason = decide(_util(improved=2, best=0.05), None, library_size=4)
    assert ok and "improves 2" in reason


def test_rejects_behavioural_duplicate():
    ok, reason = decide(_util(improved=5, best=0.9), "gaussian", library_size=0)
    assert not ok and "duplicate" in reason and "gaussian" in reason


def test_rejects_when_no_problem_improves_beyond_noise_floor():
    """既存最良をわずかに上回るだけ = 測定誤差。通さない。"""
    ok, reason = decide(_util(improved=0, best=MIN_RELATIVE_GAIN / 2), None, 0)
    assert not ok and "noise floor" in reason


def test_rejects_when_workload_cannot_evaluate_the_sort():
    ok, reason = decide(_util(evaluated=0, improved=0, best=0.0), None, 0)
    assert not ok and "in_sort" in reason


def test_capacity_bound_blocks_unbounded_growth():
    """上限に達したら、良い候補でも押し出しを要求する(黙って増やさない)。"""
    ok, reason = decide(_util(improved=9, best=2.0), None,
                        library_size=DNA_CAPACITY, capacity=DNA_CAPACITY)
    assert not ok and "capacity" in reason
    # 1 つ空けば通る
    ok2, _ = decide(_util(improved=9, best=2.0), None,
                    library_size=DNA_CAPACITY - 1, capacity=DNA_CAPACITY)
    assert ok2


# --------------------------------------------------------------------------- #
# 2. 振る舞いによる重複検出                                                     #
# --------------------------------------------------------------------------- #
def test_exact_clone_is_detected_as_duplicate():
    src = ops._BY_NAME["gaussian"]

    def clone(v, a, b):
        return src.fn(v, a, b)

    assert find_behavioural_duplicate(ops, clone, "image", limit=60) == "gaussian"


def test_slightly_different_op_is_not_a_duplicate():
    """0.1% ずれたら別物 — 重複判定が雑だと本物の発見を捨ててしまう。"""
    src = ops._BY_NAME["gaussian"]

    def tweak(v, a, b):
        return src.fn(v, a, b) * 0.999

    assert find_behavioural_duplicate(ops, tweak, "image", limit=60) is None


def test_duplicate_needs_agreement_on_every_probe():
    """1 枚だけ偶然一致しても重複にしない(プローブ全件一致が条件)。"""
    src = ops._BY_NAME["gaussian"]
    probes = _probe_inputs("image")
    calls = {"n": 0}

    def only_first_matches(v, a, b):
        calls["n"] += 1
        return src.fn(v, a, b) if calls["n"] == 1 else np.zeros_like(np.asarray(v))

    assert find_behavioural_duplicate(ops, only_first_matches, "image", limit=40) is None
    assert len(probes) >= 2, "プローブが 1 枚だとこの契約を検証できない"


def test_same_behaviour_handles_mismatched_types_without_crashing():
    assert not _same_behaviour(np.zeros((4, 4)), "not-an-array")
    assert not _same_behaviour(np.zeros((4, 4)), np.zeros((8, 8)))
    assert _same_behaviour(3.0, 3.0)


# --------------------------------------------------------------------------- #
# 3. プローブ集合そのものの健全性                                               #
# --------------------------------------------------------------------------- #
def test_probes_are_deterministic_and_non_degenerate():
    """プローブが定数だと「全部同じ」に見えて重複判定が崩壊する。"""
    for sort in ("image", "volume", "points", "signal", "matrix", "cimage"):
        a, b = _probe_inputs(sort), _probe_inputs(sort)
        assert len(a) >= 2
        for x, y in zip(a, b):
            assert np.array_equal(x, y), f"{sort}: プローブが非決定的"
        assert float(np.std(np.abs(a[0]))) > 1e-6, f"{sort}: プローブが定数"
        assert not np.array_equal(a[0], a[1]), f"{sort}: プローブに多様性が無い"
