# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""dic — 真値で検算するテスト。

方針:
  * **合成器は作らない。** 真値つきの画像対は `pivops.piv_synth_pair` が既に
    正しく作る(粒子を動かしてから描き直す / 正規化しない / callable の
    変位場を受ける)ので、この層はそれを使う。テストが `pivops` を踏むのは
    「重複ではなく上乗せである」ことを実行で示すためでもある。
  * ひずみの側は **画像を 1 枚も使わない**。厳密な剛体回転の変位場を直接
    入れて代数の恒等式(Green-Lagrange が 0)を確かめる —— ここの許容差
    だけは実測ではなく倍精度の限界。
  * 許容差は**実測した値**から取る。丸い数字を希望で書かない。各テストの
    docstring に実測値を残す。
  * fail-closed を「例外が出ること」だけでなく**文言**でも確かめる。
"""
import math

import numpy as np
import pytest

import dic as D
import pivops as PV

N = 256
MARGIN = 40
SEED = 7
S = (slice(MARGIN, N - MARGIN), slice(MARGIN, N - MARGIN))


def _rigid_rotation_field(n, deg, spacing=1.0):
    """厳密な剛体回転の変位場。``u = (cosθ-1)x - sinθ·y``, ``v = sinθ·x + (cosθ-1)y``。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    yy *= spacing
    xx *= spacing
    t = math.radians(deg)
    ct, st = math.cos(t), math.sin(t)
    return (ct - 1.0) * xx - st * yy, st * xx + (ct - 1.0) * yy, ct - 1.0


@pytest.fixture(scope="module")
def pair():
    """真値つきの粒子画像対(x に 0.37 px の一様並進)と、その piv 変位場。"""
    a, b, truth = PV.piv_synth_pair((N, N), (0.0, 0.37), density=0.02,
                                    diameter_px=3.0, seed=SEED)
    flow, info = PV.piv_cross_correlate(a, b, window=32, overlap=0.75)
    return a, b, truth, flow, info


# =========================================================================== #
# strain_from_displacement                                                    #
# =========================================================================== #
@pytest.mark.parametrize("deg", [0.5, 2.0, 5.0])
def test_green_lagrange_is_exactly_zero_under_rigid_rotation(deg):
    """★★画像を 1 枚も使わない代数の恒等式 —— この op が存在する理由。

    厳密な剛体回転の変位場を直接入れる。Green-Lagrange は
    ``exx = (cosθ-1) + ½((cosθ-1)² + sin²θ) = 0`` が**代数的に厳密**なので、
    許容差 1e-9 は実測から決めた値ではなく**倍精度で到達できる限界**。
    実測は 0.5 / 2 / 5 度で 5.7e-14 / 8.7e-14 / 3.9e-13。
    微小ひずみのほうは ``cosθ-1`` を返す(実測の差 4.7e-14 / 5.4e-14 /
    3.6e-13、許容差 1e-6)。

    同じ入力から 2 つの違う答えが出るという事実が、``method`` に既定値を
    置かない理由そのもの。5 度では微小ひずみが **-3805 µε** の嘘を返す。
    """
    n = 96
    u, v, ct_minus_1 = _rigid_rotation_field(n, deg)

    exx, eyy, exy = D.strain_from_displacement(u, v, 21, "green")
    assert float(np.max(np.abs(exx))) < 1e-9
    assert float(np.max(np.abs(eyy))) < 1e-9
    assert float(np.max(np.abs(exy))) < 1e-9

    exx, eyy, exy = D.strain_from_displacement(u, v, 21, "infinitesimal")
    assert float(np.max(np.abs(exx - ct_minus_1))) < 1e-6
    assert float(np.max(np.abs(eyy - ct_minus_1))) < 1e-6
    assert float(np.max(np.abs(exy))) < 1e-6
    assert abs(ct_minus_1) > 3.8e-5          # 0.5 度でも 38 µε の嘘がある


