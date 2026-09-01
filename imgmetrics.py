# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""imgmetrics —— **2 枚の絵がどれだけ違うかを測る** op 族。

動機は fullseye 自身の空白の実測(2026-09-02)。op カタログ全文を grep すると
``ssim`` / ``psnr`` / ``mutual_information`` / ``ciede`` / ``delta_e`` が
**一件もヒットしない**。変換する op(``denoise`` / ``gabor`` / ``wavelet`` /
``inpaint`` / ``anisotropic_diffusion`` …)は数百あるのに、**その出力が入力と
どれだけ違うかを言う op が無かった**。結果として、進化ループの目的関数も
展示の図注も、その場限りの平均二乗誤差を毎回書き直していた。

この族が特別なのは **答え合わせが外からできる**こと。ここが他の族と違う。

* **CIEDE2000 には公開された検証表がある。** Sharma, Wu & Dalal,
  *Color Research & Application* 30(1):21-30, 2005 が、実装が踏み外しやすい
  場所(色相角の平均、275°の項、彩度ゼロ近傍)を狙った **34 組**の Lab 対と
  期待値を公表している。``CIEDE2000_TEST_PAIRS`` にそれを持ち、
  ``tests/test_imgmetrics.py`` が 34 組すべてを 4 桁で照合する。
  **自分の実装が正しいことを、自分以外の基準で言える**数少ない op。
* **SSIM / PSNR / 相互情報量には解析的な既知値がある。** 同じ絵なら SSIM = 1、
  一様乱数の独立な 2 枚なら相互情報量 ≈ 0、``I(X;X) = H(X)``。これらは
  テストで数値ごと固定してある。

## 黙って間違う場所(この族で最も危険なところ)

**``data_range`` を推測しない。** これが本モジュールの中心的な設計判断。
PSNR も SSIM も「取りうる値の幅」で正規化するので、``[0, 1]`` の float を
``[0, 255]`` だと思って測ると **PSNR が 48.13 dB ずれる**(``20*log10(255)``)。
しかも例外は出ず、**それらしい数値が出る**。よって:

* 整数 dtype は dtype から一意に決まる(``uint8`` → 255)。
* float は **決めつけない**。``[0, 1]`` に収まっていれば 1.0 とみなすが、
  1.0 を超える値が 1 つでもあれば ``data_range`` の明示を要求して
  ``ValueError``。「たぶん 255 だろう」で進まない。
* 負値を含む float も同様に明示を要求する(符号つきの差分画像を、そのまま
  画像として PSNR にかけるのは大抵まちがい)。

**SSIM の縁を平均に入れない。** 窓を端に置くと、鏡像で埋めた画素が統計に
混ざる。既定 ``crop_border=True`` は窓の半径ぶんを落としてから平均する。
落とさない実装と比べると、小さい絵ほど値が変わる(テストで差を固定)。

**MS-SSIM は小さい絵で成立しない。** 5 段の縮小を経るので、11 画素の窓が
最終段で成立するには各辺 176 画素が要る。足りなければ**縮小段数を黙って
減らさず** ``ValueError``(段数が違う MS-SSIM 同士は比較できない)。

**相互情報量はビン数に依存する。** ビンを増やすほど上がる(標本が有限なので
上振れする)。``bins`` は既定 64 で明示的な引数にし、
``normalized_mutual_information`` を併置して「上限が何か」を示す。

## 既存資産との棲み分け(再実装せず import して合成)

* **色空間変換は本モジュールが持つ。** カタログに ``rgb_to_lab`` が無く、
  ΔE を測るには要るため。sRGB(IEC 61966-2-1)の伝達関数と D65 白色点、
  CIE 1976 L\\*a\\*b\\* の定義に従う ―― どれも公開規格。
* **エントロピー**は ``entropy_gray`` / ``entropy_image``(backends)が既にあるが、
  あちらは 1 枚の画像の量。ここは **2 枚の同時分布**を扱う(``joint_entropy``)。
  1 枚の周辺エントロピー ``image_entropy`` は同時分布から周辺化して出すので、
  同じ ``bins`` を渡せば ``mutual_information`` と厳密に整合する。
* **ハウスドルフ距離**は ``hausdorff_distance``(既存)。形の距離はあちら、
  画素値の距離はこちら。
* **圧縮**は stdlib の ``zlib`` / ``lzma`` のみ。画像コーデックは使わない
  (コーデックを挟むと NCD が「その実装の癖」を測ってしまう)。

使い方::

    import imgmetrics as M

    M.psnr(a, b)                       # data_range は dtype から
    M.psnr(a, b, data_range=1.0)       # float は明示
    M.ssim(a, b)                       # Wang et al. 2004 の既定(11x11 gauss σ=1.5)
    M.delta_e_2000(lab1, lab2)         # Sharma et al. 2005 の 34 組で検証済
    M.compare_images(a, b)             # 一括。何を測ったかを一緒に返す
