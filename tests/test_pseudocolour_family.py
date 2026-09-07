# -*- coding: utf-8 -*-
"""疑似カラーの「種類」を測る門(2026-09-08、ユーザー「種類が少なくないか?」)。

数えると palette は 16 あったが、**足りないのは枚数ではなく軸**だった:

* 値を色に写す方法(``norm``)が **線形しか無かった** —— 実務ではパレットより
  こちらが効く(桁の広い強度、外れ値 1 個、0 を中央に置きたい発散量)。
* ``[vmin, vmax]`` の**外側が端の色に丸められ**、正当な最小値と見分けがつかない。
  実測: ``vmin`` 省略でも ``-5`` は viridis の下端になる。
* 巡回(位相)は ``hsv`` だけ、質的(ラベル)は乱数 RGB だけ、等輝度は無し。
* 2 つの量(値 × 信頼度)を 1 枚に載せる一般の道具が無く、
  ``colorize_flow`` に 1 例が焼き込まれているだけだった。

ここで守るのは「増やした」ことではなく、**それぞれが本当に別のことをしている**
ことと、**明度が嘘をつかない**こと。
"""
from __future__ import annotations

import numpy as np
import pytest

import imgio


def _lightness(rgb):
    """CIE L*(sRGB → 線形 → Y → L*)。明度の折返しを数えるために使う。"""
    c = np.clip(np.asarray(rgb, float), 0, 1)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    y = lin @ np.array([0.2126, 0.7152, 0.0722])
    return np.where(y > 0.008856, 116 * np.cbrt(y) - 16, 903.3 * y)


def _turns(name):
    ramp = np.linspace(0.0, 1.0, 256).reshape(1, 256)
    lut = np.asarray(imgio.apply_cmap(ramp, name), float)[0]
    d = np.diff(_lightness(lut))
    return int((np.diff(np.sign(d)) != 0).sum())


# --------------------------------------------------------------------------- #
# パレットの種類                                                                #
# --------------------------------------------------------------------------- #
def test_every_palette_in_the_catalogue_actually_renders():
    ramp = np.linspace(0.0, 1.0, 64).reshape(1, 64)
    for name in imgio.COLORMAPS:
        rgb = np.asarray(imgio.apply_cmap(ramp, name), float)
        assert rgb.shape == (1, 64, 3), (name, rgb.shape)
        assert np.isfinite(rgb).all(), name
        # 定数のパレットは「疑似カラー」ではない
        assert len(np.unique(np.round(rgb.reshape(-1, 3), 4), axis=0)) > 8, name


def _delta_e_profile(name, n=512):
    """隣接色差の列(CIE76 近似)。色差の刻みが不均一だと無い境目が見える。"""
    import fullseye as fs

    t = np.linspace(0.0, 1.0, n).reshape(1, -1)
    rgb = np.asarray(fs.apply_cmap(t, name), float)[0]
    lab = np.asarray(fs.rgb_to_lab(rgb.reshape(1, -1, 3)), float)[0]
    return np.sqrt((np.diff(lab, axis=0) ** 2).sum(1))


def _ridges(name):
    de = _delta_e_profile(name)
    med = float(np.median(de)) or 1e-12
    inner = de[1:-1]
    peak = (inner > de[:-2]) & (inner > de[2:]) & (inner > 1.6 * med)
    return int(peak.sum()), float(de.max() / med)


def test_the_perceptually_safe_list_is_measured_on_both_criteria():
    """``PERCEPTUAL_SAFE`` は**明度の単調さと色差の一様さの両方**で選ぶ。

    ★2026-09-08、``poc_colormap_readability`` の指摘で基準を足した。それまでは
    「L* の折返しが 0 回」だけで選んでおり、``cividis``(折返し 0 回、しかし
    ΔE max/median **2.23** で尾根 1 本)が入っていた。明度が単調でも色差の刻みが
    不均一なら、なめらかな場に**無い境目**が見える —— 片側の基準で「安全」と
    名乗っていた。この repo が繰り返し踏む「一方向だけ確かめて不変を主張する」形。
    """
    for name in imgio.PERCEPTUAL_SAFE:
        assert _turns(name) == 0, (
            "%s を PERCEPTUAL_SAFE に挙げているが、明度が %d 回行き来する"
            % (name, _turns(name)))
        ridges, ratio = _ridges(name)
        assert ridges == 0 and ratio < 1.6, (
            "%s は明度こそ単調だが色差の刻みが不均一(尾根 %d 本 / "
            "max/median %.2f)。なめらかな場に無い境目を作るので "
            "PERCEPTUAL_SAFE には置けない" % (name, ridges, ratio))


