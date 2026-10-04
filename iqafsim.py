# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""知覚指標 FSIM / FSIMc / GMSD / VIF(画素領域版)を numpy + scipy だけで —— TID2013 の作者値と 4 桁一致する規約で(iqafsim、2026-10-04)。

第 1 弾 :mod:`iqatid` は TID2013(Ponomarenko ほか 2015)の 3,000 組と作者同梱の値ファイルで PSNR / SSIM を門にした。ここはその続きで、
作者値ファイルがある 3 指標(FSIM.txt / FSIMc.txt / VIFP.txt)と、配布物より後に出た GMSD を実装する。全部 **外から来た真値で 4 桁一致**
させた(3,000 組の行ごと max |差| 5.0e-5 / 5.0e-5 / 6.8e-5 —— 作者値 4 桁の丸め幅の中)。

一次情報:
  * FSIM / FSIMc —— Zhang, Zhang, Mou, Zhang, IEEE TIP 20(8) 2378–2386, 2011, DOI 10.1109/TIP.2011.2109730(式 4 の位相一致 PC、式 7–13 の
    S_PC・S_G・S_C・プーリング、式 15–17 の YIQ、§IV-A の定数)。位相一致は Kovesi, Videre 1(3), 1999 の式。雑音しきい値の経験則(Rayleigh の平均
    = −median/ln 0.5、フィルタの重なり、T/1.7)は Kovesi の公開コード(MIT)の規約。FSIM 作者の 原実装 は「教育・研究目的のみ」なので移植して
    いない —— 論文の式から書き、定数が論文 §IV-A と同じであることを確かめた。
  * GMSD —— Xue, Zhang, Mou, Bovik, IEEE TIP 23(2) 684–695, 2014, DOI 10.1109/TIP.2013.2293423(式 1 Prewitt /3、式 3 GMS、c = 170、2×2 平均 + 2 間引き、
    式 5 標準偏差)。
  * VIF(画素領域版)—— Sheikh & Bovik, IEEE TIP 15(2) 430–444, 2006, DOI 10.1109/TIP.2005.859378 §V の scalar GSM。窓 N = 2^(4−s+1)+1・σ = N/5・
    σ_n² = 2 は公開 vifp_mscale の規約。TID2013 の公表値 VIFP 0.6084(論文 Table 4)はこの画素領域版 —— steerable 版(VIF 0.6770)は配布物に値ファイルが
    無く、ここでは未実装。

**入力の規約(実測で特定、どのページにも書かれていない)**:

===========  ===================================================================  ============================================
作者値         入力                                                                 iqatid からの呼び方
===========  ===================================================================  ============================================
FSIM.txt     **Y′ limited(BT.601、16–235 の整数)の灰色画像**(:func:`iqatid.luma_limited_u8`)  ``tid2013_evaluate(root, fsim, luma="limited_u8")``
FSIMc.txt    色 BMP → YIQ(full range、0.299/0.587/0.114、丸めない)                        ``tid2013_evaluate(root, fsimc, luma="rgb")``
VIFP.txt     Y′ limited の灰色画像                                                   ``tid2013_evaluate(root, vifp, luma="limited_u8")``
(GMSD)       作者値ファイル無し。作者の慣例 = 色 → full-range Y                            ``tid2013_evaluate(root, gmsd, luma="rgb")``
===========  ===================================================================  ============================================

つまり **FSIM.txt は FSIMc 計算の中の FSIM 成分ではない**(色画像の full-range Y で FSIM を測ると FSIM.txt と最大 0.0318 ずれる)。
作者は FSIM を PSNR / SSIM と同じ輝度画像で、FSIMc を色画像で、別々に計算している。

全指標は 8 bit の尺度(0–255)で定義されている(T1 = 0.85・T2 = 160・c = 170・σ_n² = 2 がその尺度)。``data_range`` を渡すと内部で 255/data_range 倍する
([0, 1] の float なら ``data_range=1.0``)。黙って推測はしない(既定 255 は TID2013 と 8 bit 画像の規約)。

