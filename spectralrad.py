# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""spectralrad — 光源・フィルタ・センサの分光曲線と、その積(像の明るさの波長積分)。

動機(2026-10-14、材料ライブラリの系列の第 3 段): 材料の n,k・透過率・反射率は ``materials`` が
pairs(λ [nm], 値)で返すようになったが、**光源の分光分布とセンサの量子効率**が op として無く
(Planck は PoC の中の関数だけ)、「この光源で、このウェハ越しに、このセンサで何電子になるか」を
組めなかった。ここはその残り半分で、どの曲線も ``materials`` と同じ pairs で返す ——
像 = 光源 × 光学系 × 対象 × センサ を ``spectral_product`` で掛けて ``spectral_integral`` で積む。

内容(9 op):
  光源      `blackbody_spectrum`(Planck、SI 2019 の定数)/ `cie_illuminant_a`(CIE 15 の式そのもの)
            `led_spectrum`(Ohno 2005 のモデルか Gauss、FWHM は指定どおりになるよう解いて合わせる)
  フィルタ  `bandpass_spectrum`(超 Gauss の帯域通過、遮断域の床つき)
  センサ    `silicon_photodiode_qe`(Si の n,k(Green 2008)から QE = (1 − R)·[e^{−α d₀} − e^{−α(d₀+W)}])
  演算      `energy_to_photons`(W → 光子数、λ/hc を掛ける)/ `spectral_product` / `spectral_integral`
            `spectral_stats`(ピーク・重心・FWHM・積分)

★**エネルギーと光子数を混ぜない**: 量子効率は「光子 1 個あたりの電子数」なので、光源の分光放射
(W/nm)に QE を掛ける前に `energy_to_photons` を通す。通さないと長波長ほど λ に比例して過小評価になる
(1100 nm と 550 nm で 2 倍)—— PoC ``poc_nir_silicon_transmission`` がこの差を数える。

来歴(公開文献のみ): Planck の式と定数(CODATA / SI 2019 の定義値)、CIE 15:2004 の標準イルミナント A
の式(T = 2848 K、c₂ = 1.435e-2 m·K、560 nm で 100)、Ohno, Opt. Eng. 44, 111302 (2005)(LED の
スペクトルモデル)、Si の n,k は ``materials``(Green, Sol. Energy Mater. Sol. Cells 92, 1305 (2008))。

規約: 波長は nm、温度は K、曲線は (n, 2) の pairs(λ 昇順)。区間外は外挿しない(ValueError)。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "PLANCK_H", "LIGHT_C", "BOLTZMANN_K",
    "blackbody_spectrum", "cie_illuminant_a", "led_spectrum", "bandpass_spectrum",
    "silicon_photodiode_qe", "energy_to_photons", "spectral_product", "spectral_integral",
    "spectral_stats",
]

#: SI 2019 の定義値(誤差なし)。
PLANCK_H = 6.62607015e-34      # J s
LIGHT_C = 299792458.0          # m/s
BOLTZMANN_K = 1.380649e-23     # J/K


# --------------------------------------------------------------------------- #
# 共通                                                                          #
# --------------------------------------------------------------------------- #
def _grid_nm(wl_min_nm, wl_max_nm, n_points, op):
    lo, hi, n = float(wl_min_nm), float(wl_max_nm), int(n_points)
    if not (math.isfinite(lo) and math.isfinite(hi)) or lo <= 0.0 or hi <= lo:
        raise ValueError("%s: need 0 < wl_min_nm < wl_max_nm, got %r, %r" % (op, wl_min_nm, wl_max_nm))
    if n < 2:
        raise ValueError("%s: n_points must be >= 2, got %r" % (op, n_points))
    return np.linspace(lo, hi, n)


def _pairs(x, y):
    return np.stack([np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)], axis=1)


