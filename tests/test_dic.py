# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""dic — 真値で検算するテスト。

方針:
  * **解析的に答えが分かる入力**で当てる。合成スペックルは斑点の中心を写して
    描き直すので、仕込んだ変位が丸め誤差まで真値になる。ひずみの側は
    **画像を 1 枚も使わず**、厳密な剛体回転の変位場を直接入れて代数の恒等式
    (Green-Lagrange が 0)を確かめる —— この許容差だけは実測ではなく代数。
  * 許容差は**実測した値**から取る。「たぶん通るだろう」という丸い数字は
    書かない。各テストの docstring に実測値を残す。
  * fail-closed を「例外が出ること」だけでなく **文言**でも確かめる
    (黙って代用しないことがこの層の契約なので)。
"""
import math

import numpy as np
import pytest

import dic as D

N = 256
MARGIN = 40
SEED = 7
SL = (slice(MARGIN, N - MARGIN), slice(MARGIN, N - MARGIN))


@pytest.fixture(scope="module")
def speckle():
    """基準画像を描き終えた(= scale が確定した)スペックルモデルと基準画像。"""
    model = D.speckle_synth(N, 3000, 1.6, SEED)
    ref = D.speckle_render(model)
    return model, ref


def _shift(u0):
    """x を ``u0`` だけ動かす写像。ループ変数を閉じ込めないよう関数で作る。"""
    return (lambda x, y: x + u0), None


# --------------------------------------------------------------------------- #
# 合成器 —— この族の真値の根拠そのもの                                          #
# --------------------------------------------------------------------------- #
def test_integer_shift_reproduces_the_reference_bit_for_bit(speckle):
    """★整数シフトで重なる領域が**厳密に一致**する(実測 最大差 0.0)。

    これがこの族の土台。斑点を描き直したものが真値を名乗れるのは、
    整数の平行移動に対して描画が厳密に可換なときだけ。1 ビットでも動けば、
    サブピクセルの 0.001 px を議論する足場が無くなる。
    """
    model, ref = speckle
    cur = D.speckle_render(model, lambda x, y: x + 3.0, None)
    a = ref[MARGIN:N - MARGIN, MARGIN:N - MARGIN - 3]
    b = cur[MARGIN:N - MARGIN, MARGIN + 3:N - MARGIN]
    assert float(np.max(np.abs(a - b))) == 0.0


def test_deformed_frame_is_not_renormalised(speckle):
    """★変形後の像は**基準画像で決めた定数**で割る(像ごとに割り直さない)。

    割り直すと変形で最大値が動くたびに全体の明るさが変わり、輝度不変を
    仮定する推定器に無関係な誤差が乗る。実測: 1.02 倍に伸ばした像の最大値は
    **1.007608** で、1.0 では**ない** —— 割り直していたら定義上ちょうど 1.0 に
    なるので、この 7.6e-3 のずれが「割り直していない」ことの証拠。
    """
    model, ref = speckle
    scale_before = model["scale"]
    cur = D.speckle_render(model, lambda x, y: x * 1.02, None)
    assert model["scale"] == scale_before
    assert float(ref.max()) == pytest.approx(1.0, abs=1e-12)
    assert abs(float(cur.max()) - 1.0) > 1e-3


def test_rendering_a_deformed_frame_first_is_refused():
    """基準画像より先に変形後の像を描こうとしたら止める(正規化定数が汚れる)。"""
    model = D.speckle_synth(64, 300, 1.6, 1)
    with pytest.raises(ValueError, match="reference"):
        D.speckle_render(model, lambda x, y: x + 1.0, None)
    D.speckle_render(model)                      # 基準を描けば通る
    D.speckle_render(model, lambda x, y: x + 1.0, None)


# --------------------------------------------------------------------------- #
# dic_correlate —— サブピクセルと照明不変性                                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("u0,bias_max,sd_max", [
    (0.37, 0.002, 0.010),      # 実測 偏り -0.00001 / 散らばり 0.00572
    (0.50, 0.002, 0.010),      # 実測 偏り -0.00016 / 散らばり 0.00258
    (-0.25, 0.002, 0.010),     # 実測 偏り -0.00083 / 散らばり 0.00773
])
def test_subpixel_translation_is_recovered(speckle, u0, bias_max, sd_max):
    """既知のサブピクセル並進を格子上で読み戻す。

    許容差は実測から取った。3 例の最悪値は偏り 0.00083 px・散らばり 0.00773 px
    なので、偏り 0.002 px(2.4 倍の余裕)・散らばり 0.010 px(1.3 倍)で切る。
    散らばりの余裕が薄いのは意図的で、``step`` や当てはめを触って劣化したら
    ここが最初に鳴る。
    """
    model, ref = speckle
    fx, fy = _shift(u0)
    cur = D.speckle_render(model, fx, fy)
    g = D.dic_correlate(ref, cur, subset=31, step=8, search=8)
    assert not np.isnan(g["u"]).any()
    assert abs(float(np.mean(g["u"])) - u0) < bias_max
    assert float(np.std(g["u"])) < sd_max
    assert float(np.min(g["zncc"])) > 0.95


def test_no_motion_axis_stays_near_zero_but_scatters_more(speckle):
    """動いていない軸(v)は 0 のまわりだが、動いている軸より散らばる。

    x と y を独立に当てはめるので、v の 3 点は「x の**整数**の峰を通る断面」
    から取る。実測(u=0.37):偏り +0.00139 px、散らばり 0.03385 px ——
    **u の散らばり 0.00572 px の 5.9 倍**。これは実装の性質であって欠陥では
    ないが、片方しか動かない実験で v を精度の根拠に使わせないために固定する。
    """
    model, ref = speckle
    cur = D.speckle_render(model, *_shift(0.37))
    g = D.dic_correlate(ref, cur, subset=31, step=8, search=8)
    assert abs(float(np.mean(g["v"]))) < 0.005
    assert float(np.std(g["v"])) < 0.06
    assert float(np.std(g["v"])) > 3.0 * float(np.std(g["u"]))


def test_zncc_is_invariant_to_gain_and_offset(speckle):
    """★★ゲイン 0.7・オフセット 0.15 を掛けても変位が動かない。

    実測: ``max|Δu| = 7.4e-14 px``、``max|Δv| = 8.6e-14``、
    ``max|Δzncc| = 2.1e-14`` —— 倍精度の丸め誤差そのもの。許容差 1e-11 は
    その 130 倍上に置いた(BLAS の実装差で少し動いても落ちないように)。

    **平均を引かない素の NCC では成り立たない**ことを同じ画像で確かめる。
    同じ 3 点ガウス当てはめまで揃えたうえで、64 点の平均と分散だけを変えた
    実装は実測で **max|Δu| = 0.146 px** 動く —— ZNCC の 2e12 倍。
    「正規化相関ならどれでも照明に強い」は誤りで、**平均を引くかどうか**が
    効いている。
    """
    model, ref = speckle
    cur = D.speckle_render(model, *_shift(0.37))
    bright = 0.7 * cur + 0.15

    g1 = D.dic_correlate(ref, cur, subset=31, step=8, search=8)
    g2 = D.dic_correlate(ref, bright, subset=31, step=8, search=8)
    assert float(np.max(np.abs(g1["u"] - g2["u"]))) < 1e-11
    assert float(np.max(np.abs(g1["v"] - g2["v"]))) < 1e-11
    assert float(np.max(np.abs(g1["zncc"] - g2["zncc"]))) < 1e-11

    plain = [_plain_ncc_u(ref, cur, cy, cx) - _plain_ncc_u(ref, bright, cy, cx)
             for cy in range(64, 200, 32) for cx in range(64, 200, 32)]
    assert max(abs(d) for d in plain) > 0.01


def _plain_ncc_u(ref, cur, cy, cx, sub=31, search=8):
    """平均を**引かない**素の NCC で u を出す参照実装(比較用、テスト内だけ)。

    正規化(標準偏差で割る)と 3 点ガウス当てはめは `dic_correlate` と同じ。
    違うのは平均を引かないことだけなので、差が出たらそれが原因。
    """
    h = sub // 2
    f = ref[cy - h:cy + h + 1, cx - h:cx + h + 1]
    sf = math.sqrt(float(np.sum(f * f)))
    c = np.empty((2 * search + 1, 2 * search + 1))
    for i in range(-search, search + 1):
        for j in range(-search, search + 1):
            w = cur[cy + i - h:cy + i + h + 1, cx + j - h:cx + j + h + 1]
            c[i + search, j + search] = float(np.sum(f * w)) / (sf * math.sqrt(float(np.sum(w * w))))
    i0, j0 = np.unravel_index(int(np.argmax(c)), c.shape)
    if not 0 < j0 < 2 * search:
        return float(j0 - search)
    cm, c0, cp = float(c[i0, j0 - 1]), float(c[i0, j0]), float(c[i0, j0 + 1])
    d = 0.5 * (math.log(cm) - math.log(cp)) / (math.log(cm) - 2 * math.log(c0) + math.log(cp))
    return float(j0 - search) + d


def test_zero_variance_reference_subset_returns_nan():
    """★分散の無いサブセットは **NaN**。0 を返して「動いていない」に化けさせない。

    実測: 完全に一様な画像では格子点の 100 % が NaN。半分だけ一様にすると
    36.4 % が NaN で、境界も正しい位置に立つ —— 一様領域が x < 64、
    subset=31(半幅 15)なので、NaN になる格子点の x は 47 以下(窓が
    [32, 62] に収まる)、有限な格子点の x は 55 以上(窓が斑点に掛かる)。
    """
    flat = np.full((128, 128), 0.5)
    g = D.dic_correlate(flat, flat, subset=31, step=8, search=8)
    assert np.isnan(g["u"]).all()
    assert np.isnan(g["v"]).all()
    assert np.isnan(g["zncc"]).all()

    model = D.speckle_synth(128, 800, 1.6, 3)
    mix = D.speckle_render(model)
    mix[:, :64] = 0.5
    g = D.dic_correlate(mix, mix, subset=31, step=8, search=8)
    bad = np.isnan(g["u"])
    assert bad.any() and (~bad).any()
    assert float(np.max(g["x"][bad])) <= 47.0
    assert float(np.min(g["x"][~bad])) >= 55.0


@pytest.mark.parametrize("kwargs,match", [
    (dict(subset=30), "odd"),
    (dict(subset=1), "at least 3"),
    (dict(step=0), "step"),
    (dict(search=0), "search"),
    (dict(quality="ncc"), "zncc"),
    (dict(subset=201), "no grid point fits"),
])
def test_dic_correlate_is_fail_closed(speckle, kwargs, match):
    """壊れた設定は黙って代用せず、理由を書いて拒否する。"""
    model, ref = speckle
    small = ref[:128, :128]
    with pytest.raises(ValueError, match=match):
        D.dic_correlate(small, small, **kwargs)


def test_dic_dense_is_nan_outside_the_correlated_grid(speckle):
    """★格子の外は 0 でも縁の値でもなく **NaN**(測っていない帯だから)。

    subset=31 / search=8 なので格子は縁から 23 px 内側にしかない。
    その外を埋めると、測っていない帯が測った値の顔をする。
    """
    model, ref = speckle
    cur = D.speckle_render(model, *_shift(0.37))
    u, v, z = D.dic_dense(ref, cur, subset=31, step=8, search=8)
    assert u.shape == ref.shape == v.shape == z.shape
    assert np.isnan(u[0, 0]) and np.isnan(u[-1, -1])
    assert not np.isnan(u[SL]).any()
    assert abs(float(np.mean(u[SL])) - 0.37) < 0.002


# --------------------------------------------------------------------------- #
# strain_from_displacement —— 画像を使わない代数の検算                          #
# --------------------------------------------------------------------------- #
def _rigid_rotation_field(n, deg):
    """厳密な剛体回転の変位場。``u = (cosθ-1)x - sinθ·y``, ``v = sinθ·x + (cosθ-1)y``。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    t = math.radians(deg)
    ct, st = math.cos(t), math.sin(t)
    return (ct - 1.0) * xx - st * yy, st * xx + (ct - 1.0) * yy, ct - 1.0