@pytest.mark.parametrize("deg", [0.5, 2.0, 5.0])
def test_pivops_velocity_gradient_carries_the_rotation_artefact(deg):
    """★既存 op が「同じ嘘を持つ」ことを固定する —— 重複でない根拠。

    `piv_velocity_gradient["dudx"]` は厳密な剛体回転で ``cosθ-1`` を返し、
    `piv_strain_rate` は ``2|cosθ-1|`` を返す(2 度で +1218 µε)。どちらも
    真のひずみが 0 の運動に対しての値。この振る舞いが変わったら
    `strain_from_displacement` の存在理由が変わるので、ここで見張る。
    """
    n = 41
    step = 8.0
    u, v, ct_minus_1 = _rigid_rotation_field(n, deg, spacing=step)
    flow = np.stack([v, u])                              # pivops は (dy, dx)
    vg = PV.piv_velocity_gradient(flow, spacing=step)
    assert float(np.mean(vg["dudx"])) == pytest.approx(ct_minus_1, rel=1e-6)
    sr = PV.piv_strain_rate(flow, spacing=step)
    assert float(np.mean(sr)) == pytest.approx(2.0 * abs(ct_minus_1), rel=1e-6)
    # 同じ入力に対して green は 0。
    green = D.strain_from_displacement(u, v, 5, "green", spacing=step)[0]
    assert float(np.max(np.abs(green))) < 1e-9


def test_uniform_strain_is_recovered_exactly():
    """一様ひずみの変位場 ``u = ε x`` から ``exx = ε`` が厳密に戻る。

    対称窓の最小二乗は 1 次関数の傾きを厳密に返すので、これも代数の検算
    (実測の最大差 5.3e-15)。微小ひずみと Green の差は ``½ε²`` で、ε=0.02 なら
    **200 µε** —— 2 % のひずみでは定義の違いが 1 % 効く。
    """
    n = 96
    eps = 0.02
    _, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    u = eps * xx
    v = np.zeros_like(u)
    exx_i, eyy_i, exy_i = D.strain_from_displacement(u, v, 21, "infinitesimal")
    assert float(np.max(np.abs(exx_i - eps))) < 1e-12
    assert float(np.max(np.abs(eyy_i))) < 1e-12
    assert float(np.max(np.abs(exy_i))) < 1e-12
    exx_g, _, _ = D.strain_from_displacement(u, v, 21, "green")
    assert float(np.max(np.abs(exx_g - (eps + 0.5 * eps * eps)))) < 1e-12


def test_spacing_makes_a_coarse_grid_give_the_same_strain():
    """★``spacing`` —— 窓格子の変位場をそのまま渡せるための引数。

    節点間隔 8 px の格子に載せた同じひずみ場は、``spacing=8`` を渡せば
    真値を厳密に返す(実測の最大差 3.2e-15)。``spacing`` を渡し忘れると
    ひずみがちょうど **8 倍**(0.005 → 0.040)になる —— 例外にならず
    もっともらしい数字が出るので、ここで固定する。
    """
    eps = 0.005
    _, xx = np.mgrid[0:40, 0:40].astype(np.float64)
    u = eps * (xx * 8.0)                       # 節点 j の x 座標は 8j px
    v = np.zeros_like(u)
    exx, _, _ = D.strain_from_displacement(u, v, 5, "infinitesimal", spacing=8.0)
    assert float(np.max(np.abs(exx - eps))) < 1e-12
    wrong, _, _ = D.strain_from_displacement(u, v, 5, "infinitesimal")
    assert float(np.mean(wrong)) == pytest.approx(8.0 * eps, rel=1e-9)


