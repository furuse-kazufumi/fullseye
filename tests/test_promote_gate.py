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


# --------------------------------------------------------------------------- #
# 4. 未登録候補の判定(champion_to_macro からの入口)                            #
# --------------------------------------------------------------------------- #
def test_temp_op_is_always_removed_even_on_error():
    """判定のために本登録するのは順序が逆。一時 op は必ず外れる。"""
    from promote_gate import temp_op

    before = len(ops.REGISTRY)
    with temp_op(ops, "_probe_tmp_op", lambda v, a, b: v, "image", "image"):
        assert "_probe_tmp_op" in ops._BY_NAME and "_probe_tmp_op" in ops.RT
    assert "_probe_tmp_op" not in ops._BY_NAME
    assert "_probe_tmp_op" not in ops.RT
    assert len(ops.REGISTRY) == before
    # 例外で抜けても残さない
    with pytest.raises(RuntimeError):
        with temp_op(ops, "_probe_tmp_op", lambda v, a, b: v, "image", "image"):
            raise RuntimeError("boom")
    assert "_probe_tmp_op" not in ops._BY_NAME
    assert len(ops.REGISTRY) == before


def test_temp_op_refuses_to_shadow_an_existing_op():
    """既存 op を黙って差し替えない(判定中だけ挙動が変わる事故を防ぐ)。"""
    from promote_gate import temp_op

    with pytest.raises(ValueError, match="衝突"):
        with temp_op(ops, "gaussian", lambda v, a, b: v, "image", "image"):
            pass


def test_stages_runner_reproduces_the_pipeline_and_is_fail_soft():
    """凍結した stage 列が 1 op として動き、壊れても入力を返す(進化を止めない)。"""
    from promote_gate import stages_runner

    spec = [{"op": "gaussian", "a": 0.5, "b": 0.5},
            {"op": "sobel_mag", "a": 0.5, "b": 0.5}]
    fn = stages_runner(ops, spec)
    img = _probe_inputs("image")[0]
    got = fn(img, 0.9, 0.1)                      # a,b は凍結 = 結果に影響しない
    want = ops.run_stages(ops.decode_by_names(spec), img)
    assert np.allclose(got, want)
    assert np.allclose(fn(img, 0.1, 0.9), want), "a,b が凍結されていない"


# --------------------------------------------------------------------------- #
# 4. 0 割り(基準線 0 の課題で相対改善が跳ね上がる)の回帰                       #
#                                                                             #
# 実測 2026-09-02 (docs/ARTICLE_INTEGRATION_TODO.md D-2):                      #
#   vibration_map / 既存 video op は tb_temporal_bandpass 1 個で locked        #
#   スコアがちょうど 0.0000。denom = abs(0) + 1e-12 のせいで                    #
#   rel = +724476067514.2847 が出て、判定は PROMOTE。例外は出ないので誰も       #
#   気づかない ―― 「もっともらしく違う数字」の典型。                            #
# --------------------------------------------------------------------------- #
class _StubProb:
    """尺度だけを持つ最小の Problem 代用(_gain / _reference_scale 用)。"""

    unit = "corr"
    in_sort = "video"

    def __init__(self, hand=0.7, identity=0.0):
        self._hand, self._identity = hand, identity

    def make(self, n, size, seed):
        return {"n": n, "size": size, "seed": seed}

    def hand_stages(self):
        return ["HAND"]

    def score_stages(self, stages, data):
        return self._hand if stages else self._identity


_CFG = {"n_train": 6, "n_holdout": 6, "size": 96, "seed": 0}


def test_zero_baseline_no_longer_explodes_the_relative_gain():
    """基準線 0 で比を作らない。1e-12 を足していた頃は +7.2e+11 が出ていた。"""
    from promote_gate import _gain

    rel, absolute, improved, basis, scale, src = _gain(
        0.72448, 0.0, _StubProb(hand=0.72448), "p_zero_explode", _CFG, 20_000)

    assert rel is None, "比が定義できないのに数値を作ってはいけない"
    assert absolute == pytest.approx(0.72448)
    assert "undefined" in basis and "absolute" in basis
    assert improved is True                      # 既存語彙が届かない場所には届いている
    assert scale == pytest.approx(0.72448) and src == "hand"


def test_zero_baseline_still_rejects_a_gain_inside_the_noise_floor():
    """0 を上回りさえすれば通る、にはしない ―― 課題自身の尺度で足切りする。"""
    from promote_gate import MIN_RELATIVE_GAIN, _gain

    prob = _StubProb(hand=0.8)
    tiny = MIN_RELATIVE_GAIN * 0.8 * 0.5         # しきい値のちょうど半分
    rel, _, improved, _, _, _ = _gain(tiny, 0.0, prob, "p_zero_tiny", _CFG, 20_000)
    assert rel is None and improved is False

    big = MIN_RELATIVE_GAIN * 0.8 * 2.0
    _, _, improved2, _, _, _ = _gain(big, 0.0, prob, "p_zero_big", _CFG, 20_000)
    assert improved2 is True


def test_a_problem_nobody_can_score_is_not_promotable():
    """尺度そのものが 0(手も恒等も 0)なら判定材料が無い。fail-closed で通さない。"""
    from promote_gate import _gain

    rel, _, improved, basis, scale, src = _gain(
        1.0, 0.0, _StubProb(hand=0.0, identity=0.0), "p_no_scale", _CFG, 20_000)
    assert rel is None and improved is False
    assert "undefined" in basis and scale == 0.0 and src == "none"


def test_defined_ratios_keep_the_exact_old_formula():
    """非退化ケースの相対値は 1 つも動かさない(公開済みの +37.9% 等が変わらない)。"""
    from promote_gate import _gain

    rel, absolute, improved, basis, scale, src = _gain(
        1.379, 1.0, _StubProb(), "p_defined", _CFG, 20_000)
    assert rel == pytest.approx(0.379)
    assert absolute == pytest.approx(0.379)
    assert basis == "relative" and improved is True
    assert scale == pytest.approx(1.0) and src == "best_existing"


def test_undefined_ratios_are_excluded_from_the_relative_aggregates():
    """1 件の 0 割りで best/mean relative gain が汚染されないこと(実データで)。"""
    import types

    import problems
    from promote_gate import counterfactual_utility, decide

    shim = types.SimpleNamespace(
        PROBLEMS={"vibration_map": problems.PROBLEMS["vibration_map"]})
    u = counterfactual_utility(ops, shim, "tb_temporal_band_power", 0.5, 0.5)

    row = u["per_problem"][0]
    assert row["best_existing"] == 0.0            # 0 割りが起きる条件そのもの
    assert row["relative_gain"] is None
    assert row["absolute_gain"] > 0.5
    assert u["problems_with_undefined_ratio"] == 1
    assert u["problems_with_defined_ratio"] == 0
    assert u["best_relative_gain"] == 0.0         # 旧実装ではここが 724476067514.28
    assert u["mean_relative_gain"] == 0.0
    assert u["best_absolute_gain"] > 0.5

    ok, reason = decide(u, None, library_size=0)
    assert ok and "absolute gain" in reason and "undefined" in reason
    assert "724476067514" not in reason