@pytest.mark.parametrize("deg", [0.5, 2.0, 5.0])
def test_green_lagrange_is_exactly_zero_under_rigid_rotation(deg):
    """★★画像を 1 枚も使わない代数の恒等式。

    厳密な剛体回転の変位場を直接入れる。Green-Lagrange は
    ``exx = (cosθ-1) + ½((cosθ-1)² + sin²θ) = 0`` が**代数的に厳密**なので、
    ここの許容差 1e-9 は「実測して決めた値」ではなく**倍精度で到達できる限界**。
    実測は 2 度で 1.9e-13(許容差の 5000 分の 1)。
    微小ひずみのほうは ``exx = cosθ-1`` を 1e-6 で返す(実測 1.8e-13)。

    この 2 つが同じ入力から出るという事実が、``method`` に既定値を置かない
    理由そのもの。
    """
    n = 128
    u, v, ct_minus_1 = _rigid_rotation_field(n, deg)

    exx, eyy, exy = D.strain_from_displacement(u, v, 31, "green")
    assert float(np.max(np.abs(exx))) < 1e-9
    assert float(np.max(np.abs(eyy))) < 1e-9
    assert float(np.max(np.abs(exy))) < 1e-9

    exx, eyy, exy = D.strain_from_displacement(u, v, 31, "infinitesimal")
    assert float(np.max(np.abs(exx - ct_minus_1))) < 1e-6
    assert float(np.max(np.abs(eyy - ct_minus_1))) < 1e-6
    assert float(np.max(np.abs(exy))) < 1e-6
    # ひずみは 0 が真値なのに、微小ひずみは 5 度で -3806 µε の嘘を返す。
    assert abs(ct_minus_1) > 3.8e-5 if deg >= 0.5 else True