踏んだ罠(試作で発覚、全部ここに固定): (1) scipy の ``convolve2d(..., 'same')`` は**偶数核で原実装と半画素ずれる**(2×2 平均が [0, 0.25, 0.75] vs
[3, 4, 5])→ :func:`_conv2_same_ref`。(2) ダウンサンプル係数 F = round(min(H, W)/256) は原実装の round(半分は 0 から遠い側、384/256 = 1.5 → 2)。
(3) PC の ε = 1e-4 は単位ベクトル化だけに入れる —— 分母に足すと利得不変が 3e-5 崩れる。(4) GMSD は小さいほど良い(MOS との順位相関は負、公表表は |ρ|)。
正直に: 4 桁一致は作者と同じ規約を踏んだからで、指標の性能の話ではない(TID2013 全体 SROCC: FSIMc 0.851、FSIM 0.801、GMSD 0.804、VIFP 0.608)。
GMSD の TID2013 値は作者の一次資料が無く、二次資料(Nafchi ほか 2016, arXiv:1608.07433v4 Table I)の 0.8044 / 0.6339 に ±0.005 で合わせた —— 等級が 1 段低い。
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np
from scipy.signal import convolve2d, fftconvolve

__all__ = [
    "fsim", "fsimc", "fsim_pair", "gmsd", "gmsd_map", "vifp", "phase_congruency_pc",
    "FSIM_T1", "FSIM_T2", "FSIM_T3", "FSIM_T4", "FSIM_LAMBDA", "GMSD_C",
    "TID2013_PAPER_SROCC", "TID2013_PAPER_KROCC", "TID2013_SUBSET_ORDER", "GMSD_TID2013_SECONDARY",
]

FSIM_T1, FSIM_T2, FSIM_T3, FSIM_T4, FSIM_LAMBDA = 0.85, 160.0, 200.0, 200.0, 0.03
GMSD_C = 170.0
_SCHARR_DX = np.array([[3.0, 0.0, -3.0], [10.0, 0.0, -10.0], [3.0, 0.0, -3.0]]) / 16.0
_PREWITT_DX = np.array([[1.0, 0.0, -1.0]] * 3) / 3.0

#: TID2013 論文(Ponomarenko ほか, Signal Processing: Image Communication 30, 57–77, 2015)Table 4 / 5 の 4 桁。
#: 列 = Noise, Actual, Simple, Exotic, New, Color, Full(readme TABLE II = :data:`iqatid.TID2013_SUBSETS`)。readme の 3 桁表は Full 列の丸め。
#: **この表は作者の 4 桁丸めの txt から計算されている**(作者ファイル + mos.txt で 7 列すべて 4 桁一致、2026-10-04)—— 丸めない自前の値では
#: 歪み 18(彩度変化)の同一画像の組が同順位にならず New / Color が 4 桁目で動く(vifp で 0.007)。同じ丸めを踏めば 4 桁一致する。
TID2013_SUBSET_ORDER = ("Noise", "Actual", "Simple", "Exotic", "New", "Color", "Full")
TID2013_PAPER_SROCC: Dict[str, Tuple[float, ...]] = {
    "psnr": (0.8217, 0.8246, 0.9134, 0.5968, 0.6190, 0.5387, 0.6395),
    "ssim": (0.7574, 0.7877, 0.8371, 0.6320, 0.5801, 0.5057, 0.6370),
    "vifp": (0.7835, 0.8151, 0.8975, 0.5574, 0.5921, 0.5094, 0.6084),
    "vif": (0.8420, 0.8589, 0.9321, 0.6282, 0.5930, 0.5210, 0.6770),       # steerable 版(未実装、比較用)
    "fsim": (0.8969, 0.9108, 0.9485, 0.8436, 0.6494, 0.5650, 0.8007),
    "fsimc": (0.9022, 0.9149, 0.9472, 0.8407, 0.7878, 0.7752, 0.8510),
}
TID2013_PAPER_KROCC: Dict[str, Tuple[float, ...]] = {
    "psnr": (0.6236, 0.6242, 0.7452, 0.4254, 0.4728, 0.4156, 0.4700),
    "ssim": (0.5515, 0.5768, 0.6286, 0.4548, 0.4226, 0.3823, 0.4636),
    "vifp": (0.5873, 0.6217, 0.7143, 0.4066, 0.4512, 0.3930, 0.4567),
    "vif": (0.6590, 0.6729, 0.7694, 0.4634, 0.4474, 0.3998, 0.5148),
    "fsim": (0.7160, 0.7371, 0.7952, 0.6555, 0.5236, 0.4524, 0.6300),
    "fsimc": (0.7231, 0.7427, 0.7929, 0.6519, 0.6120, 0.5925, 0.6669),
}
#: GMSD の TID2013 値は配布物(2013)にも GMSD 論文(LIVE / CSIQ / TID2008)にも無い。二次資料 = Nafchi, Shahkolaei, Hedjam, Cheriet,
#: "Mean Deviation Similarity Index", arXiv:1608.07433v4(IEEE Access 4, 2016)Table I: SRC 0.8044 / KRC 0.6339(|ρ|、GMSD は lower is better)。
#: 同表の FSIMc 0.8510 / 0.6665・VIF 0.6769 / 0.5147 が TID2013 論文と ≤ 0.0004 で合うので、同じ MOS・同じ定義の表と判断。門は ±0.005。
GMSD_TID2013_SECONDARY = (0.8044, 0.6339, "Nafchi+ 2016 arXiv:1608.07433v4 Table I")