def test_least_squares_window_beats_central_difference_on_a_real_flow():
    """★★この op が `piv_velocity_gradient` の上に乗る理由(実測)。

    同じ piv 変位場から一様ひずみ 500 µε を読み戻すと、平均はどちらも真値
    どおりだが**散らばりが桁で違う**。実測(MARGIN 40 の内側、µε):

        piv_velocity_gradient   500.0 ± 136.9
        LS w=3                  499.7 ± 102.6   ( 1.3 倍)
        LS w=5                  498.9 ±  38.2   ( 3.6 倍)
        LS w=9                  500.0 ±  12.4   (11.1 倍)

    平均はどれも真値どおり。許容差は「``w=9`` が 5 倍以上良いこと」で、
    実測の 11.1 倍に対して 2.2 倍の余裕。
    """
    eps = 500e-6
    a, b, _ = PV.piv_synth_pair((N, N), lambda r, c: (0.0 * r, eps * c),
                                density=0.02, diameter_px=3.0, seed=SEED)
    flow, info = PV.piv_cross_correlate(a, b, window=32, overlap=0.75)
    step = float(info["step"])
    rows, cols = info["rows"], info["cols"]
    sl = np.ix_((rows >= MARGIN) & (rows <= N - MARGIN),
                (cols >= MARGIN) & (cols <= N - MARGIN))

    cd = PV.piv_velocity_gradient(flow, spacing=step)["dudx"][sl]
    ls = D.strain_from_displacement(flow[1], flow[0], 9, "infinitesimal",
                                    spacing=step)[0][sl]
    assert float(np.nanmean(cd)) == pytest.approx(eps, rel=0.05)
    assert float(np.nanmean(ls)) == pytest.approx(eps, rel=0.05)
    assert float(np.nanstd(ls)) < float(np.nanstd(cd)) / 5.0


def test_window_and_method_have_no_default():
    """★``window`` と ``method`` を省いた呼び出しは ``TypeError``。

    既定値を置かない設計そのものをテストで固定する。既定を足す変更が
    入ったらここが落ちる。
    """
    u = np.zeros((32, 32))
    v = np.zeros((32, 32))
    with pytest.raises(TypeError):
        D.strain_from_displacement(u, v)
    with pytest.raises(TypeError):
        D.strain_from_displacement(u, v, 11)


@pytest.mark.parametrize("method", ["", "engineering", "GREEN", "hencky", None, 0])
def test_unknown_strain_method_is_refused(method):
    """未知の ``method`` は黙って代用せず、選べる 2 つを挙げて拒否する。"""
    u = np.zeros((32, 32))
    v = np.zeros((32, 32))
    with pytest.raises(ValueError, match="infinitesimal"):
        D.strain_from_displacement(u, v, 11, method)


def test_passing_a_flow2d_array_as_u_is_refused_with_the_fix():
    """★★軸の取り違えを例外にする —— 黙って「もっともらしく間違う」経路を塞ぐ。

    `pivops` の ``flow2d`` は ``(dy, dx)``。``flow`` を丸ごと、あるいは
    ``flow[0]`` を ``u`` のつもりで渡す事故は、形が通ってしまうと**例外に
    ならずに x と y が入れ替わった答え**を返す。3 次元をそのまま渡した
    場合はここで捕まえ、正しい呼び方を文言で返す。
    """
    flow = np.zeros((2, 32, 32))
    with pytest.raises(ValueError, match=r"flow\[1\]"):
        D.strain_from_displacement(flow, flow[0], 11, "green")


def test_nan_displacement_propagates_to_nan_strain():
    """★NaN は 0 ではなく NaN のまま伝える。

    ``window=11`` の場に NaN を 1 点だけ置くと、ひずみ側で**ちょうど
    11x11 = 121 点**が NaN になる(実測)。0 と見なしていたら NaN は 0 点で、
    代わりに周囲へ本物に見える偽のひずみ勾配が立つ。
    """
    u, v, _ = _rigid_rotation_field(96, 2.0)
    u = u.copy()
    u[48, 48] = np.nan
    exx, eyy, exy = D.strain_from_displacement(u, v, 11, "green")
    for e in (exx, eyy, exy):
        assert int(np.isnan(e).sum()) == 121
    assert np.isnan(exx[48, 48])
    assert np.isfinite(exx[0, 0])
    # 穴の外は汚れていない(green はここでも 0 が真値)。
    assert float(np.max(np.abs(exx[np.isfinite(exx)]))) < 1e-9


