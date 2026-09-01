# -*- coding: utf-8 -*-
"""**人が呼ぶ経路**と**自動で回す経路**を別の契約に分けた層の検査。

守りたいことは 3 つ:

1. 厳格な契約(既定)は**1 ミリも緩んでいない** —— 既存の呼び手とテストが
   そのまま動く。
2. 寛容な契約は**契約による拒否だけ**を飲み込み、**実バグは飲み込まない**。
   ここが崩れると、今回のセッションで見つけたような実バグ(空間 Wiener が
   画像を縮小していた件、Sinkhorn が間違った答えに収束していた件)が
   「測れなかった候補」に化けて、進化ループの中で静かに消える。
3. 代入する値の**向き**が指標ごとに正しい —— 「測れなかった候補が優秀な
   候補に勝つ」ことが起きない。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import colortransport as CT
import imgmetrics as M
import metriccontract as MC


# =========================================================================
# 1. 厳格な契約は緩んでいない
# =========================================================================

def test_the_refusal_type_is_both_a_value_error_and_a_runtime_error():
    """既存の呼び手が ``except ValueError`` でも ``except RuntimeError`` でも捕まる。

    拒否の実態が両方にまたがるため ―― 「``data_range`` が曖昧」は入力の話、
    「Sinkhorn が収束しなかった」は手続きの話。呼び手にとってはどちらも
    同じ「測れなかった」。
    """
    assert issubclass(MC.MetricContractError, ValueError)
    assert issubclass(MC.MetricContractError, RuntimeError)


def test_the_strict_path_still_raises_exactly_as_before():
    """既定の経路は fail-closed のまま。緩めていないことを型と文言で固定。"""
    with pytest.raises(ValueError, match=r"48\.13 dB"):
        M.data_range_of(np.linspace(0, 255, 9))
    with pytest.raises(MC.MetricContractError):
        M.data_range_of(np.linspace(0, 255, 9))

    a = np.random.default_rng(0).random((64, 64))
    with pytest.raises(RuntimeError, match="needs every axis to be at least"):
        M.ms_ssim(a, a.copy())            # ValueError だったものが RuntimeError でも捕まる


def test_sinkhorn_non_convergence_is_a_refusal_not_a_crash():
    """収束しないのは想定内の結末で、バグではない ―― だから拾える型にした。"""
    rng = np.random.default_rng(13)
    a = rng.random(10); a /= a.sum()
    b = rng.random(10); b /= b.sum()
    cost = rng.random((10, 10))
    with pytest.raises(RuntimeError, match="did not converge"):
        CT.sinkhorn(a, b, cost, reg=0.01, n_iter=2, tol=1e-15)
    with pytest.raises(MC.MetricContractError):
        CT.sinkhorn(a, b, cost, reg=0.01, n_iter=2, tol=1e-15)


# =========================================================================
# 2. 寛容な契約 —— 拒否は飲み込む、バグは飲み込まない
# =========================================================================

def test_attempt_turns_a_refusal_into_a_value_you_can_carry_around():
    bad = np.linspace(0, 255, 64).reshape(8, 8)
    att = MC.attempt(M.psnr, bad, bad.copy())
    assert att.ok is False
    assert att.value is None                  # 0 で埋めたりしない
    assert "48.13 dB" in att.reason
    assert att.metric == "psnr"
    assert not att                            # __bool__ は ok を見る


def test_attempt_returns_the_number_when_it_can():
    a = np.linspace(0, 1, 4096).reshape(64, 64)
    att = MC.attempt(M.psnr, a, np.clip(a + 0.02, 0, 1))
    assert att.ok and att.value == pytest.approx(M.psnr(a, np.clip(a + 0.02, 0, 1)))
    assert att.reason is None
    assert att


def test_attempt_does_not_swallow_a_real_bug():
    """ここが本丸 —— 素の例外は握り潰さず送出する。

    素朴に ``except Exception`` で包むと、今回のセッションで見つけたような
    実バグまで「測れなかった候補」に化けて消える。
    """
    def raises_plain_value_error(*_a, **_k):
        raise ValueError("numpy said something went wrong")

    def raises_type_error(*_a, **_k):
        raise TypeError("a genuine programming mistake")

    def raises_plain_runtime_error(*_a, **_k):
        raise RuntimeError("a solver blew up for an undocumented reason")

    for fn, exc in ((raises_plain_value_error, ValueError),
                    (raises_type_error, TypeError),
                    (raises_plain_runtime_error, RuntimeError)):
        with pytest.raises(exc):
            MC.attempt(fn, metric="psnr")


def test_attempt_treats_a_non_finite_result_as_not_measured():
    """NaN を「測れた」と言うと、平均や順位づけの中で静かに広がる。"""
    att = MC.attempt(lambda: float("nan"), metric="ssim")
    assert not att.ok and "nan" in att.reason.lower()

    att = MC.attempt(lambda: None, metric="ssim")
    assert not att.ok and "None" in att.reason


def test_infinite_psnr_stays_a_real_answer():
    """完全一致の PSNR は inf だが、それは「測れた」―― しかも最善の値。"""
    a = np.linspace(0, 1, 64).reshape(8, 8)
    att = MC.attempt(M.psnr, a, a.copy())
    assert att.ok and att.value == math.inf
    assert MC.value_or_worst(att) == math.inf


def test_attempt_all_keeps_going_after_one_pair_fails():
    good = np.linspace(0, 1, 1024).reshape(32, 32)
    bad = np.linspace(0, 255, 1024).reshape(32, 32)
    atts = MC.attempt_all(M.psnr, [(good, good.copy()), (bad, bad.copy()),
                                   (good, np.clip(good + 0.1, 0, 1))])
    assert [a.ok for a in atts] == [True, False, True]


# =========================================================================
# 3. 向き —— 測れなかったものが勝たない
# =========================================================================

def test_every_scalar_metric_in_the_ledgers_declares_its_direction():
    """**宣言の無い指標を足したらここが落ちる。** 黙って穴が空かないように。

    向きを推測して埋めると、``psnr`` を 0 で埋めた候補が実測 30 dB の候補に
    負けず、選抜がひっくり返る ―― しかも例外は出ない。
    """
    import opscolortransport
    import opsimgmetrics

    scalar_ops = set()
    for reg in (opsimgmetrics.OPSIMGMETRICS, opscolortransport.OPSCOLORTRANSPORT):
        scalar_ops |= {n for n, m in reg.items() if m["out"] == "scalar"}

    undeclared = sorted(scalar_ops - set(MC.DIRECTIONS))
    assert not undeclared, f"向きが宣言されていない指標: {undeclared}"


def test_no_direction_is_declared_for_something_that_does_not_exist():
    """逆向きの検査 —— **死んだ宣言**が溜まらないようにする。

    op を消したときに宣言だけ残ると、表を見た人が「その指標がある」と誤解する。
    台帳の op でないものは、``compare_images`` の報告に**実際に現れる鍵**で
    なければならない(実測で確かめる。名前を並べるだけにしない)。
    """
    import opscolortransport
    import opsimgmetrics

    ledger = set(opsimgmetrics.OPSIMGMETRICS) | set(opscolortransport.OPSCOLORTRANSPORT)

    rng = np.random.default_rng(9)
    rgb = rng.random((16, 16, 3))
    report_keys = set(M.compare_images(rgb, np.clip(rgb + 0.02, 0, 1), channel_axis=-1))

    orphan = sorted(set(MC.DIRECTIONS) - ledger - report_keys)
    assert not orphan, f"実在しない指標の向きが宣言されている: {orphan}"

    # 台帳外の宣言が「報告の鍵」であることを名指しで固定(偶然通らないように)
    assert "delta_e_2000_mean" in report_keys
    assert "delta_e_2000_mean" not in ledger


def test_direction_refuses_to_guess():
    with pytest.raises(MC.MetricContractError, match="no direction declared"):
        MC.direction("some_new_metric")


def test_worst_case_sits_on_the_correct_side():
    assert MC.worst_case("psnr") == -math.inf          # 大きいほど良い
    assert MC.worst_case("mse") == math.inf            # 小さいほど良い
    assert MC.worst_case("ssim") == -math.inf
    assert MC.worst_case("wasserstein_1d") == math.inf


def test_a_metric_that_is_not_an_ordering_axis_has_no_worst():
    """``compressed_size`` は良し悪しの軸ではない ―― 順位づけに使わせない。"""
    assert MC.direction("compressed_size") is None
    with pytest.raises(MC.MetricContractError, match="not an ordering axis"):
        MC.worst_case("compressed_size")


@pytest.mark.parametrize("metric", ["psnr", "ssim", "mse", "rmse", "ncd", "wasserstein_1d"])
def test_an_unmeasurable_candidate_can_never_beat_a_measured_one(metric):
    """この族の存在理由そのもの。有限の代用値ではこれが保証できない。"""
    failed = MC.Attempt(ok=False, value=None, reason="…", metric=metric)
    for real in (-1e9, -1.0, 0.0, 1e-9, 1.0, 42.0, 1e9):
        measured = MC.Attempt(ok=True, value=real, reason=None, metric=metric)
        assert MC.is_better(MC.value_or_worst(measured), MC.value_or_worst(failed), metric)


def test_ranking_puts_the_unmeasurable_last_in_both_directions():
    for metric, best in (("psnr", 40.0), ("mse", 0.001)):
        atts = [
            MC.Attempt(False, None, "…", metric),
            MC.Attempt(True, best, None, metric),
            MC.Attempt(True, 20.0 if metric == "psnr" else 0.5, None, metric),
        ]
        ranked = MC.rank_attempts(atts)
        assert ranked[0].value == best
        assert ranked[-1].ok is False


def test_ranking_two_different_metrics_together_is_refused():
    with pytest.raises(MC.MetricContractError, match="one metric at a time"):
        MC.rank_attempts([MC.Attempt(True, 1.0, None, "psnr"),
                          MC.Attempt(True, 2.0, None, "mse")])


def test_best_of_says_none_rather_than_naming_a_loser():
    """全滅を最悪値つきの候補として返すと、それが**選ばれてしまう**。"""
    atts = [MC.Attempt(False, None, "…", "psnr"), MC.Attempt(False, None, "…", "psnr")]
    assert MC.best_of(atts) is None
    assert MC.best_of([]) is None

    atts.append(MC.Attempt(True, 12.0, None, "psnr"))
    assert MC.best_of(atts).value == 12.0


def test_value_or_worst_only_takes_an_attempt():
    with pytest.raises(MC.MetricContractError, match="expected an Attempt"):
        MC.value_or_worst(3.0)


# =========================================================================
# 4. 実際の使い方どおりに一度通す
# =========================================================================

def test_a_sweep_over_candidates_of_mixed_validity_ranks_correctly():
    """進化ループが実際にやることを、そのままの形で一度通す。

    3 番目の候補だけ ``[0, 255]`` の float で、厳格な契約なら例外になる ――
    寛容な契約ではそれが「測れなかった」として最下位に落ち、**残りの候補は
    ふつうに比較される**。
    """
    rng = np.random.default_rng(3)
    ref = rng.random((48, 48))
    candidates = [
        np.clip(ref + 0.01 * rng.standard_normal((48, 48)), 0, 1),      # よく似ている
        np.clip(ref + 0.20 * rng.standard_normal((48, 48)), 0, 1),      # 似ていない
        ref * 255.0,                                                     # 契約違反
    ]
    atts = [MC.attempt(M.psnr, ref, c) for c in candidates]
    assert [a.ok for a in atts] == [True, True, False]

    ranked = MC.rank_attempts(atts)
    assert ranked[0].value > ranked[1].value > 0.0
    assert ranked[-1].ok is False
    assert MC.best_of(atts) is ranked[0]


def test_the_same_sweep_would_have_died_under_the_strict_contract():
    """分けた意味を数字で示す ―― 厳格な契約では 3 番目で止まる。"""
    ref = np.random.default_rng(4).random((32, 32))
    with pytest.raises(MC.MetricContractError):
        [M.psnr(ref, c) for c in (ref.copy(), ref * 255.0)]
