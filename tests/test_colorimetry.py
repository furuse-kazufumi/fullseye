# -*- coding: utf-8 -*-
"""測色(sRGB -> XYZ -> L*a*b*)の回帰テスト。

背景 = docs/ops/2d/guides/colorimetry.md。

2026-09-05: この repo には RGB→L*a*b* が 2 か所ある。**尺度が違うので混ぜられない**:

* :mod:`imgmetrics` —— **CIE の定義どおり**(sRGB 原色・白色点を選べる・L\* は 0-100)。
  **これが正**で、ここで固定するのはこちら。
* op 台帳経由の ``trans_from_rgb``(``backends_color``、OpenCV 実装)—— **uint8 に
  量子化**してから変換し 255 で割った 8-bit スケール。同じ名前でも別物。

かつて 3 か所目(``color_pca``)があったが、**どこからも import されず wheel にも
入らない死んだモジュール**だったので 0.1.7 で削除した(機能は ``xsk_inpaint`` /
``xsp_wiener`` / ``ncc_locate`` 等がレジストリ側で既に覆っていた)。

値はすべて閉形式か広く公表された既知値で、実装を写したものではない。
"""
import numpy as np
import pytest

import imgmetrics as M


def _px(r, g, b):
    return np.array([[[float(r), float(g), float(b)]]])


def M_trans(img, space):
    """``imgmetrics`` の色空間変換を 1 つの入口にまとめる(テスト用の薄い糖衣)。"""
    if space == "xyz":
        return M.rgb_to_xyz(img)
    if space == "lab":
        return M.rgb_to_lab(img)
    raise ValueError("unknown colour space: " + space)


def test_srgb_transfer_function_matches_the_iec_61966_2_1_breakpoint():
    """伝達関数は 0.04045 で線形部と冪部が連続していること。"""
    lo = M.srgb_to_linear(np.array([[[0.04045, 0.0, 0.0]]]))[0, 0, 0]
    assert lo == pytest.approx(0.04045 / 12.92, rel=1e-12)
    # 冪部側から同じ点に寄せても一致する(定義が連続)
    hi = ((0.04045 + 0.055) / 1.055) ** 2.4
    assert lo == pytest.approx(hi, abs=2e-6)
    # 白と黒は不動点
    assert M.srgb_to_linear(_px(1, 1, 1))[0, 0, 0] == pytest.approx(1.0, rel=1e-12)
    assert M.srgb_to_linear(_px(0, 0, 0))[0, 0, 0] == 0.0


def test_white_lands_on_the_d65_white_point():
    """sRGB の白は D65 白色点そのもの。L*a*b* = (100, 0, 0) に落ちること。

    厳密なゼロにはならない —— 公表されている sRGB 行列は 7 桁に丸められており、
    Y の行の和が 1.0000001 になる。**丸め由来のずれであって実装の誤りではない**
    ので、そのぶん(2e-5 級)だけ許す。
    """
    xyz = M_trans(_px(1, 1, 1), "xyz")[0, 0]
    assert xyz == pytest.approx([0.95047, 1.0, 1.08883], abs=5e-6)
    lab = M_trans(_px(1, 1, 1), "lab")[0, 0]
    assert lab == pytest.approx([100.0, 0.0, 0.0], abs=5e-5)


def test_black_is_the_origin_of_lab():
    assert M_trans(_px(0, 0, 0), "lab")[0, 0] == pytest.approx([0.0, 0.0, 0.0])


def test_mid_gray_is_not_l_50():
    """sRGB の 0.5 は L* = 50 ではなく **53.39**。

    「中間グレー = 明度の中間」という直感が外れる典型で、ガンマを外さずに平均すると
    暗く濁る理由でもある(guides/colorimetry.md §4)。
    """
    lab = M_trans(_px(0.5, 0.5, 0.5), "lab")[0, 0]
    assert lab[0] == pytest.approx(53.389, abs=1e-3)
    assert lab[1:] == pytest.approx([0.0, 0.0], abs=5e-5)   # 無彩色は a*=b*=0


def test_primaries_match_the_published_srgb_lab_values():
    """sRGB 原色の L*a*b* は広く公表された既知値と一致すること。"""
    assert M_trans(_px(1, 0, 0), "lab")[0, 0] == pytest.approx(
        [53.241, 80.092, 67.203], abs=2e-3)
    assert M_trans(_px(0, 1, 0), "lab")[0, 0] == pytest.approx(
        [87.735, -86.183, 83.179], abs=2e-3)
    assert M_trans(_px(0, 0, 1), "lab")[0, 0] == pytest.approx(
        [32.297, 79.188, -107.860], abs=2e-3)


def test_luminance_row_is_the_photopic_weighting():
    """Y の行は測光の重み。緑の Y が最大で、3 原色の Y の和が 1 になること。

    公表されている sRGB 行列は 7 桁に丸められているので、Y 行の和は厳密な 1 ではなく
    1.0000001 になる。**丸め由来のずれであって実装の誤りではない**ので、そこまで許す。
    """
    ys = [M_trans(_px(*c), "xyz")[0, 0, 1] for c in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    assert ys[1] > ys[0] > ys[2]
    assert sum(ys) == pytest.approx(1.0, abs=2e-7)


def test_the_two_lab_paths_are_different_scales_on_purpose():
    """CIE の Lab(:mod:`imgmetrics`)と op 台帳の Lab(OpenCV)は**別の尺度**。

    同じ名前なので混ぜられがちだが、片方は L\* が 0-100 の実数、もう片方は uint8 に
    量子化した 8-bit スケール。**一致しないことを固定**しておかないと、どちらかを
    「バグ」と思って揃えてしまう。背景は docs/ops/2d/guides/colorimetry.md。
    """
    import api
    img = np.random.default_rng(0).random((8, 8, 3))
    cie = M.rgb_to_lab(img)
    assert cie[..., 0].max() > 1.5                    # L* は 0-100 の尺度
    assert np.isfinite(cie).all()

    op = api.find_op("trans_from_rgb")
    assert op is not None, "op 台帳側の trans_from_rgb が消えている"
    ledger = np.asarray(op.fn(img, 0.3, 0.5))         # a=0.3 -> Lab を選ぶ
    assert ledger.shape == img.shape
    assert float(ledger.max()) <= 1.0 + 1e-9          # 255 で割った 8-bit 尺度
    # 尺度が違うので、同じ絵でも値は一致しない(これが正しい状態)
    assert not np.allclose(cie, ledger, atol=1.0)