# ----------------------------------------------------------------------------------------------------------------------
# 内部: 原実装 の規約を名前にして固定する
def _ref_round(x: float) -> int:
    """原実装(数値環境の round)の丸め = 半分は 0 から遠い側。numpy の半偶数とは 1.5 で同じ(2)だが 2.5 で違う(3 vs 2)。"""
    return int(math.floor(abs(x) + 0.5)) * (1 if x >= 0 else -1)


def _conv2_same_ref(a: np.ndarray, k: np.ndarray) -> np.ndarray:
    """原実装の ``conv2(a, k, 'same')``: ゼロ詰めの full 畳み込みから、行 ``ceil((kh−1)/2)`` 始まりで a と同じ大きさを取る。
    scipy の 'same' は偶数核で半画素ずれる(2×2 平均が別の画素を平均する)ので、ここで明示する。"""
    full = convolve2d(a, k, mode="full", boundary="fill", fillvalue=0.0)
    kh, kw = k.shape
    r0 = int(math.ceil((kh - 1) / 2.0))
    c0 = int(math.ceil((kw - 1) / 2.0))
    return full[r0:r0 + a.shape[0], c0:c0 + a.shape[1]]


def _average_downsample(a: np.ndarray, f: int) -> np.ndarray:
    """F×F 平均(原実装の ``fspecial('average', F)``)を 'same' で畳み ``[::F, ::F]`` で間引く。F = 2 ならブロック平均に等しい。F ≤ 1 は恒等。"""
    if f <= 1:
        return a
    return _conv2_same_ref(a, np.full((f, f), 1.0 / (f * f)))[::f, ::f]