def test_cividis_is_kept_out_of_perceptual_safe_for_a_measured_reason():
    """外した理由を数字で固定する(直したら基準の側でなくこのテストが鳴る)。"""
    assert "cividis" not in imgio.PERCEPTUAL_SAFE
    assert "cividis" in imgio.CVD_SAFE
    ridges, ratio = _ridges("cividis")
    assert _turns("cividis") == 0                # 明度は単調 —— だから見落とした
    assert ridges >= 1 and ratio > 1.6, (ridges, ratio)


def test_the_rainbow_maps_are_worse_and_we_say_so_with_numbers():
    """jet / hsv が「無い境目を作る」ことを数字で固定する(既定を選ぶ根拠)。"""
    assert _turns("hsv") >= 4, _turns("hsv")
    assert _turns("jet") >= 3, _turns("jet")
    assert _turns("turbo") <= 1, _turns("turbo")      # 虹色のまま素直な代替
    assert _turns("viridis") == 0


def test_cyclic_maps_really_close_the_loop():
    """巡回マップは端と端がほぼ同じ色(位相 0 と 2π が別の色だと嘘になる)。"""
    ramp = np.linspace(0.0, 1.0, 256).reshape(1, 256)
    for name in ("twilight", "phase"):
        lut = np.asarray(imgio.apply_cmap(ramp, name), float)[0]
        gap = float(np.abs(lut[0] - lut[-1]).max())
        assert gap < 0.02, (name, gap)
    # hsv は巡回だが明度が動くので、CYCLIC に居ても既定にはしない
    assert set(imgio.CYCLIC) == {"twilight", "phase", "hsv"}


def test_qualitative_palettes_are_actually_distinct():
    """質的パレットは、隣り合う色が**十分離れている**こと。"""
    for name, pal in imgio.QUALITATIVE.items():
        p = np.asarray(pal, float)
        d = np.linalg.norm(p[:, None, :] - p[None, :, :], axis=-1)
        np.fill_diagonal(d, np.inf)
        assert float(d.min()) > 0.2, (name, float(d.min()))


# --------------------------------------------------------------------------- #
# 写し方(norm)—— パレットと直交する軸                                          #
# --------------------------------------------------------------------------- #
def test_every_norm_is_a_different_mapping():
    """8 つの ``norm`` が本当に別々の写し方であること(名前だけ増やさない)。

    ★探針を 2 枚にしている。1 枚目の指数ランプだけだと **log と rank が厳密に
    一致する** —— 対数を取ると等間隔になる並びでは、分位も等間隔だから。
    これは op の欠陥ではなく**探針の縮退**で、最初に書いたときこの門が
    「同じ写し方になっている」と鳴った(2026-09-08)。2 枚のどちらかで違えばよい、
    という判定にする。
    """
    probes = {
        "指数ランプ": np.exp(np.linspace(0.0, 6.0, 1024)).reshape(32, 32),
        "対数正規の標本": np.exp(np.random.default_rng(20260908)
                                 .normal(0.0, 1.4, 1024)).reshape(32, 32),
    }
    seen = {}
    for tag, x in probes.items():
        for n in imgio.NORMS:
            rgb = np.asarray(imgio.apply_cmap(x, "viridis", norm=n), float)
            seen[(tag, n)] = rgb
            assert np.isfinite(rgb).all(), (tag, n)
    for a in imgio.NORMS:
        for b in imgio.NORMS:
            if a >= b:
                continue
            same = [tag for tag in probes
                    if np.allclose(seen[(tag, a)], seen[(tag, b)])]
            assert len(same) < len(probes), (
                a, b, "どの探針でも同じ写し方になっている")