def _curve(c, name, op):
    """pairs(λ nm, 値)を検証して返す(λ は有限・正・狭義単調増加、値は有限)。"""
    a = np.asarray(c, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 2:
        raise ValueError("%s: %s must be pairs of (wavelength nm, value), shape (n, 2); got %s"
                         % (op, name, a.shape))
    if a.shape[0] < 2:
        raise ValueError("%s: %s needs at least 2 wavelengths, got %d" % (op, name, a.shape[0]))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: %s contains non-finite values" % (op, name))
    if np.any(a[:, 0] <= 0.0) or np.any(np.diff(a[:, 0]) <= 0.0):
        raise ValueError("%s: %s wavelengths must be > 0 and strictly increasing" % (op, name))
    return a


def _positive(v, name, op):
    x = float(v)
    if not (math.isfinite(x) and x > 0.0):
        raise ValueError("%s: %s must be finite and > 0, got %r" % (op, name, v))
    return x


# --------------------------------------------------------------------------- #
# 1. 光源                                                                       #
# --------------------------------------------------------------------------- #
def blackbody_spectrum(temperature_k=2856.0, wl_min_nm=300.0, wl_max_nm=2500.0, n_points=221,
                       normalize_nm=None):
    """黒体の分光放射輝度 L(λ, T)、単位 W m⁻² sr⁻¹ nm⁻¹(Planck の式、SI 2019 の定数)。

    L = 2hc²/λ⁵ · 1/(exp(hc/λkT) − 1)。ハロゲン電球(≈ 2800〜3200 K)・赤外の熱源・太陽(≈ 5772 K)の
    近似に使う。*normalize_nm* を与えると、その波長で 1 になるよう割った相対分布を返す。

    返り値: pairs(λ nm, L)。
    """
    op = "blackbody_spectrum"
    T = _positive(temperature_k, "temperature_k", op)
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    lam = wl * 1e-9
    x = PLANCK_H * LIGHT_C / (lam * BOLTZMANN_K * T)
    with np.errstate(over="ignore"):
        L = 2.0 * PLANCK_H * LIGHT_C ** 2 / lam ** 5 / np.expm1(x) * 1e-9      # per nm
    L = np.where(np.isfinite(L), L, 0.0)
    if normalize_nm is not None:
        ln = float(normalize_nm)
        if not (math.isfinite(ln) and ln > 0.0):
            raise ValueError("%s: normalize_nm must be a positive wavelength, got %r" % (op, normalize_nm))
        xn = PLANCK_H * LIGHT_C / (ln * 1e-9 * BOLTZMANN_K * T)
        Ln = 2.0 * PLANCK_H * LIGHT_C ** 2 / (ln * 1e-9) ** 5 / math.expm1(xn) * 1e-9
        if not (Ln > 0.0 and math.isfinite(Ln)):
            raise ValueError("%s: the spectrum is zero or non-finite at normalize_nm=%g" % (op, ln))
        L = L / Ln
    return _pairs(wl, L)


def cie_illuminant_a(wl_min_nm=300.0, wl_max_nm=830.0, n_points=107):
    """CIE 標準イルミナント A の相対分光分布(CIE 15:2004 の定義式、560 nm で 100)。

    S_A(λ) = 100 (560/λ)⁵ · (exp(c₂/(2848·560e-9)) − 1)/(exp(c₂/(2848·λ)) − 1)、c₂ = 1.435e-2 m·K。
    タングステン電球の基準光源。定義が式なので、表の値はこの式の値そのもの(外部の真値になる)。

    返り値: pairs(λ nm, S_A)。
    """
    op = "cie_illuminant_a"
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    c2, T = 1.435e-2, 2848.0
    lam = wl * 1e-9
    S = 100.0 * (560e-9 / lam) ** 5 * math.expm1(c2 / (T * 560e-9)) / np.expm1(c2 / (T * lam))
    return _pairs(wl, S)


def _ohno_half_width():
    """Ohno のモデル s = (g + 2g⁵)/3、g = exp(−x²) が 1/2 になる x(二分法、閉じた区間で 60 回)。"""
    lo, hi = 0.0, 3.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        g = math.exp(-mid * mid)
        if (g + 2.0 * g ** 5) / 3.0 > 0.5:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def led_spectrum(peak_nm=1050.0, fwhm_nm=50.0, wl_min_nm=800.0, wl_max_nm=1300.0, n_points=251,
                 model="ohno"):
    """LED の相対分光分布(ピークで 1)。

    model: "ohno"(Ohno 2005: s = (g + 2g⁵)/3、g = exp(−((λ − λ₀)/Δ)²)。裾が Gauss より太く
    実測の LED に近い)/ "gaussian"。どちらも **半値全幅が fwhm_nm になるよう Δ を解いて**決める
    (Ohno の式の Δ をそのまま FWHM と読むと 15 % ほど狭くなる)。

    返り値: pairs(λ nm, 相対強度)。
    """
    op = "led_spectrum"
    p = _positive(peak_nm, "peak_nm", op)
    w = _positive(fwhm_nm, "fwhm_nm", op)
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    if model == "gaussian":
        x = (wl - p) / (w / (2.0 * math.sqrt(math.log(2.0))))
        s = np.exp(-x * x)
    elif model == "ohno":
        x = (wl - p) * (2.0 * _ohno_half_width() / w)
        g = np.exp(-x * x)
        s = (g + 2.0 * g ** 5) / 3.0
    else:
        raise ValueError("%s: model must be 'ohno' or 'gaussian', got %r" % (op, model))
    return _pairs(wl, s)


def bandpass_spectrum(center_nm=1100.0, fwhm_nm=40.0, peak_transmittance=0.9, order=4,
                      blocking=1e-4, wl_min_nm=800.0, wl_max_nm=1400.0, n_points=301):
    """帯域通過フィルタの透過率(超 Gauss)。

    T = b + (T₀ − b)·exp(−ln2 · |2(λ − λc)/FWHM|^{2·order})。order = 1 が Gauss、大きいほど肩が立つ
    (干渉フィルタは 3〜6)。*blocking* は遮断域の床(OD 4 = 1e-4)。FWHM は床を引いた山の半値全幅。

    返り値: pairs(λ nm, T)。
    """
    op = "bandpass_spectrum"
    c = _positive(center_nm, "center_nm", op)
    w = _positive(fwhm_nm, "fwhm_nm", op)
    t0 = float(peak_transmittance)
    b = float(blocking)
    q = int(order)
    if not (0.0 < t0 <= 1.0):
        raise ValueError("%s: peak_transmittance must lie in (0, 1], got %r" % (op, peak_transmittance))
    if not (0.0 <= b < t0):
        raise ValueError("%s: blocking must lie in [0, peak_transmittance), got %r" % (op, blocking))
    if q < 1 or q != order:
        raise ValueError("%s: order must be an integer >= 1, got %r" % (op, order))
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    u = np.abs(2.0 * (wl - c) / w)
    T = b + (t0 - b) * np.exp(-math.log(2.0) * u ** (2 * q))
    return _pairs(wl, T)


# --------------------------------------------------------------------------- #
# 2. センサ                                                                     #
# --------------------------------------------------------------------------- #
def silicon_photodiode_qe(collection_depth_um=3.0, dead_layer_um=0.0, front_reflectance=None,
                          wl_min_nm=300.0, wl_max_nm=1200.0, n_points=181):
    """Si フォトダイオードの外部量子効率(電子/光子)を Si の n,k から。

    QE(λ) = (1 − R(λ)) · [exp(−α d₀) − exp(−α (d₀ + W))]、α = 4πk/λ(Si の k は ``materials`` の
    Green 2008、300 K)。W = *collection_depth_um*(空乏層 + 拡散で集まる深さ。裏面照射の CMOS で
    ≈ 3 µm、NIR 強化品で 6〜10 µm、PIN フォトダイオードで 50 µm 以上)、d₀ = *dead_layer_um*
    (表面の再結合で失う層)。*front_reflectance* が None なら空気/Si の Fresnel(≈ 0.3、反射防止膜なし)、
    数を与えればその一定値(反射防止膜つきなら 0.02〜0.05)。

    集める深さが有限なので、吸収端(1.1 µm)より手前から QE が落ちる —— 厚いほど NIR に効く。

    返り値: pairs(λ nm, QE)。Green 2008 の範囲(250〜1450 nm)の外は ValueError。
    """
    op = "silicon_photodiode_qe"
    import materials as _mat
    W = _positive(collection_depth_um, "collection_depth_um", op)
    d0 = float(dead_layer_um)
    if not (math.isfinite(d0) and d0 >= 0.0):
        raise ValueError("%s: dead_layer_um must be finite and >= 0, got %r" % (op, dead_layer_um))
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    rec = _mat._record("SI", op)
    n, k, _, k_src = _mat._nk(rec, wl / 1000.0, op)
    if any(src is None for src in k_src):
        bad = float(wl[[i for i, src in enumerate(k_src) if src is None][0]])
        raise ValueError("%s: the Si table has no extinction coefficient at %.6g nm (Green 2008 covers "
                         "250-1450 nm); a QE there would be a silent 0" % (op, bad))
    if front_reflectance is None:
        R = ((n - 1.0) ** 2 + k ** 2) / ((n + 1.0) ** 2 + k ** 2)
    else:
        r = float(front_reflectance)
        if not (0.0 <= r < 1.0):
            raise ValueError("%s: front_reflectance must lie in [0, 1), got %r" % (op, front_reflectance))
        R = np.full(wl.shape, r)
    alpha_per_um = 4.0 * math.pi * k / (wl / 1000.0)
    qe = (1.0 - R) * (np.exp(-alpha_per_um * d0) - np.exp(-alpha_per_um * (d0 + W)))
    return _pairs(wl, qe)


# --------------------------------------------------------------------------- #
# 3. 曲線の演算                                                                 #
# --------------------------------------------------------------------------- #
def energy_to_photons(spectrum):
    """エネルギーの分光分布(W/nm)を光子数の分布(光子 s⁻¹ nm⁻¹)にする: λ/(hc) を掛ける。

    量子効率(電子/光子)を掛ける前に通す。相対分布でも、波長ごとの重みの比は正しくなる。
    返り値: pairs(λ nm, 光子数)。
    """
    a = _curve(spectrum, "spectrum", "energy_to_photons")
    return _pairs(a[:, 0], a[:, 1] * (a[:, 0] * 1e-9) / (PLANCK_H * LIGHT_C))


def spectral_product(a, b):
    """2 本の曲線の積を *a* の波長で(*b* は線形補間)。光源 × 透過率 × QE を 1 本ずつ掛ける。

    *b* の波長範囲が *a* を覆わなければ ValueError(外挿して 0 や端の値で埋めない ——
    範囲の足りない曲線を掛けると、黙って信号が消える)。返り値: pairs(λ nm, a·b)。
    """
    op = "spectral_product"
    A = _curve(a, "a", op)
    B = _curve(b, "b", op)
    if A[0, 0] < B[0, 0] - 1e-9 or A[-1, 0] > B[-1, 0] + 1e-9:
        raise ValueError("%s: b covers %.6g-%.6g nm but a spans %.6g-%.6g nm; resample a onto the "
                         "overlap first (the curves are not extrapolated)" % (op, B[0, 0], B[-1, 0], A[0, 0], A[-1, 0]))
    return _pairs(A[:, 0], A[:, 1] * np.interp(A[:, 0], B[:, 0], B[:, 1]))


def spectral_integral(spectrum, wl_min_nm=None, wl_max_nm=None):
    """曲線の波長積分 ∫ s(λ) dλ(台形則、λ は nm)。区間を与えればその中だけ(端は線形補間)。

    返り値: float(単位は「値 × nm」)。
    """
    op = "spectral_integral"
    a = _curve(spectrum, "spectrum", op)
    lo = a[0, 0] if wl_min_nm is None else float(wl_min_nm)
    hi = a[-1, 0] if wl_max_nm is None else float(wl_max_nm)
    if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo:
        raise ValueError("%s: need wl_min_nm < wl_max_nm, got %r, %r" % (op, wl_min_nm, wl_max_nm))
    if lo < a[0, 0] - 1e-9 or hi > a[-1, 0] + 1e-9:
        raise ValueError("%s: the interval %.6g-%.6g nm is outside the curve (%.6g-%.6g nm)"
                         % (op, lo, hi, a[0, 0], a[-1, 0]))
    inner = a[(a[:, 0] > lo) & (a[:, 0] < hi)]
    x = np.concatenate([[lo], inner[:, 0], [hi]])
    y = np.concatenate([[np.interp(lo, a[:, 0], a[:, 1])], inner[:, 1], [np.interp(hi, a[:, 0], a[:, 1])]])
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(x)))