def _rgb_to_yiq(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """FSIM 論文 式 15–17: Y = 0.299R+0.587G+0.114B、I = 0.596R−0.274G−0.322B、Q = 0.211R−0.523G+0.312B(full range、丸めない)。"""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return (0.299 * r + 0.587 * g + 0.114 * b, 0.596 * r - 0.274 * g - 0.322 * b, 0.211 * r - 0.523 * g + 0.312 * b)


def _prep(img, name: str, data_range: float) -> np.ndarray:
    """入力を float64 の 0–255 尺度に(2-D か (H, W, 3))。**Raises** ``ValueError``: 形・非有限・data_range ≤ 0。"""
    a = np.asarray(img)
    if a.ndim == 3 and a.shape[2] == 3:
        pass
    elif a.ndim != 2:
        raise ValueError("%s: expected an image (H, W) or (H, W, 3), got shape %r" % (name, a.shape))
    if a.shape[0] < 2 or a.shape[1] < 2:
        raise ValueError("%s: image must be at least 2x2, got %r" % (name, a.shape))
    if not (data_range > 0.0 and math.isfinite(data_range)):
        raise ValueError("%s: data_range must be a positive finite number, got %r" % (name, data_range))
    x = a.astype(np.float64)
    if not np.all(np.isfinite(x)):
        raise ValueError("%s: image holds non-finite values" % name)
    return x if data_range == 255.0 else x * (255.0 / data_range)


def _pair(ref, dist, name: str, data_range: float) -> Tuple[np.ndarray, np.ndarray]:
    a, b = _prep(ref, name, data_range), _prep(dist, name, data_range)
    if a.shape != b.shape:
        raise ValueError("%s: reference and distorted images must have the same shape, got %r and %r" % (name, a.shape, b.shape))
    return a, b


def _gray(x: np.ndarray) -> np.ndarray:
    return x if x.ndim == 2 else _rgb_to_yiq(x)[0]


def _kovesi_grid(rows: int, cols: int):
    """Kovesi の周波数格子: 偶数 n は [−n/2, n/2−1]/n、奇数 n は [−(n−1)/2, (n−1)/2]/(n−1)、ifftshift 済み、θ = atan2(−y, x)。
    半径の [0,0] は log の発散を避けて 1 に置く(低域フィルタ用には 0 のまま別に返す)。"""
    def rng(n):
        if n % 2:
            return np.arange(-(n - 1) / 2.0, (n - 1) / 2.0 + 1.0) / float(n - 1)
        return np.arange(-n / 2.0, n / 2.0) / float(n)
    x, y = np.meshgrid(rng(cols), rng(rows))
    radius = np.fft.ifftshift(np.sqrt(x * x + y * y))
    theta = np.fft.ifftshift(np.arctan2(-y, x))
    radius_lp = radius.copy()
    radius[0, 0] = 1.0
    return radius, theta, radius_lp


def _log_gabor_bank(rows: int, cols: int, nscale: int, norient: int, min_wavelength: float, mult: float, sigma_onf: float,
                    dtheta_on_sigma: float, lp_cutoff: float = 0.45, lp_order: int = 15):
    """半径成分 G_s(r) = exp(−(ln(r/f_s))²/(2 (ln σ_r)²))(f_s = 1/(λ_min mult^s))× Butterworth 低域 1/(1+(r/0.45)^30)、DC = 0。
    角度成分 S_o(θ) = exp(−Δθ²/(2 σ_θ²))、σ_θ = π/norient/dθ_on_σ、Δθ = |atan2(sin(θ−θ_o), cos(θ−θ_o))|(180° 回しても同じにならないので
    フィルタは非エルミート —— ifft の実部が偶、虚部が奇の応答になる)。"""
    radius, theta, r_lp = _kovesi_grid(rows, cols)
    lp = 1.0 / (1.0 + (r_lp / lp_cutoff) ** (2 * lp_order))
    radial = []
    for s in range(nscale):
        fo = 1.0 / (min_wavelength * mult ** s)
        g = np.exp(-(np.log(radius / fo) ** 2) / (2.0 * math.log(sigma_onf) ** 2)) * lp
        g[0, 0] = 0.0
        radial.append(g)
    sin_t, cos_t = np.sin(theta), np.cos(theta)
    theta_sigma = math.pi / norient / dtheta_on_sigma
    spread = []
    for o in range(norient):
        angl = o * math.pi / norient
        ds = sin_t * math.cos(angl) - cos_t * math.sin(angl)
        dc = cos_t * math.cos(angl) + sin_t * math.sin(angl)
        spread.append(np.exp(-(np.abs(np.arctan2(ds, dc)) ** 2) / (2.0 * theta_sigma ** 2)))
    return radial, spread


def _fspecial_gaussian(n: int, sigma: float) -> np.ndarray:
    """原実装の ``fspecial('gaussian', n, sigma)`` と同じ窓(総和 1、eps·max 未満は 0)。"""
    r = np.arange(n, dtype=np.float64) - (n - 1) / 2.0
    xx, yy = np.meshgrid(r, r)
    h = np.exp(-(xx * xx + yy * yy) / (2.0 * sigma * sigma))
    h[h < np.finfo(float).eps * h.max()] = 0.0
    return h / h.sum()


# ----------------------------------------------------------------------------------------------------------------------
# 1. 位相一致
def phase_congruency_pc(img, data_range: float = 255.0, nscale: int = 4, norient: int = 4, min_wavelength: float = 6.0, mult: float = 2.0,
                        sigma_onf: float = 0.55, dtheta_on_sigma: float = 1.2, k: float = 2.0, epsilon: float = 1e-4) -> np.ndarray:
    """位相一致 PC(x) = Σ_o E_o(x) / Σ_o Σ_s A_{s,o}(x) ∈ [0, 1] (Kovesi 1999、FSIM 論文 式 4 の規約: log-Gabor 4 スケール × 4 向き)。

    既存の ``phase_congruency``(backends_transform2、Riesz/モノジェニック版、方向を持たない、ノブ a/b)とは**別物**なので接尾 ``_pc``。
    E_o = Σ_s [e ē + o ō − |e ō − o ē|] (ē, ō = その向きの総和ベクトルの単位方向、ε = 1e-4 はこの単位ベクトル化だけに入れる)から
    Kovesi の雑音しきい値 T を引いて 0 で切る: 最小スケールの |EO|² の中央値 → Rayleigh の平均 −median/ln 0.5 → 雑音電力 → フィルタの重なりを含む
    雑音エネルギーの平均 + k σ、最後に 1.7 で割る(Kovesi の経験則)。周波数広がりの sigmoid 重みは掛けない(FSIM の式 4 に無い)。
    利得不変: 入力を定数倍しても PC は変わらない —— ただし ε の分だけ(ε = 1e-4 で最大 3e-5、ε に厳密比例)。入力 (H, W)((H, W, 3) は Y)。
    既定値は FSIM 論文 §IV-A(λ_min = 6、mult = 2、σ_r = 0.55、σ_θ = π/4/1.2、k = 2)。
    **Raises** ``ValueError``: 2×2 未満、非有限、data_range ≤ 0。"""
    x = _gray(_prep(img, "phase_congruency_pc", data_range))
    rows, cols = x.shape
    if nscale < 1 or norient < 1:
        raise ValueError("phase_congruency_pc: nscale and norient must be >= 1, got %d / %d" % (nscale, norient))
    radial, spread = _log_gabor_bank(rows, cols, nscale, norient, min_wavelength, mult, sigma_onf, dtheta_on_sigma)
    F = np.fft.fft2(x)
    energy_all = np.zeros((rows, cols))
    an_all = np.zeros((rows, cols))
    scale_norm = math.sqrt(rows * cols)
    for o in range(norient):
        sum_e = np.zeros((rows, cols))
        sum_o = np.zeros((rows, cols))
        sum_an = np.zeros((rows, cols))
        eo, ifft_filt = [], []
        em_n = 1.0
        for s in range(nscale):
            filt = radial[s] * spread[o]
            ifft_filt.append(np.fft.ifft2(filt).real * scale_norm)
            resp = np.fft.ifft2(F * filt)
            eo.append(resp)
            sum_an += np.abs(resp)
            sum_e += resp.real
            sum_o += resp.imag
            if s == 0:
                em_n = float((filt * filt).sum())
        x_energy = np.sqrt(sum_e * sum_e + sum_o * sum_o) + epsilon
        mean_e, mean_o = sum_e / x_energy, sum_o / x_energy
        energy = np.zeros((rows, cols))
        for s in range(nscale):
            e, od = eo[s].real, eo[s].imag
            energy += e * mean_e + od * mean_o - np.abs(e * mean_o - od * mean_e)
        median_e2n = float(np.median(np.abs(eo[0]) ** 2))
        noise_power = (-median_e2n / math.log(0.5)) / em_n
        est_sum_an2 = float(sum((f * f).sum() for f in ifft_filt))
        est_sum_aiaj = 0.0
        for si in range(nscale - 1):
            for sj in range(si + 1, nscale):
                est_sum_aiaj += float((ifft_filt[si] * ifft_filt[sj]).sum())
        tau = math.sqrt((2.0 * noise_power * est_sum_an2 + 4.0 * noise_power * est_sum_aiaj) / 2.0)
        T = (tau * math.sqrt(math.pi / 2.0) + k * math.sqrt((2.0 - math.pi / 2.0) * tau * tau)) / 1.7
        energy_all += np.maximum(energy - T, 0.0)
        an_all += sum_an
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(an_all > 0.0, energy_all / an_all, 0.0)     # 振幅が厳密に 0(定数画像)は 0、nan にしない


# ----------------------------------------------------------------------------------------------------------------------
# 2. FSIM / FSIMc
def _scharr_mag(y: np.ndarray) -> np.ndarray:
    gx = _conv2_same_ref(y, _SCHARR_DX)
    gy = _conv2_same_ref(y, _SCHARR_DX.T)
    return np.sqrt(gx * gx + gy * gy)


def fsim_pair(ref, dist, data_range: float = 255.0, downsample: bool = True) -> dict:
    """FSIM と FSIMc を一度に(位相一致は 1 枚 1 回しか計算しない —— 評価器や PoC はこちらを呼ぶ)。

    手順(論文 §III): (1) F = max(1, round(min(H, W)/256)) で F×F 平均 + 間引き(TID2013 の 384×512 は F = 2 → 192×256)、(2) Y の位相一致 PC と
    Scharr([3 0 −3; 10 0 −10; 3 0 −3]/16)勾配の大きさ G、(3) S_PC = (2 PC1 PC2 + T1)/(PC1² + PC2² + T1)、S_G = (2 G1 G2 + T2)/(G1² + G2² + T2)、
    (4) FSIM = Σ S_G S_PC PC_m / Σ PC_m(PC_m = max(PC1, PC2))、(5) FSIMc は彩度 I / Q の S_I S_Q(T3 = T4 = 200)の λ = 0.03 乗の実部を掛ける。
    入力は同じ形の (H, W) か (H, W, 3)(0–255; ``data_range`` で尺度を宣言)。**(H, W) のときは FSIMc = FSIM**(彩度の項が無い)。
    TID2013 の作者値: FSIM.txt は **Y′ limited の灰色画像**、FSIMc.txt は色画像(モジュール docstring の表)—— 色画像 1 枚から両方を出すと FSIM の方は
    FSIM.txt と合わない(max 0.0318)。返り値 ``{"fsim", "fsimc", "f"}``(f = 間引き係数)。恒等で 1。
    **Raises** ``ValueError``: 形が違う、2×2 未満、位相一致が全画素 0(平坦画像: FSIM は 0/0 で定義されない)。"""
    a, b = _pair(ref, dist, "fsim_pair", data_range)
    color = a.ndim == 3
    if color:
        y1, i1, q1 = _rgb_to_yiq(a)
        y2, i2, q2 = _rgb_to_yiq(b)
    else:
        y1, y2 = a, b
    rows, cols = y1.shape
    f = max(1, _ref_round(min(rows, cols) / 256.0)) if downsample else 1
    y1, y2 = _average_downsample(y1, f), _average_downsample(y2, f)
    pc1, pc2 = phase_congruency_pc(y1), phase_congruency_pc(y2)
    g1, g2 = _scharr_mag(y1), _scharr_mag(y2)
    s_pc = (2.0 * pc1 * pc2 + FSIM_T1) / (pc1 * pc1 + pc2 * pc2 + FSIM_T1)
    s_g = (2.0 * g1 * g2 + FSIM_T2) / (g1 * g1 + g2 * g2 + FSIM_T2)
    pcm = np.maximum(pc1, pc2)
    den = float(pcm.sum())
    if den <= 0.0:
        raise ValueError("fsim_pair: phase congruency is zero everywhere (flat images); FSIM is undefined (0/0)")
    out = {"fsim": float((s_g * s_pc * pcm).sum() / den), "f": int(f)}
    if color:
        i1, i2 = _average_downsample(i1, f), _average_downsample(i2, f)
        q1, q2 = _average_downsample(q1, f), _average_downsample(q2, f)
        s_i = (2.0 * i1 * i2 + FSIM_T3) / (i1 * i1 + i2 * i2 + FSIM_T3)
        s_q = (2.0 * q1 * q2 + FSIM_T4) / (q1 * q1 + q2 * q2 + FSIM_T4)
        chroma = np.real(np.power((s_i * s_q).astype(np.complex128), FSIM_LAMBDA))     # 負になりうるので複素べきの実部(論文 式 13)
        out["fsimc"] = float((s_g * s_pc * chroma * pcm).sum() / den)
    else:
        out["fsimc"] = out["fsim"]
    return out


def fsim(ref, dist, data_range: float = 255.0) -> float:
    """FSIM(輝度のみ、1 = 同一、**higher is better**)。TID2013 の FSIM.txt と 4 桁一致するのは **Y′ limited の灰色画像**を渡したとき
    (``iqatid.tid2013_evaluate(root, fsim, luma="limited_u8")``、3,000 組 max |差| 5.0e-5)。詳細 :func:`fsim_pair`。"""
    return fsim_pair(ref, dist, data_range=data_range)["fsim"]


def fsimc(ref, dist, data_range: float = 255.0) -> float:
    """FSIMc(彩度 I / Q を含む、1 = 同一、**higher is better**)。TID2013 の FSIMc.txt と 4 桁一致するのは色画像(RGB → YIQ full range)を渡したとき
    (``iqatid.tid2013_evaluate(root, fsimc, luma="rgb")``、3,000 組 max |差| 5.0e-5)。(H, W) 入力なら FSIM と同じ値。詳細 :func:`fsim_pair`。"""
    return fsim_pair(ref, dist, data_range=data_range)["fsimc"]


# ----------------------------------------------------------------------------------------------------------------------
# 3. GMSD
def gmsd_map(ref, dist, data_range: float = 255.0, c: float = GMSD_C, down_step: int = 2) -> np.ndarray:
    """GMS 地図 (2 m_r m_d + c)/(m_r² + m_d² + c) ∈ (0, 1] (論文 式 3)。m = Prewitt([1 0 −1]×3 /3)勾配の大きさ、前処理は 2×2 平均 + 2 間引き
    (:func:`_average_downsample`、原実装の 'same' 規約)。入力 (H, W) か (H, W, 3)(3-ch は Y = 0.299R+0.587G+0.114B、作者の慣例)。
    **Raises** ``ValueError``: 形が違う、c ≤ 0、down_step < 1。"""
    a, b = _pair(ref, dist, "gmsd_map", data_range)
    if not c > 0.0:
        raise ValueError("gmsd_map: c must be positive, got %r" % c)
    if down_step < 1:
        raise ValueError("gmsd_map: down_step must be >= 1, got %r" % down_step)
    y1, y2 = _average_downsample(_gray(a), down_step), _average_downsample(_gray(b), down_step)
    m1 = np.sqrt(_conv2_same_ref(y1, _PREWITT_DX) ** 2 + _conv2_same_ref(y1, _PREWITT_DX.T) ** 2)
    m2 = np.sqrt(_conv2_same_ref(y2, _PREWITT_DX) ** 2 + _conv2_same_ref(y2, _PREWITT_DX.T) ** 2)
    return (2.0 * m1 * m2 + c) / (m1 * m1 + m2 * m2 + c)


def gmsd(ref, dist, data_range: float = 255.0, c: float = GMSD_C) -> float:
    """GMSD = GMS 地図の標準偏差(N−1、原実装の ``std2``、論文 式 5)。0 = 同一、大きいほど劣化(**lower is better** —— MOS との順位相関は負で、
    公表表は |ρ| を載せる: TID2013 全体 |SROCC| 0.8038、二次資料 0.8044)。入力 (H, W) か (H, W, 3)(3-ch は Y)。
    ``iqatid.tid2013_evaluate(root, gmsd, luma="rgb")``。**Raises** ``ValueError``: :func:`gmsd_map` と同じ、地図が 1 画素(分散が定義されない)。"""
    q = gmsd_map(ref, dist, data_range=data_range, c=c)
    if q.size < 2:
        raise ValueError("gmsd: GMS map has %d pixel(s); the standard deviation is undefined" % q.size)
    return float(np.std(q, ddof=1))


# ----------------------------------------------------------------------------------------------------------------------
# 4. VIF(画素領域版)
def vifp(ref, dist, data_range: float = 255.0, sigma_nsq: float = 2.0, nscales: int = 4) -> float:
    """VIF の画素領域版(Sheikh & Bovik 2006 §V の scalar GSM、公開 vifp_mscale の規約)。1 = 同一、**higher is better**。

    各スケール s = 1..4: 窓 N = 2^(4−s+1)+1、ガウス σ = N/5(17/3.4、9/1.8、5/1.0、3/0.6)。s > 1 では窓で平滑して 2 間引き。局所統計(μ、σ²、σ12)は
    'valid' 相関、g = σ12/(σ1²+1e-10)、σ_v² = σ2² − g σ12、σ1² < 1e-10・σ2² < 1e-10・g < 0 の画素は規約どおり潰す、σ_v² ≤ 1e-10 → 1e-10。
    VIF = Σ log10(1 + g² σ1²/(σ_v² + σ_n²)) / Σ log10(1 + σ1²/σ_n²)。**非対称**(参照の情報量で割る: vif(a, b) ≠ vif(b, a))、コントラスト強調で
    **1 を超える**(TID2013 の作者値も最大 1.1379 = 歪み 17)—— 忠実度でなく情報量の比。入力 (H, W) か (H, W, 3)(3-ch は Y)。
    TID2013 の VIFP.txt(論文の「VIFP」、steerable 版の「VIF」とは別行)と 4 桁一致するのは **Y′ limited の灰色画像**
    (``iqatid.tid2013_evaluate(root, vifp, luma="limited_u8")``、3,000 組 max |差| 6.8e-5)。
    **Raises** ``ValueError``: 形が違う、最小スケールで窓より小さい、参照が平坦(分母 0)、sigma_nsq ≤ 0。"""
    r, d = _pair(ref, dist, "vifp", data_range)
    if not sigma_nsq > 0.0:
        raise ValueError("vifp: sigma_nsq must be positive, got %r" % sigma_nsq)
    if nscales < 1:
        raise ValueError("vifp: nscales must be >= 1, got %r" % nscales)
    r, d = _gray(r), _gray(d)
    num = den = 0.0
    for scale in range(1, nscales + 1):
        n = 2 ** (nscales - scale + 1) + 1
        win = _fspecial_gaussian(n, n / 5.0)
        if scale > 1:
            r = fftconvolve(r, win, mode="valid")[::2, ::2]
            d = fftconvolve(d, win, mode="valid")[::2, ::2]
        if r.shape[0] < n or r.shape[1] < n:
            raise ValueError("vifp: image too small at scale %d (%r < window %d); need at least %d px on each side"
                             % (scale, r.shape, n, 2 ** (nscales - 1) * (n + 1)))
        mu1, mu2 = fftconvolve(r, win, mode="valid"), fftconvolve(d, win, mode="valid")
        s1 = np.maximum(fftconvolve(r * r, win, mode="valid") - mu1 * mu1, 0.0)
        s2 = np.maximum(fftconvolve(d * d, win, mode="valid") - mu2 * mu2, 0.0)
        s12 = fftconvolve(r * d, win, mode="valid") - mu1 * mu2
        g = s12 / (s1 + 1e-10)
        sv = s2 - g * s12
        low1 = s1 < 1e-10
        g[low1] = 0.0
        sv[low1] = s2[low1]
        s1[low1] = 0.0
        low2 = s2 < 1e-10
        g[low2] = 0.0
        sv[low2] = 0.0
        neg = g < 0.0
        sv[neg] = s2[neg]
        g[neg] = 0.0
        sv[sv <= 1e-10] = 1e-10
        num += float(np.log10(1.0 + g * g * s1 / (sv + sigma_nsq)).sum())
        den += float(np.log10(1.0 + s1 / sigma_nsq).sum())
    if den == 0.0:
        raise ValueError("vifp: the reference carries no information (flat image); VIF is undefined (0/0)")
    return num / den