def test_log_norm_does_not_silently_lift_non_positive_values():
    x = np.array([[-1.0, 0.0, 1.0, 100.0]])
    rgb = np.asarray(imgio.apply_cmap(x, "viridis", norm="log"), float)
    assert np.isfinite(rgb).all()
    # 負と 0 は下端に寄る(持ち上げて「小さい正の値」に化けさせない)
    assert np.allclose(rgb[0, 0], rgb[0, 1])
    assert not np.allclose(rgb[0, 1], rgb[0, 3])


def test_symmetric_norm_puts_zero_in_the_middle():
    x = np.array([[-4.0, 0.0, 1.0]])
    rgb = np.asarray(imgio.apply_cmap(x, "coolwarm", norm="symmetric"), float)
    mid = np.asarray(imgio.apply_cmap(np.array([[0.0]]), "coolwarm",
                                      vmin=-1.0, vmax=1.0), float)[0, 0]
    assert np.allclose(rgb[0, 1], mid, atol=1e-9), (rgb[0, 1], mid)


def test_rank_norm_survives_one_outlier_where_linear_does_not():
    """外れ値 1 個で中身が潰れるのを防ぐ、が ``rank`` の仕事。"""
    x = np.linspace(0.0, 1.0, 400).reshape(20, 20).copy()
    x[0, 0] = 1e6
    lin = np.asarray(imgio.apply_cmap(x, "viridis", norm="linear"), float)
    rnk = np.asarray(imgio.apply_cmap(x, "viridis", norm="rank"), float)
    n_lin = len(np.unique(np.round(lin.reshape(-1, 3), 3), axis=0))
    n_rnk = len(np.unique(np.round(rnk.reshape(-1, 3), 3), axis=0))
    assert n_lin < 10, n_lin                     # 線形では 1 個の外れ値で潰れる
    assert n_rnk > 100, n_rnk


def test_levels_quantises_into_exactly_that_many_bands():
    x = np.linspace(0.0, 1.0, 4096).reshape(64, 64)
    for n in (2, 5, 12):
        rgb = np.asarray(imgio.apply_cmap(x, "viridis", levels=n), float)
        assert len(np.unique(np.round(rgb.reshape(-1, 3), 6), axis=0)) == n, n
    with pytest.raises(ValueError, match="levels must be >= 2"):
        imgio.apply_cmap(x, "viridis", levels=1)


def test_out_of_range_is_distinguishable_only_when_asked():
    """既定は今までどおり丸める。``under`` / ``over`` を渡したときだけ別の色。"""
    x = np.array([[-5.0, 0.0, 0.5, 1.0, 9.0]])
    clamped = np.asarray(imgio.apply_cmap(x, "viridis", vmin=0.0, vmax=1.0), float)
    assert np.allclose(clamped[0, 0], clamped[0, 1])          # 範囲外 == 下端(従来)
    marked = np.asarray(imgio.apply_cmap(x, "viridis", vmin=0.0, vmax=1.0,
                                         under=(1, 0, 1), over=(0, 1, 1)), float)
    assert np.allclose(marked[0, 0], (1, 0, 1))
    assert np.allclose(marked[0, 4], (0, 1, 1))
    assert np.allclose(marked[0, 1], clamped[0, 1])           # 端そのものは動かない


def test_unknown_norm_is_refused():
    with pytest.raises(ValueError, match="unknown norm"):
        imgio.apply_cmap(np.zeros((4, 4)), "viridis", norm="magic")


