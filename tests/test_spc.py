# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""spc — 統計的工程管理 op の閉じた式の恒等式と fail-closed を検査する。

各 op は学習でなく標準・教科書の閉じた式なので、突き合わせる厳密な恒等式がある
(モジュール docstring の表)。乱数は「対称性の破れ」を隠すので(feedback:
random_test_data_hides_structural_defects)、恒等式は**構造を作った系列**で確かめる:
一定・ステップ・中心を仕様中点に置いた分布・平均行そのもの。
"""
from __future__ import annotations

import numpy as np
import pytest

import spc


# ---- Xbar-R 管理図 --------------------------------------------------------
def test_xbar_r_constants_are_iso8258():
    sg = np.random.default_rng(0).normal(10.0, 1.0, size=(20, 5))
    r = spc.spc_xbar_r(sg)
    assert (r["a2"], r["d3"], r["d4"]) == (0.577, 0.000, 2.115)


def test_xbar_r_in_control_on_stationary_data():
    sg = np.random.default_rng(1).normal(50.0, 2.0, size=(30, 4))
    r = spc.spc_xbar_r(sg)
    # 定常データは限界内に収まる(誤警報率は低いが 0 とは限らないので、大半が管理下)。
    assert len(r["out_of_control"]) <= 1


def test_xbar_r_catches_a_large_shift():
    rng = np.random.default_rng(2)
    sg = rng.normal(10.0, 1.0, size=(25, 5))
    sg[-2:] += 5.0
    r = spc.spc_xbar_r(sg)
    assert not r["in_control"]
    assert set(r["out_of_control"]) >= {23, 24}


def test_xbar_r_limits_are_symmetric_about_grand_mean():
    sg = np.random.default_rng(3).normal(0.0, 1.0, size=(40, 6))
    r = spc.spc_xbar_r(sg)
    assert r["xbar_ucl"] - r["xbar_cl"] == pytest.approx(r["xbar_cl"] - r["xbar_lcl"])
    assert r["r_lcl"] == 0.0            # n=6 は D3=0


@pytest.mark.parametrize("bad", [np.zeros(5), np.zeros((3, 1)), np.zeros((3, 11))])
def test_xbar_r_rejects_bad_shapes(bad):
    with pytest.raises(ValueError):
        spc.spc_xbar_r(bad)


# ---- CUSUM ----------------------------------------------------------------
def test_cusum_constant_at_target_stays_zero():
    r = spc.spc_cusum(np.full(50, 7.0), target=7.0, k=0.5, h=5.0)
    assert float(np.max(r["c_plus"])) == 0.0
    assert float(np.max(r["c_minus"])) == 0.0
    assert r["in_control"]


def test_cusum_step_accumulates_at_rate_d_minus_k():
    x = np.concatenate([np.zeros(5), np.full(20, 2.0)])
    r = spc.spc_cusum(x, target=0.0, k=0.5, h=1e9)     # h 無限大で警報させない
    slope = np.diff(r["c_plus"][6:])                    # ステップ後の傾き
    assert np.allclose(slope, 1.5)                      # d - k = 2 - 0.5


def test_cusum_symmetry_positive_and_negative_shift():
    up = np.concatenate([np.zeros(10), np.full(20, 1.5)])
    dn = np.concatenate([np.zeros(10), np.full(20, -1.5)])
    ru = spc.spc_cusum(up, target=0.0, k=0.5, h=5.0)
    rd = spc.spc_cusum(dn, target=0.0, k=0.5, h=5.0)
    assert np.allclose(ru["c_plus"], rd["c_minus"])
    assert ru["first_alarm"] == rd["first_alarm"]


@pytest.mark.parametrize("kw", [{"k": -1.0}, {"h": 0.0}, {"target": np.inf}])
def test_cusum_rejects_bad_params(kw):
    base = {"target": 0.0, "k": 0.5, "h": 5.0}
    base.update(kw)
    with pytest.raises(ValueError):
        spc.spc_cusum(np.arange(10.0), **base)


# ---- EWMA -----------------------------------------------------------------
def test_ewma_constant_at_target_stays_flat():
    r = spc.spc_ewma(np.full(30, 7.0), target=7.0, sigma=1.0)
    assert np.allclose(r["z"], 7.0)
    assert r["in_control"] and r["first_alarm"] == -1


def test_ewma_matches_the_recursion_exactly():
    rng = np.random.default_rng(3)
    x = rng.normal(0.0, 1.0, 40)
    lam = 0.25
    r = spc.spc_ewma(x, target=0.0, lam=lam, sigma=1.0)
    z = np.empty_like(x)
    prev = 0.0
    for i in range(x.size):
        prev = lam * x[i] + (1.0 - lam) * prev
        z[i] = prev
    assert np.allclose(r["z"], z)


def test_ewma_limits_widen_toward_the_asymptote():
    r = spc.spc_ewma(np.zeros(60), target=0.0, lam=0.2, L=3.0, sigma=1.0)
    assert np.all(np.diff(r["ucl"]) >= -1e-12)          # monotone non-decreasing
    assert r["ucl"][-1] == pytest.approx(r["ucl_inf"], abs=1e-3)
    assert r["ucl"][0] == pytest.approx(3.0 * np.sqrt((0.2 / 1.8) * (1 - 0.8 ** 2)), rel=1e-9)  # i=1 closed form


def test_ewma_lambda_one_reduces_to_shewhart_individuals():
    x = np.array([5.0, 8.0, 3.0, 6.0, 5.0])
    r = spc.spc_ewma(x, target=5.0, lam=1.0, L=3.0, sigma=1.0)
    assert np.allclose(r["z"], x)                       # no smoothing
    assert np.allclose(r["ucl"], 8.0) and np.allclose(r["lcl"], 2.0)  # constant target±L*sigma


def test_ewma_catches_small_sustained_shift_that_shewhart_misses():
    rng = np.random.default_rng(0)
    base = rng.normal(0.0, 1.0, 60)
    base[20:] += 0.8                                     # +0.8 sigma sustained drift
    r = spc.spc_ewma(base, target=0.0, lam=0.2, L=3.0, sigma=1.0)
    assert r["first_alarm"] != -1                        # EWMA alarms
    assert not np.any(np.abs(base) > 3.0)                # a 3-sigma Shewhart chart would not


@pytest.mark.parametrize("kw", [{"lam": 0.0}, {"lam": 1.5}, {"L": 0.0},
                                {"sigma": -1.0}, {"target": np.inf}])
def test_ewma_rejects_bad_params(kw):
    base = {"target": 0.0, "lam": 0.2, "L": 3.0, "sigma": 1.0}
    base.update(kw)
    with pytest.raises(ValueError):
        spc.spc_ewma(np.arange(10.0), **base)


def test_ewma_registered_in_opsspc_change_category():
    import opsspc
    assert "spc_ewma" in opsspc.list_ops("change")
    assert opsspc.get("spc_ewma") is spc.spc_ewma


# ---- 工程能力 -------------------------------------------------------------
def test_capability_centred_gives_cpk_equals_cp():
    x = np.array([9.0, 10.0, 11.0, 10.0, 9.0, 11.0, 10.0] * 6)
    x = x - x.mean() + 10.0                             # 中心 = 中点 10
    r = spc.spc_capability(x, 6.0, 14.0)
    assert r["cpk"] == pytest.approx(r["cp"])


def test_capability_off_centre_reduces_cpk_below_cp():
    x = np.random.default_rng(4).normal(10.0, 1.0, size=300)
    x = x - x.mean() + 12.0                             # 中心を上限寄りに
    r = spc.spc_capability(x, 6.0, 14.0)
    assert r["cpk"] < r["cp"]


def test_capability_cpk_never_exceeds_cp():
    rng = np.random.default_rng(5)
    for _ in range(20):
        x = rng.normal(rng.uniform(6, 14), rng.uniform(0.3, 2.0), size=100)
        r = spc.spc_capability(x, 6.0, 14.0)
        assert r["cpk"] <= r["cp"] + 1e-12


def test_capability_rejects_constant_series():
    with pytest.raises(ValueError):
        spc.spc_capability(np.full(20, 10.0), 6.0, 14.0)


def test_capability_rejects_inverted_limits():
    with pytest.raises(ValueError):
        spc.spc_capability(np.arange(10.0), 14.0, 6.0)


# ---- Hotelling T² ---------------------------------------------------------
def test_hotelling_mean_row_is_zero():
    data = np.random.default_rng(6).normal(0.0, 1.0, size=(50, 3))
    mu = data.mean(axis=0)
    t2 = spc.spc_hotelling_t2(np.vstack([data, mu]))["t2"][-1]
    assert abs(float(t2)) < 1e-9


def test_hotelling_ucl_matches_f_distribution():
    from scipy.stats import f as fdist
    data = np.random.default_rng(7).normal(0.0, 1.0, size=(40, 2))
    r = spc.spc_hotelling_t2(data, alpha=0.0027)
    m, p = 40, 2
    ucl = p * (m + 1.0) * (m - 1.0) / (m * (m - p)) * fdist.ppf(1 - 0.0027, p, m - p)
    assert r["ucl"] == pytest.approx(ucl)


def test_hotelling_catches_joint_outlier():
    rng = np.random.default_rng(8)
    data = rng.normal(0.0, 1.0, size=(60, 3))
    data[-1] += 8.0                                     # 全特徴を同時に飛ばす
    r = spc.spc_hotelling_t2(data)
    assert not r["in_control"]
    assert 59 in r["out_of_control"]


def test_hotelling_rejects_singular_covariance():
    a = np.random.default_rng(9).normal(0.0, 1.0, size=(30, 1))
    data = np.hstack([a, a])                            # 2 列が完全共線
    with pytest.raises(ValueError):
        spc.spc_hotelling_t2(data)


def test_hotelling_rejects_too_few_observations():
    with pytest.raises(ValueError):
        spc.spc_hotelling_t2(np.random.default_rng(10).normal(0, 1, size=(3, 4)))


# ---- 共通の fail-closed ---------------------------------------------------
@pytest.mark.parametrize("op,args", [
    ("spc_cusum", (np.array([np.nan, 1.0, 2.0]),)),
    ("spc_capability", (np.array([np.inf, 1.0]),)),
])
def test_non_finite_is_rejected(op, args):
    fn = getattr(spc, op)
    with pytest.raises(ValueError):
        if op == "spc_cusum":
            fn(*args, target=0.0)
        else:
            fn(*args, 0.0, 10.0)


def test_the_two_registries_agree():
    """★同じ問い(このモジュールは何を publish するか)に答える入口が 2 つある:
    `spc.SPC` と `opsspc` の台帳。一致を門にする。

    以前ここは `spc.SPC` を **4 op に固定**していた。ewma / msa / gum が入っても
    `spc.SPC` は手書きのまま 4 件で、この試験が**その古さを守っていた**(13 op 漏れ)。
    片方だけ直して穴が半分残る型なので、固定値でなく**両者の一致**を見る。
    """
    import opsspc
    assert set(spc.SPC) == set(opsspc.OPSSPC), sorted(
        set(spc.SPC) ^ set(opsspc.OPSSPC))
    assert len(spc.SPC) >= 17, len(spc.SPC)
    for name, fn in spc.SPC.items():
        assert callable(fn), name


# ---- MT 法(マハラノビス・タグチ) -----------------------------------------
# ★真値は導出した恒等式と**既存 op**。当てはめた数字を固定しない。
#   単位空間の MD² の平均はちょうど (n-1)/n で、教科書の「平均 1」を有限標本で
#   正確に言い直したもの。1.0 を固定する試験はどんな標本でも間違いになる。
def _correlated(n=200, seed=7):
    """相関のある正常データ。構造(上三角の混合行列)を作ってから雑音を通す。"""
    rng = np.random.default_rng(seed)
    mix = np.array([[1.0, 0.5, 0.0, 0.0],
                    [0.0, 1.0, 0.3, 0.0],
                    [0.0, 0.0, 1.0, 0.2],
                    [0.0, 0.0, 0.0, 1.0]])
    return rng.normal(size=(n, 4)) @ mix


def test_mt_unit_space_md_squared_averages_exactly_n_minus_one_over_n():
    """★中心の恒等式。標本ごとに違う値になるので、定数 1.0 を固定してはいけない。"""
    for n in (5, 37, 200):
        u = spc.spc_mt_unit_space(_correlated(n=n, seed=n))
        assert u["n"] == n
        assert u["md_sq_mean_exact"] == pytest.approx((n - 1) / n, rel=0, abs=0)
        # 浮動小数の丸めしか差が出ない(実測では 0 だった)。
        assert u["md_sq_mean"] == pytest.approx(u["md_sq_mean_exact"], abs=1e-12)


def test_mt_distance_is_hotelling_t2_over_p():
    """★既存 op を真値にする。標準化した行列では共分散 = 相関なので MD² = T²/p。"""
    a = _correlated()
    d = spc.spc_mt_distance(a)
    z = (a - a.mean(axis=0)) / a.std(axis=0, ddof=1)
    t = spc.spc_hotelling_t2(z)
    assert np.allclose(d["md_sq"], t["t2"] / a.shape[1], rtol=0, atol=1e-12)


def test_mt_is_invariant_to_per_feature_affine_rescaling():
    """単位を変えても距離は変わらない(標準化が尺度を消す)。対称性の門。"""
    a = _correlated()
    scale = np.array([1000.0, 0.001, 2.5, 7.0])      # 3 桁またぐ倍率を混ぜる
    offset = np.array([-50.0, 0.0, 1e4, 3.0])
    base = spc.spc_mt_distance(a)["md"]
    moved = spc.spc_mt_distance(a * scale + offset)["md"]
    assert np.allclose(base, moved, rtol=1e-9, atol=1e-9)


def test_mt_with_one_feature_is_the_absolute_z_score():
    """p=1 では相関行列が [[1]] なので MD = |z| ちょうど。"""
    x = np.array([[1.0], [2.0], [4.0], [8.0], [16.0]])
    md = spc.spc_mt_distance(x)["md"]
    z = (x[:, 0] - x[:, 0].mean()) / x[:, 0].std(ddof=1)
    assert np.allclose(md, np.abs(z), rtol=0, atol=1e-12)


def test_mt_with_independent_features_is_the_mean_square_z():
    """相関がほぼ無ければ R ≈ I なので MD² ≈ 平均(z²)。"""
    a = np.random.default_rng(3).normal(size=(4000, 3))
    d = spc.spc_mt_distance(a)
    z = (a - a.mean(axis=0)) / a.std(axis=0, ddof=1)
    assert np.allclose(d["md_sq"], np.mean(z ** 2, axis=1), rtol=0.05, atol=0.05)


def test_mt_flags_a_row_pushed_outside_the_unit_space():
    """単位空間を作ってから、外れた 1 行を入れて検出されることを見る。"""
    a = _correlated()
    u = spc.spc_mt_unit_space(a)
    probe = np.vstack([a[:3], a.mean(axis=0) + 12.0 * a.std(axis=0, ddof=1)])
    d = spc.spc_mt_distance(probe, mean=u["mean"], std=u["std"],
                            inv_corr=u["inv_corr"], threshold=3.0)
    assert d["flagged"].tolist() == [3], (d["md"], d["flagged"])
    assert d["md"][3] > 3.0 * d["md"][:3].max()


def test_mt_unit_space_reports_a_feature_with_no_spread():
    """潰れた列は距離に 1 も寄与させず、**数えて報告する**(黙って無視しない)。"""
    a = _correlated()
    a = np.hstack([a, np.full((a.shape[0], 1), 4.2)])     # 動かないセンサー 1 本
    # ★この列の std は **0 ではない**。4.2 を 200 個並べただけで丸め屑が 1.3e-14
    #   残る(実測)。`std == 0.0` で判定していた最初の版はここを取りこぼし、
    #   その屑で割った距離が意味を失っていた。屑が在ることを門に書いておく ——
    #   絶対判定に戻したらこの行が落ちる。
    dust = a[:, -1].std(ddof=1)
    assert dust != 0.0 and dust < 1e-12, dust
    u = spc.spc_mt_unit_space(a)
    assert u["flat_features"] == 1
    assert u["p"] == 5
    # 潰れた列を外した 4 列の MD と一致する = その列は何も足していない。
    assert np.allclose(u["md"] ** 2 * 5.0,
                       spc.spc_mt_distance(a[:, :4])["md_sq"] * 4.0,
                       rtol=0, atol=1e-10)


def test_mt_sn_ratio_of_a_constant_distance_is_twenty_log10():
    """★SN 比の閉じた式。MD が一定 d なら η = 20 log10(d) ちょうど。"""
    for d in (1.0, 3.0, 10.0, 31.62277660168379):
        r = spc.spc_mt_sn_ratio(np.full(9, d))
        assert r["sn_ratio_db"] == pytest.approx(20.0 * np.log10(d), abs=1e-12)
        assert r["n"] == 9


def test_mt_sn_ratio_is_dragged_down_by_one_unseparated_sample():
    """逆二乗平均なので、1 本でも近い標本があれば点は落ちる(意図した挙動)。"""
    good = spc.spc_mt_sn_ratio(np.full(4, 10.0))["sn_ratio_db"]
    one_near = spc.spc_mt_sn_ratio(np.array([10.0, 10.0, 10.0, 1.0]))["sn_ratio_db"]
    assert one_near < good - 5.0, (good, one_near)


# ---- MT 法の fail-closed --------------------------------------------------
def test_mt_rejects_a_unit_space_given_only_in_part():
    """★一部だけ渡されたら拒む。残りを検査対象から推定すると、ずれた束が
    自分を正常と採点してしまう(最も危ない失敗の仕方)。"""
    a = _correlated(n=20)
    u = spc.spc_mt_unit_space(a)
    with pytest.raises(ValueError, match="together"):
        spc.spc_mt_distance(a, mean=u["mean"])
    with pytest.raises(ValueError, match="together"):
        spc.spc_mt_distance(a, mean=u["mean"], std=u["std"])


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_mt_rejects_a_non_positive_threshold(bad):
    with pytest.raises(ValueError):
        spc.spc_mt_distance(_correlated(n=20), threshold=bad)


def test_mt_rejects_non_two_dimensional_data():
    with pytest.raises(ValueError):
        spc.spc_mt_unit_space(np.arange(10.0))
    with pytest.raises(ValueError):
        spc.spc_mt_distance(np.arange(10.0))


def test_mt_rejects_a_single_observation():
    with pytest.raises(ValueError):
        spc.spc_mt_unit_space(np.array([[1.0, 2.0]]))
    with pytest.raises(ValueError):
        spc.spc_mt_distance(np.array([[1.0, 2.0]]))


def test_mt_rejects_a_unit_space_whose_shape_disagrees():
    a = _correlated(n=20)
    u = spc.spc_mt_unit_space(a)
    with pytest.raises(ValueError):
        spc.spc_mt_distance(a[:, :3], mean=u["mean"], std=u["std"],
                            inv_corr=u["inv_corr"])


def test_mt_rejects_a_zero_standard_deviation_in_a_given_unit_space():
    a = _correlated(n=20)
    u = spc.spc_mt_unit_space(a)
    std = u["std"].copy()
    std[1] = 0.0
    with pytest.raises(ValueError, match="positive"):
        spc.spc_mt_distance(a, mean=u["mean"], std=std, inv_corr=u["inv_corr"])


@pytest.mark.parametrize("bad", [np.array([1.0, 0.0, 2.0]), np.array([-1.0, 2.0])])
def test_mt_sn_ratio_rejects_a_non_positive_distance(bad):
    with pytest.raises(ValueError):
        spc.spc_mt_sn_ratio(bad)


def test_mt_rejects_non_finite_input():
    with pytest.raises(ValueError):
        spc.spc_mt_unit_space(np.array([[1.0, 2.0], [np.nan, 3.0]]))
    with pytest.raises(ValueError):
        spc.spc_mt_sn_ratio(np.array([1.0, np.inf]))