"""
from __future__ import annotations

import lzma
import zlib

import numpy as np
from scipy import ndimage

__all__ = [
    # 色空間
    "srgb_to_linear", "linear_to_srgb", "rgb_to_xyz", "xyz_to_lab",
    "rgb_to_lab", "lab_to_rgb", "D65_WHITE",
    # 色差
    "delta_e_76", "delta_e_2000", "delta_e_map", "CIEDE2000_TEST_PAIRS",
    # 忠実度
    "mse", "rmse", "psnr", "ssim", "ssim_map", "ms_ssim", "MS_SSIM_WEIGHTS",
    # 情報量
    "joint_histogram", "image_entropy", "joint_entropy",
    "mutual_information", "normalized_mutual_information",
    # 圧縮
    "compressed_size", "ncd",
    # まとめ
    "compare_images", "data_range_of",
]


# =========================================================================
# data_range —— この族で最も黙って間違いやすい場所
# =========================================================================

_INT_RANGES = {
    np.dtype(np.uint8): 255.0,
    np.dtype(np.uint16): 65535.0,
    np.dtype(np.uint32): 4294967295.0,
    np.dtype(np.int8): 255.0,
    np.dtype(np.int16): 65535.0,
}


def data_range_of(*arrays, data_range=None):
    """画素値が取りうる幅を決める。**推測はしない**。

    整数 dtype は dtype から一意に決まる。float は ``[0, 1]`` に収まっている
    ときだけ 1.0 とみなし、それ以外は ``data_range`` の明示を要求する。

    ``[0, 1]`` の float を 255 だと思って PSNR を測ると **48.13 dB** ずれるが
    例外は出ない ―― それらしい数値が出るだけなので、ここで止める。

    Parameters
    ----------
    *arrays : ndarray
        同じ画素値の約束を共有するはずの配列(通常 2 枚)。
    data_range : float, optional
        明示する場合の幅。正の有限値でなければ ``ValueError``。

    Returns
    -------
    float
    """
    if data_range is not None:
        dr = float(data_range)
        if not np.isfinite(dr) or dr <= 0.0:
            raise ValueError(f"data_range must be a positive finite number, got {data_range!r}")
        return dr

    arrays = [np.asarray(a) for a in arrays]
    dts = {a.dtype for a in arrays}
    if len(dts) > 1:
        raise ValueError(
            "data_range cannot be inferred from mixed dtypes "
            f"{sorted(str(d) for d in dts)}; pass data_range= explicitly"
        )
    dt = dts.pop()

    if dt in _INT_RANGES:
        return _INT_RANGES[dt]
    if dt == np.dtype(bool):
        return 1.0
    if not np.issubdtype(dt, np.floating):
        raise ValueError(f"data_range cannot be inferred from dtype {dt}; pass data_range= explicitly")

    lo = min(float(np.min(a)) for a in arrays)
    hi = max(float(np.max(a)) for a in arrays)
    if not (np.isfinite(lo) and np.isfinite(hi)):
        raise ValueError("array contains non-finite values; data_range cannot be inferred")
    if lo < 0.0:
        raise ValueError(
            f"float array holds negative values (min={lo:.6g}), so its range is not [0, 1]; "
            "pass data_range= explicitly (a signed difference image is usually not what "
            "PSNR/SSIM should be measured on)"
        )
    if hi > 1.0:
        raise ValueError(
            f"float array reaches {hi:.6g} > 1, so it is not the [0, 1] convention; "
            "pass data_range= explicitly (guessing 255 here would shift PSNR by "
            "20*log10(255) = 48.13 dB without raising)"
        )
    return 1.0


def _as_float_pair(a, b, name_a="a", name_b="b"):
    a = np.asarray(a)
    b = np.asarray(b)
    if a.shape != b.shape:
        raise ValueError(f"{name_a} and {name_b} must have the same shape, got {a.shape} and {b.shape}")
    if a.size == 0:
        raise ValueError("empty arrays have no measurable difference")
    fa = a.astype(np.float64, copy=False)
    fb = b.astype(np.float64, copy=False)
    if not (np.all(np.isfinite(fa)) and np.all(np.isfinite(fb))):
        raise ValueError("arrays must be finite; NaN/Inf would propagate into the metric silently")
    return fa, fb


# =========================================================================
# 色空間 —— sRGB (IEC 61966-2-1) / CIE 1976 L*a*b*
# =========================================================================

#: CIE standard illuminant D65, 2° observer(Xn, Yn, Zn)。Y = 1 に正規化。
D65_WHITE = (0.95047, 1.00000, 1.08883)

# sRGB(D65)→ CIE XYZ。IEC 61966-2-1 の行列。
_M_RGB2XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
], dtype=np.float64)
_M_XYZ2RGB = np.linalg.inv(_M_RGB2XYZ)


def _to_unit_float(rgb):
    """整数 dtype の画像を ``[0, 1]`` の float にする(float はそのまま検査)。"""
    x = np.asarray(rgb)
    if x.dtype in _INT_RANGES:
        return x.astype(np.float64) / _INT_RANGES[x.dtype]
    x = x.astype(np.float64, copy=False)
    if x.size and (np.nanmin(x) < -1e-6 or np.nanmax(x) > 1.0 + 1e-6):
        raise ValueError(
            f"sRGB values must lie in [0, 1] (or be an integer dtype), got "
            f"[{float(np.nanmin(x)):.6g}, {float(np.nanmax(x)):.6g}]"
        )
    return np.clip(x, 0.0, 1.0)


def srgb_to_linear(rgb):
    """sRGB の伝達関数を外して線形 RGB にする(IEC 61966-2-1)。

    **実体は :func:`gfx2d.srgb_to_linear`。** ここは整数 dtype を ``[0, 1]`` に
    正規化してから委譲するだけの薄い入口で、伝達関数そのものは一箇所にしかない
    (2 つ持つと片方だけ直したときに**例外なく違う色**が出る)。
    実測で両者は ``[0, 1]`` の 257 点にわたり **最大差 0.0** で一致していたので、
    こちらの重複実装を削除して委譲に置き換えた(2026-09-02)。

    **ガンマを二度外す**のがこの手の処理で最も多い間違い ―― 線形値を受け取った
    つもりで再度これを掛けないこと(``linear_to_srgb`` が逆)。
    """
    return _elementwise_transfer("srgb_to_linear", _to_unit_float(rgb))


def linear_to_srgb(lin):
    """線形 RGB に sRGB の伝達関数を掛ける(``srgb_to_linear`` の逆)。

    実体は :func:`gfx2d.linear_to_srgb`(上と同じ理由で委譲)。
    """
    return _elementwise_transfer("linear_to_srgb",
                                 np.clip(np.asarray(lin, dtype=np.float64), 0.0, 1.0))


def _elementwise_transfer(fname, x):
    """``gfx2d`` の伝達関数を**任意の形**に適用する。

    ``gfx2d`` 側は画像 API なので ``(H, W)`` / ``(H, W, 3)`` / ``(H, W, 4)``
    しか受けない。一方こちらは ``(3,)`` の 1 色や ``(N, 3)`` の色表も測る。
    sRGB の伝達関数は**画素ごと・チャネルごとに独立**なので、``(1, -1)`` に
    畳んで通し、元の形に戻せば厳密に同じ値になる ―― 形を変えるだけで、
    計算そのものは 1 か所にしか無い状態を保てる。
    """
    import gfx2d
    x = np.asarray(x, dtype=np.float64)
    flat = gfx2d.__dict__[fname](x.reshape(1, -1) if x.size else np.zeros((1, 1)))
    return np.asarray(flat).reshape(x.shape) if x.size else x.copy()


def rgb_to_xyz(rgb):
    """sRGB(``(..., 3)``)→ CIE XYZ。伝達関数を外してから行列を掛ける。"""
    lin = srgb_to_linear(rgb)
    if lin.shape[-1] != 3:
        raise ValueError(f"rgb must have 3 channels in the last axis, got shape {lin.shape}")
    return lin @ _M_RGB2XYZ.T


def xyz_to_lab(xyz, white=D65_WHITE):
    """CIE XYZ → CIE 1976 L\\*a\\*b\\*。既定の白色点は D65 2°。"""
    xyz = np.asarray(xyz, dtype=np.float64)
    if xyz.shape[-1] != 3:
        raise ValueError(f"xyz must have 3 channels in the last axis, got shape {xyz.shape}")
    wn = np.asarray(white, dtype=np.float64)
    if wn.shape != (3,) or np.any(wn <= 0):
        raise ValueError(f"white point must be 3 positive numbers, got {white!r}")
    t = xyz / wn
    delta = 6.0 / 29.0
    f = np.where(t > delta ** 3, np.cbrt(t), t / (3.0 * delta ** 2) + 4.0 / 29.0)
    L = 116.0 * f[..., 1] - 16.0
    a = 500.0 * (f[..., 0] - f[..., 1])
    b = 200.0 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def rgb_to_lab(rgb, white=D65_WHITE):
    """sRGB → CIE L\\*a\\*b\\*(D65)。ΔE を測る前段。"""
    return xyz_to_lab(rgb_to_xyz(rgb), white=white)


def lab_to_rgb(lab, white=D65_WHITE):
    """CIE L\\*a\\*b\\* → sRGB ``[0, 1]``。**色域外は切り詰められる**ので
    ``rgb_to_lab`` との往復は色域内でしか一致しない(テストで固定)。"""
    lab = np.asarray(lab, dtype=np.float64)
    if lab.shape[-1] != 3:
        raise ValueError(f"lab must have 3 channels in the last axis, got shape {lab.shape}")
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0
    delta = 6.0 / 29.0
    finv = lambda f: np.where(f > delta, f ** 3, 3.0 * delta ** 2 * (f - 4.0 / 29.0))
    xyz = np.stack([finv(fx), finv(fy), finv(fz)], axis=-1) * np.asarray(white, dtype=np.float64)
    return linear_to_srgb(xyz @ _M_XYZ2RGB.T)


# =========================================================================
# 色差
# =========================================================================

def delta_e_76(lab1, lab2):
    """CIE76 色差 ―― Lab 空間のユークリッド距離。

    単純だが**知覚と合わない**(特に彩度の高い青)ので、比較の基準としてのみ
    置いてある。実用は :func:`delta_e_2000`。
    """
    l1 = np.asarray(lab1, dtype=np.float64)
    l2 = np.asarray(lab2, dtype=np.float64)
    if l1.shape[-1] != 3 or l2.shape[-1] != 3:
        raise ValueError("lab inputs must have 3 channels in the last axis")
    return np.sqrt(np.sum((l1 - l2) ** 2, axis=-1))


def delta_e_2000(lab1, lab2, kL=1.0, kC=1.0, kH=1.0):
    """CIEDE2000 色差(CIE 142-2001)。

    実装が踏み外しやすい 3 か所 ―― **色相角の平均**(0/360 をまたぐ扱い)、
    **275° の回転項**、**彩度ゼロ近傍**(``atan2(0, 0)`` の扱い)―― は
    Sharma, Wu & Dalal (2005) の 34 組の検証対で固定してある
    (``CIEDE2000_TEST_PAIRS`` / ``tests/test_imgmetrics.py``)。

    Parameters
    ----------
    lab1, lab2 : array_like
        最後の軸が ``(L*, a*, b*)`` の配列。ブロードキャストされる。
    kL, kC, kH : float
        観察条件のパラメトリック係数。既定は基準条件の 1。

    Returns
    -------
    ndarray
        ΔE00(最後の軸が落ちた形)。
    """
    l1 = np.asarray(lab1, dtype=np.float64)
    l2 = np.asarray(lab2, dtype=np.float64)
    if l1.shape[-1] != 3 or l2.shape[-1] != 3:
        raise ValueError("lab inputs must have 3 channels in the last axis")
    for k, nm in ((kL, "kL"), (kC, "kC"), (kH, "kH")):
        if not np.isfinite(k) or k <= 0:
            raise ValueError(f"{nm} must be a positive finite number, got {k!r}")

    L1, a1, b1 = l1[..., 0], l1[..., 1], l1[..., 2]
    L2, a2, b2 = l2[..., 0], l2[..., 1], l2[..., 2]

    C1 = np.hypot(a1, b1)
    C2 = np.hypot(a2, b2)
    Cbar = 0.5 * (C1 + C2)
    G = 0.5 * (1.0 - np.sqrt(Cbar ** 7 / (Cbar ** 7 + 25.0 ** 7)))
    a1p = (1.0 + G) * a1
    a2p = (1.0 + G) * a2
    C1p = np.hypot(a1p, b1)
    C2p = np.hypot(a2p, b2)

    # 色相角。彩度が 0 のとき a' も b' も 0 なので atan2(0,0)=0 になるが、
    # CIE 142-2001 はこの場合の色相を「定義しない」としており、後段の差分では
    # 0 として扱ってよい(下の np.where がそれを保証する)。
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0

    dLp = L2 - L1
    dCp = C2p - C1p

    Cprod = C1p * C2p
    dhp = h2p - h1p
    dhp = np.where(dhp > 180.0, dhp - 360.0, dhp)
    dhp = np.where(dhp < -180.0, dhp + 360.0, dhp)
    dhp = np.where(Cprod == 0.0, 0.0, dhp)           # 片方が無彩色なら色相差なし
    dHp = 2.0 * np.sqrt(Cprod) * np.sin(np.radians(0.5 * dhp))

    Lbarp = 0.5 * (L1 + L2)
    Cbarp = 0.5 * (C1p + C2p)

    # 平均色相。0/360 をまたぐ場合の場合分けが CIEDE2000 の要点のひとつ。
    hsum = h1p + h2p
    hdiff = np.abs(h1p - h2p)
    hbarp = np.where(
        Cprod == 0.0,
        hsum,                                          # 無彩色: 和をそのまま(片方は 0)
        np.where(
            hdiff <= 180.0,
            0.5 * hsum,
            np.where(hsum < 360.0, 0.5 * (hsum + 360.0), 0.5 * (hsum - 360.0)),
        ),
    )

    T = (1.0
         - 0.17 * np.cos(np.radians(hbarp - 30.0))
         + 0.24 * np.cos(np.radians(2.0 * hbarp))
         + 0.32 * np.cos(np.radians(3.0 * hbarp + 6.0))
         - 0.20 * np.cos(np.radians(4.0 * hbarp - 63.0)))

    dtheta = 30.0 * np.exp(-(((hbarp - 275.0) / 25.0) ** 2))
    RC = 2.0 * np.sqrt(Cbarp ** 7 / (Cbarp ** 7 + 25.0 ** 7))
    SL = 1.0 + (0.015 * (Lbarp - 50.0) ** 2) / np.sqrt(20.0 + (Lbarp - 50.0) ** 2)
    SC = 1.0 + 0.045 * Cbarp
    SH = 1.0 + 0.015 * Cbarp * T
    RT = -np.sin(np.radians(2.0 * dtheta)) * RC

    tL = dLp / (kL * SL)
    tC = dCp / (kC * SC)
    tH = dHp / (kH * SH)
    return np.sqrt(tL ** 2 + tC ** 2 + tH ** 2 + RT * tC * tH)


def delta_e_map(rgb1, rgb2, kind="2000", white=D65_WHITE):
    """2 枚の **sRGB 画像**の画素ごとの色差マップ。

    RGB の平均二乗誤差ではなく**知覚的な色差**で見るための入口。
    ``kind`` は ``"2000"``(既定)または ``"76"``。
    """
    if kind not in ("2000", "76"):
        raise ValueError(f"kind must be '2000' or '76', got {kind!r}")
    a = np.asarray(rgb1)
    b = np.asarray(rgb2)
    if a.shape != b.shape:
        raise ValueError(f"images must have the same shape, got {a.shape} and {b.shape}")
    if a.ndim < 3 or a.shape[-1] != 3:
        raise ValueError(f"delta_e_map needs RGB images with 3 channels last, got shape {a.shape}")
    la = rgb_to_lab(a, white=white)
    lb = rgb_to_lab(b, white=white)
    return delta_e_2000(la, lb) if kind == "2000" else delta_e_76(la, lb)


#: Sharma, Wu & Dalal, *Color Res. Appl.* 30(1):21-30, 2005 の CIEDE2000
#: 検証対。``(L1, a1, b1, L2, a2, b2, expected_dE00)``。実装が踏み外しやすい
#: 場所(色相の折り返し、275° の項、無彩色近傍)を狙って選ばれている。
CIEDE2000_TEST_PAIRS = (
    (50.0000, 2.6772, -79.7751, 50.0000, 0.0000, -82.7485, 2.0425),
    (50.0000, 3.1571, -77.2803, 50.0000, 0.0000, -82.7485, 2.8615),
    (50.0000, 2.8361, -74.0200, 50.0000, 0.0000, -82.7485, 3.4412),
    (50.0000, -1.3802, -84.2814, 50.0000, 0.0000, -82.7485, 1.0000),
    (50.0000, -1.1848, -84.8006, 50.0000, 0.0000, -82.7485, 1.0000),
    (50.0000, -0.9009, -85.5211, 50.0000, 0.0000, -82.7485, 1.0000),
    (50.0000, 0.0000, 0.0000, 50.0000, -1.0000, 2.0000, 2.3669),
    (50.0000, -1.0000, 2.0000, 50.0000, 0.0000, 0.0000, 2.3669),
    (50.0000, 2.4900, -0.0010, 50.0000, -2.4900, 0.0009, 7.1792),
    (50.0000, 2.4900, -0.0010, 50.0000, -2.4900, 0.0010, 7.1792),
    (50.0000, 2.4900, -0.0010, 50.0000, -2.4900, 0.0011, 7.2195),
    (50.0000, 2.4900, -0.0010, 50.0000, -2.4900, 0.0012, 7.2195),
    (50.0000, -0.0010, 2.4900, 50.0000, 0.0009, -2.4900, 4.8045),
    (50.0000, -0.0010, 2.4900, 50.0000, 0.0010, -2.4900, 4.8045),
    (50.0000, -0.0010, 2.4900, 50.0000, 0.0011, -2.4900, 4.7461),
    (50.0000, 2.5000, 0.0000, 50.0000, 0.0000, -2.5000, 4.3065),
    (50.0000, 2.5000, 0.0000, 73.0000, 25.0000, -18.0000, 27.1492),
    (50.0000, 2.5000, 0.0000, 61.0000, -5.0000, 29.0000, 22.8977),
    (50.0000, 2.5000, 0.0000, 56.0000, -27.0000, -3.0000, 31.9030),
    (50.0000, 2.5000, 0.0000, 58.0000, 24.0000, 15.0000, 19.4535),
    (50.0000, 2.5000, 0.0000, 50.0000, 3.1736, 0.5854, 1.0000),
    (50.0000, 2.5000, 0.0000, 50.0000, 3.2972, 0.0000, 1.0000),
    (50.0000, 2.5000, 0.0000, 50.0000, 1.8634, 0.5757, 1.0000),
    (50.0000, 2.5000, 0.0000, 50.0000, 3.2592, 0.3350, 1.0000),
    (60.2574, -34.0099, 36.2677, 60.4626, -34.1751, 39.4387, 1.2644),
    (63.0109, -31.0961, -5.8663, 62.8187, -29.7946, -4.0864, 1.2630),
    (61.2901, 3.7196, -5.3901, 61.4292, 2.2480, -4.9620, 1.8731),
    (35.0831, -44.1164, 3.7933, 35.0232, -40.0716, 1.5901, 1.8645),
    (22.7233, 20.0904, -46.6940, 23.0331, 14.9730, -42.5619, 2.0373),
    (36.4612, 47.8580, 18.3852, 36.2715, 50.5065, 21.2231, 1.4146),
    (90.8027, -2.0831, 1.4410, 91.1528, -1.6435, 0.0447, 1.4441),
    (90.9257, -0.5406, -0.9208, 88.6381, -0.8985, -0.7239, 1.5381),
    (6.7747, -0.2908, -2.4247, 5.8714, -0.0985, -2.2286, 0.6377),
    (2.0776, 0.0795, -1.1350, 0.9033, -0.0636, -0.5514, 0.9082),
)


# =========================================================================
# 忠実度 —— MSE / PSNR / SSIM / MS-SSIM
# =========================================================================

def mse(a, b):
    """平均二乗誤差。``data_range`` に依らない生の量。"""
    fa, fb = _as_float_pair(a, b)
    return float(np.mean((fa - fb) ** 2))


def rmse(a, b):
    """平均二乗誤差の平方根(画素値と同じ単位)。"""
    return float(np.sqrt(mse(a, b)))


def psnr(a, b, data_range=None):
    """ピーク信号対雑音比 [dB]。

    完全に一致する 2 枚では **``inf``** を返す(0 除算を黙って回避するために
    小さな値を足したりしない ―― それは「非常に良い一致」を有限の数値に化かし、
    平均を取ったときに嘘になる)。

    ``data_range`` の決め方は :func:`data_range_of` を参照。
    """
    fa, fb = _as_float_pair(a, b)
    dr = data_range_of(a, b, data_range=data_range)
    e = float(np.mean((fa - fb) ** 2))
    if e == 0.0:
        return float("inf")
    return float(10.0 * np.log10(dr ** 2 / e))


def _ssim_channel(fa, fb, dr, win_size, sigma, K1, K2, crop_border):
    """1 チャネルぶんの SSIM マップ(縁を落とす前)。"""
    C1 = (K1 * dr) ** 2
    C2 = (K2 * dr) ** 2
    flt = lambda x: ndimage.gaussian_filter(x, sigma=sigma, truncate=(win_size - 1) / 2.0 / sigma,
                                            mode="reflect")
    mu_a = flt(fa)
    mu_b = flt(fb)
    mu_aa = mu_a * mu_a
    mu_bb = mu_b * mu_b
    mu_ab = mu_a * mu_b
    # 母分散(Wang et al. 2004 の重み付き定義。標本分散への補正は入れない)
    sa = flt(fa * fa) - mu_aa
    sb = flt(fb * fb) - mu_bb
    sab = flt(fa * fb) - mu_ab
    num = (2.0 * mu_ab + C1) * (2.0 * sab + C2)
    den = (mu_aa + mu_bb + C1) * (sa + sb + C2)
    smap = num / den
    if crop_border:
        pad = (win_size - 1) // 2
        if any(d <= 2 * pad for d in smap.shape):
            raise ValueError(
                f"image {smap.shape} is too small for an {win_size}x{win_size} window once the "
                f"border is cropped; pass a larger image, a smaller win_size, or crop_border=False"
            )
        sl = tuple(slice(pad, d - pad) for d in smap.shape)
        smap = smap[sl]
    return smap


def _prep_ssim(a, b, data_range, win_size, sigma, channel_axis):
    fa, fb = _as_float_pair(a, b)
    dr = data_range_of(a, b, data_range=data_range)
    if win_size % 2 == 0 or win_size < 3:
        raise ValueError(f"win_size must be an odd integer >= 3, got {win_size}")
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError(f"sigma must be a positive finite number, got {sigma!r}")
    if channel_axis is None:
        planes = [(fa, fb)]
        spatial = fa.shape
    else:
        fa2 = np.moveaxis(fa, channel_axis, 0)
        fb2 = np.moveaxis(fb, channel_axis, 0)
        planes = list(zip(fa2, fb2))
        spatial = fa2.shape[1:]
    if any(d < win_size for d in spatial):
        raise ValueError(
            f"each spatial axis must be at least win_size={win_size}, got {spatial}"
        )
    return planes, dr, spatial


def ssim_map(a, b, data_range=None, win_size=11, sigma=1.5, K1=0.01, K2=0.03,
             channel_axis=None, crop_border=True):
    """SSIM の**マップ**(平均を取る前)。どこが似ていないかを絵で見るため。

    ``channel_axis`` を指定するとチャネルごとに計算し、その平均マップを返す。
    """
    planes, dr, _ = _prep_ssim(a, b, data_range, win_size, sigma, channel_axis)
    maps = [_ssim_channel(pa, pb, dr, win_size, sigma, K1, K2, crop_border) for pa, pb in planes]
    return maps[0] if len(maps) == 1 else np.mean(np.stack(maps, axis=0), axis=0)


def ssim(a, b, data_range=None, win_size=11, sigma=1.5, K1=0.01, K2=0.03,
         channel_axis=None, crop_border=True):
    """構造的類似度(Wang, Bovik, Sheikh & Simoncelli, IEEE TIP 13(4), 2004)。

    既定は原論文の設定 ―― **11x11 のガウシアン窓 σ=1.5、K1=0.01、K2=0.03**、
    重み付き**母**分散(標本分散への ``n/(n-1)`` 補正を入れない)。

    ``crop_border=True``(既定)は窓の半径ぶんの縁を平均から落とす。縁では
    鏡像で埋めた画素が統計に混ざるため。**落とすかどうかで値が変わる**ので、
    他所の数値と比べるときは必ずこの設定を揃えること(小さい絵ほど差が出る)。

    Returns
    -------
    float
        1.0 が完全一致。
    """
    return float(np.mean(ssim_map(a, b, data_range=data_range, win_size=win_size, sigma=sigma,
                                  K1=K1, K2=K2, channel_axis=channel_axis,
                                  crop_border=crop_border)))


#: MS-SSIM の段ごとの重み(Wang, Simoncelli & Bovik, Asilomar Conf. 2003)。
#:
#: **この 5 つの和は 1 ではなく 1.0001**(実測: ``sum`` が厳密に ``1.0001``)。
#: 原論文が小数 4 桁で丸めて公表した値をそのまま使うのが慣例で、正規化して
#: 使う実装と 1e-4 のずれが出る。**黙って正規化しない** ―― 他所の MS-SSIM と
#: 比べたときの微差の出所がここだと分かるようにしておく方が大事。
#: よって ``ms_ssim`` の重み検査の許容は 1e-3(``tests/test_imgmetrics.py``)。
MS_SSIM_WEIGHTS = (0.0448, 0.2856, 0.3001, 0.2363, 0.1333)


def _downsample2(x):
    """2x2 平均でプールしてから間引く(MS-SSIM の標準的な縮小)。"""
    h, w = x.shape[-2], x.shape[-1]
    x = x[..., : h - h % 2, : w - w % 2]
    return 0.25 * (x[..., 0::2, 0::2] + x[..., 1::2, 0::2] + x[..., 0::2, 1::2] + x[..., 1::2, 1::2])


def ms_ssim(a, b, data_range=None, win_size=11, sigma=1.5, K1=0.01, K2=0.03,
            weights=MS_SSIM_WEIGHTS, crop_border=True):
    """多尺度 SSIM(Wang, Simoncelli & Bovik, Asilomar Conf. 2003)。

    5 段の縮小を経るので、最終段で 11 画素の窓が成立するには**各辺 176 画素**が
    要る。足りないときに**段数を黙って減らさない** ―― 段数の違う MS-SSIM は
    別の指標であり、比べると嘘になる。足りなければ ``ValueError``。

    2 次元のグレー画像専用(色は ``channel_axis`` ではなくチャネルごとに呼ぶ)。
    """
    fa, fb = _as_float_pair(a, b)
    if fa.ndim != 2:
        raise ValueError(f"ms_ssim takes 2-D grayscale images, got shape {fa.shape}")
    dr = data_range_of(a, b, data_range=data_range)
    w = np.asarray(weights, dtype=np.float64)
    # 許容が 1e-3 なのは、原論文の公表値そのものが 1.0001 に和が立つため
    # (:data:`MS_SSIM_WEIGHTS` の注記)。正規化して黙って直したりはしない。
    if w.ndim != 1 or w.size < 2 or np.any(w < 0) or not np.isclose(w.sum(), 1.0, atol=1e-3):
        raise ValueError(
            "weights must be a 1-D non-negative array summing to 1 (within 1e-3; the published "
            f"MS-SSIM weights sum to {sum(MS_SSIM_WEIGHTS)!r}, which is why the tolerance is "
            f"not tighter), got sum={float(w.sum())!r}"
        )
    n = w.size
    need = (win_size - 1) * (2 ** (n - 1)) + 2 ** (n - 1)
    if min(fa.shape) < need:
        raise ValueError(
            f"ms_ssim with {n} scales and win_size={win_size} needs every axis to be at least "
            f"{need} px, got {fa.shape}; use fewer scales (weights=) or a bigger image "
            "(silently dropping a scale would produce a number that is not comparable)"
        )

    C1 = (K1 * dr) ** 2
    C2 = (K2 * dr) ** 2
    flt = lambda x: ndimage.gaussian_filter(x, sigma=sigma, truncate=(win_size - 1) / 2.0 / sigma,
                                            mode="reflect")
    pad = (win_size - 1) // 2
    mcs = []
    x, y = fa, fb
    for i in range(n):
        mu_x, mu_y = flt(x), flt(y)
        sx = flt(x * x) - mu_x * mu_x
        sy = flt(y * y) - mu_y * mu_y
        sxy = flt(x * y) - mu_x * mu_y
        cs = (2.0 * sxy + C2) / (sx + sy + C2)
        lum = (2.0 * mu_x * mu_y + C1) / (mu_x * mu_x + mu_y * mu_y + C1)
        if crop_border:
            sl = tuple(slice(pad, d - pad) for d in cs.shape)
            cs, lum = cs[sl], lum[sl]
        mcs.append((float(np.mean(np.maximum(cs, 0.0))), float(np.mean(np.maximum(lum, 0.0)))))
        if i < n - 1:
            x, y = _downsample2(x), _downsample2(y)

    out = 1.0
    for i in range(n - 1):
        out *= mcs[i][0] ** w[i]
    out *= (mcs[-1][0] * mcs[-1][1]) ** w[-1]
    return float(out)


# =========================================================================
# 情報量
# =========================================================================

def _binned(a, b, bins, data_range):
    fa, fb = _as_float_pair(a, b)
    if not isinstance(bins, (int, np.integer)) or bins < 2:
        raise ValueError(f"bins must be an integer >= 2, got {bins!r}")
    dr = data_range_of(a, b, data_range=data_range)
    lo = min(float(fa.min()), float(fb.min()))
    return fa.ravel(), fb.ravel(), int(bins), (lo, lo + dr)


def joint_histogram(a, b, bins=64, data_range=None):
    """2 枚の同時ヒストグラム(正規化した同時確率)。

    ビン幅は ``data_range`` から決める ―― 画像ごとに min/max で伸縮させると、
    **一様に暗い絵と一様に明るい絵の相互情報量が同じになる**ので。
    """
    x, y, nb, rng = _binned(a, b, bins, data_range)
    h, _, _ = np.histogram2d(x, y, bins=nb, range=[rng, rng])
    total = h.sum()
    if total == 0:
        raise ValueError("no samples fell inside the data range; check data_range")
    return h / total


def _entropy(p):
    p = p[p > 0]
    return float(-np.sum(p * np.log2(p)))


def image_entropy(a, bins=64, data_range=None):
    """1 枚のシャノンエントロピー [bit]。

    ``mutual_information`` と**同じビン割り**で出すので、
    ``mutual_information(a, a) == image_entropy(a)`` が厳密に成り立つ
    (テストで固定)。既存の ``entropy_gray`` / ``entropy_image``(backends)は
    別のビン割りなので値は一致しない ―― こちらは同時分布と整合する側。
    """
    return _entropy(joint_histogram(a, a, bins=bins, data_range=data_range).sum(axis=1))


def joint_entropy(a, b, bins=64, data_range=None):
    """同時エントロピー H(A, B) [bit]。"""
    return _entropy(joint_histogram(a, b, bins=bins, data_range=data_range))


def mutual_information(a, b, bins=64, data_range=None):
    """相互情報量 I(A; B) [bit] = H(A) + H(B) - H(A, B)。

    **ビン数に依存する**(増やすほど上振れする)ので ``bins`` は明示的な引数。
    独立な 2 枚でも標本が有限なので厳密に 0 にはならない ―― どれくらい上振れ
    するかはテストに数値で残してある。
    """
    pab = joint_histogram(a, b, bins=bins, data_range=data_range)
    return _entropy(pab.sum(axis=1)) + _entropy(pab.sum(axis=0)) - _entropy(pab)


def normalized_mutual_information(a, b, bins=64, data_range=None):
    """正規化相互情報量 2*I(A;B) / (H(A) + H(B))。同じ絵で 1.0。

    周辺エントロピーが両方 0(どちらも一様な絵)のときは、**上限が 0 なので
    比が定義できない** ―― 0 除算を避けるために 0 や 1 を返さず ``ValueError``。
    """
    pab = joint_histogram(a, b, bins=bins, data_range=data_range)
    ha = _entropy(pab.sum(axis=1))
    hb = _entropy(pab.sum(axis=0))
    if ha + hb == 0.0:
        raise ValueError(
            "both images are constant, so H(A) = H(B) = 0 and the normalising bound is 0; "
            "normalized mutual information is undefined here (returning 0 or 1 would be a guess)"
        )
    return float(2.0 * (ha + hb - _entropy(pab)) / (ha + hb))


# =========================================================================
# 圧縮距離
# =========================================================================

_COMPRESSORS = {"zlib": lambda b: zlib.compress(b, 9), "lzma": lzma.compress}


def compressed_size(a, compressor="lzma"):
    """配列を可逆圧縮したバイト数。``ncd`` の材料。

    画像コーデックは**使わない** ―― 挟むとその実装の癖を測ってしまう。
    stdlib の ``zlib`` / ``lzma`` のみ。dtype と shape の違いが結果を変える
    ので、比べる 2 枚は同じ dtype・同じ shape であること。
    """
    if compressor not in _COMPRESSORS:
        raise ValueError(f"compressor must be one of {sorted(_COMPRESSORS)}, got {compressor!r}")
    return len(_COMPRESSORS[compressor](np.ascontiguousarray(np.asarray(a)).tobytes()))


def ncd(a, b, compressor="lzma"):
    """正規化圧縮距離(Li, Chen, Li, Ma & Vitányi, IEEE TIT 50(12), 2004)。

    ``NCD(x,y) = (C(xy) - min(C(x),C(y))) / max(C(x),C(y))``。
    同じものなら 0 に近づき、無関係なら 1 に近づく ―― ただし **実際の圧縮器は
    理想的な Kolmogorov 複雑度ではない**ので、同一入力でも厳密に 0 にはならない
    (ヘッダぶんの下駄がある)。その下駄の実測値はテストに残してある。
    """
    a = np.asarray(a)
    b = np.asarray(b)
    if a.dtype != b.dtype or a.shape != b.shape:
        raise ValueError(
            f"ncd compares like with like: dtypes {a.dtype}/{b.dtype}, shapes {a.shape}/{b.shape}"
        )
    ca = compressed_size(a, compressor)
    cb = compressed_size(b, compressor)
    joined = np.ascontiguousarray(a).tobytes() + np.ascontiguousarray(b).tobytes()
    cab = len(_COMPRESSORS[compressor](joined))
    return float((cab - min(ca, cb)) / max(ca, cb))


# =========================================================================
# まとめ
# =========================================================================

def compare_images(a, b, data_range=None, bins=64, channel_axis=None, ms=False):
    """一括で測り、**何をどう測ったかを一緒に返す**。

    返り値の ``contract`` に ``data_range`` / ``bins`` / ``crop_border`` /
    SSIM の窓を入れてあるのは、数値だけを図注に写して**条件が消える**のを
    防ぐため(この repo で実際に起きた事故の型)。

    Returns
    -------
    dict
        ``{"mse", "rmse", "psnr", "ssim", "mutual_information",
        "normalized_mutual_information", "ncd", "contract": {...}}``。
        ``ms=True`` なら ``ms_ssim`` も(成立しない大きさなら ``ValueError``)。
        カラー画像で ``channel_axis`` を渡すと ``delta_e_2000_mean`` も入る。
    """
    dr = data_range_of(a, b, data_range=data_range)
    out = {
        "mse": mse(a, b),
        "rmse": rmse(a, b),
        "psnr": psnr(a, b, data_range=dr),
        "ssim": ssim(a, b, data_range=dr, channel_axis=channel_axis),
        "mutual_information": mutual_information(a, b, bins=bins, data_range=dr),
        "ncd": ncd(np.asarray(a), np.asarray(b)),
    }
    try:
        out["normalized_mutual_information"] = normalized_mutual_information(
            a, b, bins=bins, data_range=dr)
    except ValueError:
        out["normalized_mutual_information"] = None      # 両方一様: 上限が 0
    if ms:
        out["ms_ssim"] = ms_ssim(a, b, data_range=dr)
    if channel_axis is not None and np.asarray(a).shape[channel_axis] == 3:
        aa = np.moveaxis(np.asarray(a), channel_axis, -1)
        bb = np.moveaxis(np.asarray(b), channel_axis, -1)
        if dr != 1.0:
            aa = aa / dr
            bb = bb / dr
        out["delta_e_2000_mean"] = float(np.mean(delta_e_map(aa, bb)))
    out["contract"] = {
        "data_range": dr,
        "bins": bins,
        "ssim_win_size": 11,
        "ssim_sigma": 1.5,
        "ssim_crop_border": True,
        "ncd_compressor": "lzma",
    }
    return out


if __name__ == "__main__":     # pragma: no cover - 手元確認用
    worst = 0.0
    for L1, a1, b1, L2, a2, b2, want in CIEDE2000_TEST_PAIRS:
        got = float(delta_e_2000((L1, a1, b1), (L2, a2, b2)))
        worst = max(worst, abs(got - want))
    print(f"CIEDE2000: {len(CIEDE2000_TEST_PAIRS)} 対の最大誤差 {worst:.2e}")