@pytest.mark.parametrize("kwargs,match", [
    (dict(window=30, method="green"), "odd"),
    (dict(window=201, method="green"), "larger than the field"),
    (dict(window=11, method="green", spacing=0.0), "spacing"),
])
def test_strain_is_fail_closed(kwargs, match):
    """窓や節点間隔の指定が壊れていたら拒否する。"""
    u = np.zeros((64, 64))
    v = np.zeros((64, 64))
    with pytest.raises(ValueError, match=match):
        D.strain_from_displacement(u, v, **kwargs)


# =========================================================================== #
# correlation_quality                                                         #
# =========================================================================== #
def test_quality_is_one_for_a_perfect_match(pair):
    """変位 0 の場で同じ画像どうしを採点すると厳密に 1。

    ここが 1 でなければ規格化が壊れている。実測の最大偏差 **0.0**(厳密)。
    許容差 1e-12 は BLAS の実装差ぶんの逃げ。
    """
    a, _, _, _, _ = pair
    zero = np.zeros((2,) + a.shape)
    q = D.correlation_quality(a, a, zero, None, subset=31)
    inner = q[S]
    assert np.isfinite(inner).all()
    assert float(np.max(np.abs(inner - 1.0))) < 1e-12


def test_quality_localises_a_swapped_patch_where_peak_ratio_cannot(pair):
    """★★この op が存在する理由。局所的な破綻を **peak_ratio は見つけられない**。

    60x60 画素だけを無関係な模様に差し替えた実測:

        指標                  差し替え領域   健全領域   比
        peak_ratio               1.1838       1.3285   0.891  ← 分布が重なる
        correlation_quality      0.0998       0.9991   0.100  ← 10 倍差

    許容差は「差し替え領域の中央値 < 0.5」「健全領域の中央値 > 0.9」
    「peak_ratio の比は 0.8 より上(= 区別になっていない)」。
    最後の 1 本は **既存 op の弱点が残っていることを固定する**ためのもので、
    peak_ratio が将来改善されたらここが落ちて、この op の存在理由を
    見直す合図になる。
    """
    a, b, _, _, _ = pair
    rng = np.random.default_rng(1)
    occ = b.copy()
    occ[100:160, 100:160] = rng.uniform(0, float(b.max()), (60, 60))
    flow, info = PV.piv_cross_correlate(a, occ, window=32, overlap=0.75)
    q = D.correlation_quality(a, occ, flow, info, subset=31)

    inside = q[110:150, 110:150]
    outside = np.concatenate([q[50:90, 50:90].ravel(), q[180:220, 180:220].ravel()])
    assert float(np.nanmedian(inside)) < 0.5
    assert float(np.nanmedian(outside)) > 0.9

    pr = D._grid_to_pixels(info["peak_ratio"], np.asarray(info["rows"]),
                           np.asarray(info["cols"]), a.shape)
    pr_in = float(np.nanmedian(pr[110:150, 110:150]))
    pr_out = float(np.nanmedian(np.concatenate(
        [pr[50:90, 50:90].ravel(), pr[180:220, 180:220].ravel()])))
    assert pr_in / pr_out > 0.8