def test_uniform_strain_is_recovered_exactly():
    """一様ひずみの変位場 ``u = ε x`` から ``exx = ε`` が厳密に戻る。

    対称窓の最小二乗は 1 次関数の傾きを厳密に返すので、これも代数の検算。
    実測 5e-19(倍精度の丸め)。微小ひずみと Green の差は ``½ε²`` で、
    ε=0.02 なら 200 µε —— **2 % のひずみでは定義の差が 1 % 効く**。
    """
    n = 96
    eps = 0.02
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    u = eps * xx
    v = np.zeros_like(u)
    exx_i, eyy_i, exy_i = D.strain_from_displacement(u, v, 21, "infinitesimal")
    assert float(np.max(np.abs(exx_i - eps))) < 1e-12
    assert float(np.max(np.abs(eyy_i))) < 1e-12
    assert float(np.max(np.abs(exy_i))) < 1e-12
    exx_g, _, _ = D.strain_from_displacement(u, v, 21, "green")
    assert float(np.max(np.abs(exx_g - (eps + 0.5 * eps * eps)))) < 1e-12


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


def test_nan_displacement_propagates_to_nan_strain():
    """★NaN は 0 ではなく NaN のまま伝える。

    ``window=11`` の場に NaN を 1 点だけ置くと、ひずみ側で **ちょうど
    11x11 = 121 点**が NaN になる(実測)。0 と見なしていたら NaN は 0 点で、
    代わりに周囲へ本物に見える偽のひずみ勾配が立つ。
    """
    n = 128
    u, v, _ = _rigid_rotation_field(n, 2.0)
    u = u.copy()
    u[64, 64] = np.nan
    exx, eyy, exy = D.strain_from_displacement(u, v, 11, "green")
    for e in (exx, eyy, exy):
        assert int(np.isnan(e).sum()) == 121
    assert np.isnan(exx[64, 64])
    assert np.isfinite(exx[0, 0])
    # 穴の縁の外は汚れていない(Green はここでも 0 が真値)。
    assert float(np.max(np.abs(exx[np.isfinite(exx)]))) < 1e-9