def spectral_stats(spectrum):
    """曲線の要約: ピーク波長と値、重心波長、半値全幅(線形補間で交点を取る)、積分。

    返り値: dict(peak_nm, peak_value, centroid_nm, fwhm_nm, integral)。半値の交点が曲線の
    範囲内に無い側があれば fwhm_nm は None(端で切れた山の幅を推測しない)。
    """
    op = "spectral_stats"
    a = _curve(spectrum, "spectrum", op)
    x, y = a[:, 0], a[:, 1]
    i = int(np.argmax(y))
    peak = float(y[i])
    total = spectral_integral(a)
    if peak <= 0.0 or total <= 0.0:
        raise ValueError("%s: the curve has no positive peak" % op)
    centroid = float(np.sum(0.5 * (x[1:] * y[1:] + x[:-1] * y[:-1]) * np.diff(x)) / total)
    half = 0.5 * peak
    left = right = None
    for j in range(i, 0, -1):
        if y[j - 1] < half <= y[j]:
            left = x[j - 1] + (half - y[j - 1]) * (x[j] - x[j - 1]) / (y[j] - y[j - 1])
            break
    for j in range(i, len(x) - 1):
        if y[j + 1] < half <= y[j]:
            right = x[j] + (y[j] - half) * (x[j + 1] - x[j]) / (y[j] - y[j + 1])
            break
    fwhm = None if left is None or right is None else float(right - left)
    return {"peak_nm": float(x[i]), "peak_value": peak, "centroid_nm": centroid,
            "fwhm_nm": fwhm, "integral": total}