def test_quality_gate_cuts_the_error_of_a_locally_broken_field(pair):
    """★品質で切ると実際に誤差が減る(局所的な破綻の場合)。

    差し替えのある対で、変位誤差 RMS は全点 **1.9122 px**。

        門                  残る割合   誤差 RMS [px]
        なし                 100.0 %      1.9122
        zncc >= 0.5           87.2 %      0.0298
        zncc >= 0.8           82.8 %      0.0036   ← 537 倍改善
        peak_ratio >= 1.2     83.8 %      1.0952   ← 1.7 倍
        peak_ratio >= 1.3     58.4 %      0.9329   ← 4 割捨てて 2.0 倍

    許容差は「門ありの RMS が門なしの 1/20 未満」で、実測の 537 倍に対して
    27 倍の余裕(粒子の撒き方が変われば残る割合が動くため広く取る)。
    """
    a, b, _, _, _ = pair
    rng = np.random.default_rng(2)
    occ = b.copy()
    occ[100:160, 100:160] = rng.uniform(0, float(b.max()), (60, 60))
    flow, info = PV.piv_cross_correlate(a, occ, window=32, overlap=0.75)
    q = D.correlation_quality(a, occ, flow, info, subset=31)
    ri = np.clip(np.rint(info["rows"]).astype(int), 0, a.shape[0] - 1)
    ci = np.clip(np.rint(info["cols"]).astype(int), 0, a.shape[1] - 1)
    qg = q[np.ix_(ri, ci)]

    err = np.abs(flow[1] - 0.37)
    ok = np.isfinite(qg) & np.isfinite(err)
    rms_all = float(np.sqrt(np.mean(err[ok] ** 2)))
    keep = ok & (qg >= 0.8)
    rms_gate = float(np.sqrt(np.mean(err[keep] ** 2)))
    assert keep.sum() > 0.5 * ok.sum()
    assert rms_gate < rms_all / 20.0


def test_quality_is_invariant_to_gain_and_offset(pair):
    """★ゲイン 0.7・オフセット 0.15 を掛けても品質マップが動かない。

    ZNCC は平均と標準偏差の両方を割り引くので、アフィンな輝度変換に対して
    代数的に不変。実測の最大差 1.6e-14(倍精度の丸め)。許容差 1e-11。
    """
    a, b, _, flow, info = pair
    q1 = D.correlation_quality(a, b, flow, info, subset=31)
    q2 = D.correlation_quality(a, 0.7 * b + 0.15, flow, info, subset=31)
    d = np.abs(q1 - q2)
    assert float(np.nanmax(d)) < 1e-11


def test_quality_is_blind_to_sub_pixel_error(pair):
    """★★「品質が高い = 精度が高い」ではないことを固定する。

    真の変位 0.37 px の対に、わざと誤差を入れた場を採点した実測:

        誤差 [px]  0.00     0.05     0.10     0.25     0.50    1.00    2.00
        zncc 中央値 0.99931 0.99904 0.99822 0.99256 0.97389 0.89753 0.65318

    **0.05 px 間違えても差は 2.7e-4 しかない。** 1 px ずらして初めて
    0.898 まで落ちる。この op が測れるのは
    デコリレーションであって 0.01 px の精度ではない、という主張を
    数字で固定しておく —— 逆向きに読まれると危険な指標なので。
    """
    a, b, _, _, _ = pair
    shape = a.shape

    def q_for(err):
        fl = np.stack([np.zeros(shape), np.full(shape, 0.37 - err)])
        return float(np.nanmedian(D.correlation_quality(a, b, fl, None, subset=31)[S]))

    q0, q005, q1 = q_for(0.0), q_for(0.05), q_for(1.0)
    assert q0 > 0.999
    assert q0 - q005 < 1e-3          # 0.05 px の誤差はほぼ見えない
    assert q1 < 0.95                 # 1 px なら見える


def test_quality_marks_unmeasured_points_nan(pair):
    """★測っていない点は 0 でも 1 でもなく NaN。

    サブセットが画像からはみ出す縁(subset=31 なら外周 15 画素)と、
    変位が画像の外を指す点。実測: 外周 15 画素がすべて NaN。
    """
    a, b, _, _, _ = pair
    zero = np.zeros((2,) + a.shape)
    q = D.correlation_quality(a, b, zero, None, subset=31)
    assert np.isnan(q[:15, :]).all() and np.isnan(q[-15:, :]).all()
    assert np.isnan(q[:, :15]).all() and np.isnan(q[:, -15:]).all()
    assert np.isfinite(q[128, 128])

    far = np.zeros((2,) + a.shape)
    far[1] = 10_000.0                          # 画像の外を指す
    q2 = D.correlation_quality(a, b, far, None, subset=31)
    assert np.isnan(q2).all()