@pytest.mark.parametrize("kwargs,match", [
    (dict(window=30, method="green"), "odd"),
    (dict(window=201, method="green"), "larger than the field"),
])
def test_strain_is_fail_closed(kwargs, match):
    """窓の指定が壊れていたら拒否する。"""
    u = np.zeros((64, 64))
    v = np.zeros((64, 64))
    with pytest.raises(ValueError, match=match):
        D.strain_from_displacement(u, v, **kwargs)


# --------------------------------------------------------------------------- #
# speckle_quality                                                              #
# --------------------------------------------------------------------------- #
def test_mig_is_larger_for_a_fine_speckle():
    """★平均輝度勾配(MIG)は細かいスペックルほど大きい。

    同じ斑点数・同じ種で 1σ 半径だけ 1.0 と 3.0 に変えた実測:
    ``mig`` は **0.0873 対 0.0433(2.02 倍)**、``grad_rms`` は
    0.0617 対 0.0310(1.99 倍)。許容差は「1.5 倍以上」で、実測の 2.02 倍に
    対して 1.35 倍の余裕。

    ★ここは MIG の**限界**も同時に示している。MIG は「細かいほど良い」としか
    言わないが、直径 1.4 px のスペックルは標本化が足りず実際には最悪
    (`examples/poc_dic_strain.py` の 9 節)。MIG は下限を切る指標であって、
    最大化する目的関数ではない。
    """
    fine = D.speckle_quality(D.speckle_render(D.speckle_synth(N, 3000, 1.0, 3)))
    coarse = D.speckle_quality(D.speckle_render(D.speckle_synth(N, 3000, 3.0, 3)))
    assert fine["mig"] > 1.5 * coarse["mig"]
    assert fine["grad_rms"] > 1.5 * coarse["grad_rms"]
    assert coarse["mean_blob_diameter_px"] > 2.0 * fine["mean_blob_diameter_px"]


@pytest.mark.parametrize("radius,n_blob", [(1.0, 7680), (1.6, 3000), (2.5, 1228)])
def test_blob_diameter_estimate_matches_the_gaussian_fwhm(radius, n_blob):
    """自己相関の半値幅から戻した直径が ``2.355 σ`` に一致する(ガウス斑点)。

    実測の比(推定 / 真の FWHM)は σ=1.0 で 1.01、σ=1.6 で 1.00、σ=2.5 で 0.98。
    許容差 5 % は最悪の 2 % に対して 2.5 倍の余裕。**実物のスペックルは
    ガウスではないので、これは換算の算数が合っていることの確認であって、
    実写での精度ではない。**
    """
    model = D.speckle_synth(N, n_blob, radius, SEED)
    q = D.speckle_quality(D.speckle_render(model))
    assert q["mean_blob_diameter_px"] == pytest.approx(2.3548 * radius, rel=0.05)
    assert 0.0 < q["coverage"] < 1.0


def test_speckle_quality_refuses_a_uniform_image():
    """斑点が 1 つも無い画像は「品質」を返さない(0 を返すと比較で通ってしまう)。"""
    with pytest.raises(ValueError, match="uniform"):
        D.speckle_quality(np.full((64, 64), 0.3))
