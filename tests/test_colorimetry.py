# -*- coding: utf-8 -*-
"""測色(sRGB -> XYZ -> L*a*b*)の回帰テスト。

背景 = docs/ops/2d/guides/colorimetry.md。

2026-09-05 に見つかった不整合の回帰テストでもある。``color_pca.trans_from_rgb``
は ``hsv`` / ``yuv`` / ``gray`` しか受け付けず、``"lab"`` / ``"xyz"`` を渡すと
``ValueError`` を投げていた —— **CIE の定義どおりの実装は :mod:`imgmetrics` に
既にあったのに、色空間変換の入口からそこへ到達する道が無かった**。

直し方は「もう一組実装を書く」ではなく **委譲**。行列と伝達関数を二組持つと、
片方だけ直したときに例外を出さずに違う色が出る(``imgmetrics`` 自身も同じ理由で
sRGB の伝達関数を ``gfx2d`` に委譲している)。そこでここでは
**色の値そのもの**と**委譲が保たれていること**の両方を固定する。

値はすべて閉形式か広く公表された既知値で、実装を写したものではない。
"""
import numpy as np
import pytest

import color_pca as C
import imgmetrics as M


def _px(r, g, b):
    return np.array([[[float(r), float(g), float(b)]]])


def test_srgb_transfer_function_matches_the_iec_61966_2_1_breakpoint():
    """伝達関数は 0.04045 で線形部と冪部が連続していること。"""
    lo = C.srgb_to_linear(np.array([[[0.04045, 0.0, 0.0]]]))[0, 0, 0]
    assert lo == pytest.approx(0.04045 / 12.92, rel=1e-12)
    # 冪部側から同じ点に寄せても一致する(定義が連続)
    hi = ((0.04045 + 0.055) / 1.055) ** 2.4
    assert lo == pytest.approx(hi, abs=2e-6)
    # 白と黒は不動点
    assert C.srgb_to_linear(_px(1, 1, 1))[0, 0, 0] == pytest.approx(1.0, rel=1e-12)
    assert C.srgb_to_linear(_px(0, 0, 0))[0, 0, 0] == 0.0


def test_white_lands_on_the_d65_white_point():
    """sRGB の白は D65 白色点そのもの。L*a*b* = (100, 0, 0) に落ちること。

    厳密なゼロにはならない —— 公表されている sRGB 行列は 7 桁に丸められており、
    Y の行の和が 1.0000001 になる。**丸め由来のずれであって実装の誤りではない**
    ので、そのぶん(2e-5 級)だけ許す。
    """
    xyz = C.trans_from_rgb(_px(1, 1, 1), "xyz")[0, 0]
    assert xyz == pytest.approx([0.95047, 1.0, 1.08883], abs=5e-6)
    lab = C.trans_from_rgb(_px(1, 1, 1), "lab")[0, 0]
    assert lab == pytest.approx([100.0, 0.0, 0.0], abs=5e-5)


def test_black_is_the_origin_of_lab():
    assert C.trans_from_rgb(_px(0, 0, 0), "lab")[0, 0] == pytest.approx([0.0, 0.0, 0.0])


def test_mid_gray_is_not_l_50():
    """sRGB の 0.5 は L* = 50 ではなく **53.39**。

    「中間グレー = 明度の中間」という直感が外れる典型で、ガンマを外さずに平均すると
    暗く濁る理由でもある(guides/colorimetry.md §4)。
    """
    lab = C.trans_from_rgb(_px(0.5, 0.5, 0.5), "lab")[0, 0]
    assert lab[0] == pytest.approx(53.389, abs=1e-3)
    assert lab[1:] == pytest.approx([0.0, 0.0], abs=5e-5)   # 無彩色は a*=b*=0


def test_primaries_match_the_published_srgb_lab_values():
    """sRGB 原色の L*a*b* は広く公表された既知値と一致すること。"""
    assert C.trans_from_rgb(_px(1, 0, 0), "lab")[0, 0] == pytest.approx(
        [53.241, 80.092, 67.203], abs=2e-3)
    assert C.trans_from_rgb(_px(0, 1, 0), "lab")[0, 0] == pytest.approx(
        [87.735, -86.183, 83.179], abs=2e-3)
    assert C.trans_from_rgb(_px(0, 0, 1), "lab")[0, 0] == pytest.approx(
        [32.297, 79.188, -107.860], abs=2e-3)


def test_luminance_row_is_the_photopic_weighting():
    """Y の行は測光の重み。緑の Y が最大で、3 原色の Y の和が 1 になること。

    公表されている sRGB 行列は 7 桁に丸められているので、Y 行の和は厳密な 1 ではなく
    1.0000001 になる。**丸め由来のずれであって実装の誤りではない**ので、そこまで許す。
    """
    ys = [C.trans_from_rgb(_px(*c), "xyz")[0, 0, 1] for c in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    assert ys[1] > ys[0] > ys[2]
    assert sum(ys) == pytest.approx(1.0, abs=2e-7)


def test_library_api_now_covers_the_same_spaces_as_the_ledger_op():
    """二層 API の対応範囲が揃っていること(この食い違いが元の不具合)。"""
    img = np.random.default_rng(0).random((4, 5, 3))
    for space in ("hsv", "yuv", "gray", "xyz", "lab"):
        out = C.trans_from_rgb(img, space)
        assert np.isfinite(out).all()
        assert out.shape == ((4, 5) if space == "gray" else (4, 5, 3))
    with pytest.raises(ValueError):
        C.trans_from_rgb(img, "no_such_space")


def test_colour_maths_lives_in_exactly_one_place():
    """``color_pca`` は :mod:`imgmetrics` へ**委譲**しており、値が 1 bit も違わないこと。

    ここが等しくなくなったら、行列か白色点か伝達関数がどこかで二重化している。
    そのときに壊れる形は「例外」ではなく「静かに違う色」なので、テストで押さえる。
    """
    img = np.random.default_rng(7).random((6, 5, 3))
    assert np.array_equal(C.trans_from_rgb(img, "xyz"), M.rgb_to_xyz(img))
    assert np.array_equal(C.trans_from_rgb(img, "lab"), M.rgb_to_lab(img))
    assert np.array_equal(C.srgb_to_linear(img), M.srgb_to_linear(img))
    # 重複した実装が復活していないこと(モジュール属性として持たない)
    for gone in ("_SRGB_TO_XYZ_D65", "_WHITE_D65", "_xyz_to_lab", "_rgb_to_xyz"):
        assert not hasattr(C, gone), f"color_pca が測色の実装を再び抱えている: {gone}"