@pytest.mark.parametrize("kwargs,match", [
    (dict(subset=30), "odd"),
    (dict(subset=1), "at least 3"),
])
def test_quality_is_fail_closed_on_the_subset(pair, kwargs, match):
    a, b, _, flow, info = pair
    with pytest.raises(ValueError, match=match):
        D.correlation_quality(a, b, flow, info, **kwargs)


def test_quality_refuses_a_grid_flow_without_info(pair):
    """格子の変位場を ``info`` 無しで渡したら、直し方つきで拒否する。"""
    a, b, _, flow, _ = pair
    with pytest.raises(ValueError, match="info"):
        D.correlation_quality(a, b, flow, None, subset=31)


def test_quality_refuses_a_flow_that_does_not_match_info(pair):
    a, b, _, flow, info = pair
    with pytest.raises(ValueError, match="window grid"):
        D.correlation_quality(a, b, flow[:, :-3, :], info, subset=31)


def test_quality_refuses_a_non_flow2d_array(pair):
    a, b, _, _, _ = pair
    with pytest.raises(ValueError, match="flow2d"):
        D.correlation_quality(a, b, np.zeros(a.shape), None, subset=31)


# =========================================================================== #
# speckle_quality                                                             #
# =========================================================================== #
def test_mig_is_larger_for_a_fine_speckle():
    """★平均輝度勾配(MIG)は細かい斑点ほど大きい。

    ★ 密度を固定したまま直径だけ変えると被覆率も動いてしまい、``mig`` は
    単調にならない(`dic` の docstring の右表では d=4.0 で頭打ち)。
    ここは**被覆率をおおよそ揃える**ため密度を ``1/d²`` で合わせる。
    `piv_synth_particles`、``diameter_px`` 1.5 対 6.0 の実測:

        指標        細かい    粗い     比
        mig         0.1336   0.0452   2.96
        grad_rms    0.0947   0.0315   3.00
        推定直径      1.79     6.93   3.87(逆向き)
        coverage     0.053    0.074

    許容差は「2 倍以上」で、実測の 2.96 倍に対して 1.5 倍の余裕。
    """
    fine, _ = PV.piv_synth_particles((N, N), density=0.02, diameter_px=1.5, seed=3)
    coarse, _ = PV.piv_synth_particles((N, N), density=0.02 * (1.5 / 6.0) ** 2,
                                       diameter_px=6.0, seed=3)
    qf = D.speckle_quality(fine)
    qc = D.speckle_quality(coarse)
    assert qf["mig"] > 2.0 * qc["mig"]
    assert qf["grad_rms"] > 2.0 * qc["grad_rms"]
    assert qc["mean_blob_diameter_px"] > 2.0 * qf["mean_blob_diameter_px"]


@pytest.mark.parametrize("diameter", [1.5, 2.5, 4.0, 6.0])
def test_blob_diameter_estimate_matches_the_gaussian_fwhm(diameter):
    """自己相関の半値幅から戻した直径がガウス粒子の FWHM に一致する。

    `piv_synth_particles` の ``diameter_px`` は 2σ なので、FWHM は
    ``2√(2ln2)·σ = 1.1774 · diameter_px``。実測の比(推定 / 真値)は
    1.02 / 1.00 / 1.00 / 0.99。許容差 5 % は最悪の 2 % に対して 2.5 倍の余裕。

    **実物のスペックルはガウスではないので、これは換算の算数が合っている
    ことの確認であって、実写での精度ではない。**
    """
    img, _ = PV.piv_synth_particles((N, N), density=0.02, diameter_px=diameter, seed=SEED)
    q = D.speckle_quality(img)
    assert q["mean_blob_diameter_px"] == pytest.approx(1.1774 * diameter, rel=0.05)
    assert 0.0 < q["coverage"] < 1.0
    assert q["mig"] > 0.0


def test_speckle_quality_refuses_a_uniform_image():
    """斑点が 1 つも無い画像は「品質」を返さない(0 を返すと比較で通ってしまう)。"""
    with pytest.raises(ValueError, match="uniform"):
        D.speckle_quality(np.full((64, 64), 0.3))