# --------------------------------------------------------------------------- #
# 2 つの量を 1 枚に                                                             #
# --------------------------------------------------------------------------- #
def test_bivariate_dims_where_the_weight_is_low():
    v = np.tile(np.linspace(-1.0, 1.0, 16), (16, 1))
    w = np.tile(np.linspace(0.0, 1.0, 16).reshape(16, 1), (1, 16))
    rgb = np.asarray(imgio.colorize_bivariate(v, w, floor=0.15), float)
    top = float(rgb[-1].mean())          # 重みが大きい行
    bot = float(rgb[0].mean())           # 重みが 0 の行
    assert bot < top * 0.4, (bot, top)
    assert bot > 0.0                     # 真っ黒にはしない(形が読めなくなる)
    with pytest.raises(ValueError, match="same shape"):
        imgio.colorize_bivariate(v, w[:4])


def test_significance_greys_out_what_cannot_be_claimed():
    v = np.linspace(-3.0, 3.0, 64).reshape(8, 8)
    sig = np.abs(v) > 2.0
    rgb = np.asarray(imgio.colorize_significance(v, sig, dim=0.25), float)
    plain = np.asarray(imgio.apply_cmap(v, "coolwarm", norm="symmetric"), float)
    assert np.allclose(rgb[sig], plain[sig])                    # 有意はそのまま
    # 有意でないところは彩度が落ちている(R,G,B の広がりが小さい)
    spread_in = float(np.ptp(plain[~sig], axis=-1).mean())
    spread_out = float(np.ptp(rgb[~sig], axis=-1).mean())
    assert spread_out < spread_in * 0.4, (spread_out, spread_in)
    with pytest.raises(ValueError, match="same shape"):
        imgio.colorize_significance(v, sig[:2])


def test_categorical_does_not_imply_an_order():
    lab = np.array([[0, 1, 2], [3, 4, 5]])
    rgb = np.asarray(imgio.colorize_categorical(lab, "wong"), float)
    assert np.allclose(rgb[0, 0], (0, 0, 0))                    # 背景
    cols = np.unique(np.round(rgb.reshape(-1, 3), 6), axis=0)
    assert len(cols) == 6                                       # 背景 + 5 ラベル
    with pytest.raises(ValueError, match="unknown qualitative palette"):
        imgio.colorize_categorical(lab, "rainbow")


# --------------------------------------------------------------------------- #
# 族の中の契約が片側だけになっていないか(KNOWN_ISSUES §42 と同じ型)             #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fn", ["colorize_depth", "colorize_disparity"])
def test_the_thin_wrappers_pass_the_whole_contract_through(fn):
    f = getattr(imgio, fn)
    x = np.array([[-5.0, 0.0, 0.5, 1.0, 9.0]])
    marked = np.asarray(f(x, vmin=0.0, vmax=1.0, under=(1, 0, 1)), float)
    assert np.allclose(marked[0, 0], (1, 0, 1)), (
        "%s が under を下の層へ渡していない(包みが契約を落としている)" % fn)
    banded = np.asarray(f(np.linspace(0, 1, 256).reshape(1, 256), levels=4), float)
    assert len(np.unique(np.round(banded.reshape(-1, 3), 6), axis=0)) == 4


def test_disparity_default_is_no_longer_the_worst_map():
    import inspect
    assert inspect.signature(imgio.colorize_disparity).parameters["name"].default == "turbo"
    assert _turns("turbo") < _turns("jet")


def test_categorical_refuses_to_reuse_a_colour_without_being_told_to():
    """★色数を超えたら拒否する(2026-09-08、黙って循環していた)。

    24 領域を ``tab10`` で塗ると隣り合う領域が同じ色になり(実測: 隣接色差の
    最小 0.0 が 3 組)、循環したことが戻り値からは分からなかった。
    """
    lab = np.arange(25).reshape(5, 5)
    with pytest.raises(ValueError, match="exceeds the 10 colours"):
        imgio.colorize_categorical(lab, "tab10")
    assert imgio.colorize_categorical(lab, "tab10", cycle=True).shape == (5, 5, 3)
    ok = np.arange(11).reshape(11, 1)            # ラベル 1..10 はちょうど収まる
    assert imgio.colorize_categorical(ok, "tab10").shape == (11, 1, 3)
