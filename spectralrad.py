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
    "ingaas_photodiode_qe", "kubelka_munk_reflectance", "spectral_reflectance_from_material",
    "hyperspectral_band_weights", "hyperspectral_capture", "hyperspectral_capture_cube", "DEFAULT_BAND_CENTERS_NM",
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


# --------------------------------------------------------------------------- #
# 4. 近赤外の分光撮像(ハイパースペクトル): InGaAs・散乱層の反射・帯域ごとの電子数         #
# --------------------------------------------------------------------------- #
#: eV·nm(hc/e)。λ [nm] = HC_EV_NM / E [eV]。
HC_EV_NM = PLANCK_H * LIGHT_C / 1.602176634e-19 * 1e9


def _direct_gap_alpha(e_ev, eg_ev, a_per_um, urbach_ev):
    """直接遷移の吸収端 α(E) = A √(E − E_g)、E_g + E_u/2 より下は Urbach の指数の裾(C¹ でつなぐ)。単位 1/µm。"""
    e0 = eg_ev + 0.5 * urbach_ev
    above = a_per_um * np.sqrt(np.maximum(e_ev - eg_ev, 0.0))
    below = a_per_um * math.sqrt(0.5 * urbach_ev) * np.exp(np.minimum(e_ev - e0, 0.0) / urbach_ev)
    return np.where(e_ev >= e0, above, below)


def ingaas_photodiode_qe(cutoff_nm=1700.0, absorber_um=3.0, window_cutoff_nm=920.0, window_um=1.0,
                         front_reflectance=0.03, urbach_mev=8.0, wl_min_nm=800.0, wl_max_nm=2600.0,
                         n_points=361):
    """InGaAs フォトダイオードの外部量子効率(電子/光子)を、吸収層と窓層の直接遷移の吸収端から。

    QE(λ) = (1 − R) · exp(−α_win d_win) · [1 − exp(−α_abs W)]、α(E) = A √(E − E_g)(直接遷移、
    E_g より E_u/2 上から下は Urbach の裾 A√(E_u/2) exp((E − E_g − E_u/2)/E_u) に C¹ でつなぐ)。
    吸収層の E_g = hc/*cutoff_nm*(標準の In₀.₅₃Ga₀.₄₇As で 0.74 eV → 約 1.7 µm、拡張品は In 組成を
    上げて 1.9 / 2.2 / 2.6 µm)、A = 3.1 µm⁻¹ eV^−½(In₀.₅₃Ga₀.₄₇As の 1.55 µm で α ≈ 7×10³ /cm に
    合わせた値)。窓(InP、E_g 1.344 eV → 922 nm)は短波長を吸って下限を作る。窓を薄く(基板除去)
    すると可視まで伸びる。

    ★これは**形のモデル**で、データシートの曲線ではない: 市販の標準品の典型値(データシート: 0.9〜1.7 µm、
    1.0〜1.6 µm で 80 % 前後、1.7 µm で急落)の形を、吸収端の物理(直接遷移の √ と Urbach の裾)
    から出す。実機は製品のデータシートの曲線を ``spectral_product`` に直接渡すこと。

    出典: S. Adachi, J. Appl. Phys. 66, 6030 (1989)(III-V の直接遷移の吸収端)/ F. Urbach,
    Phys. Rev. 92, 1324 (1953)/ A. Rogalski, *Infrared Detectors*, 2nd ed., CRC (2010)(InGaAs の
    組成とカットオフ)。

    返り値: pairs(λ nm, QE)。
    """
    op = "ingaas_photodiode_qe"
    lam_c = _positive(cutoff_nm, "cutoff_nm", op)
    W = _positive(absorber_um, "absorber_um", op)
    lam_w = _positive(window_cutoff_nm, "window_cutoff_nm", op)
    dw = float(window_um)
    if not (math.isfinite(dw) and dw >= 0.0):
        raise ValueError("%s: window_um must be finite and >= 0, got %r" % (op, window_um))
    if lam_w >= lam_c:
        raise ValueError("%s: window_cutoff_nm (%g) must be shorter than cutoff_nm (%g)" % (op, lam_w, lam_c))
    r = float(front_reflectance)
    if not (0.0 <= r < 1.0):
        raise ValueError("%s: front_reflectance must lie in [0, 1), got %r" % (op, front_reflectance))
    eu = _positive(urbach_mev, "urbach_mev", op) * 1e-3
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    e = HC_EV_NM / wl
    a_abs = _direct_gap_alpha(e, HC_EV_NM / lam_c, 3.1, eu)
    a_win = _direct_gap_alpha(e, HC_EV_NM / lam_w, 4.0, eu)
    qe = (1.0 - r) * np.exp(-a_win * dw) * (1.0 - np.exp(-a_abs * W))
    return _pairs(wl, qe)


def _km_reflectance(K, S, X, Rg):
    """Kubelka (1948) の双曲線形。K, S [1/mm]、X [mm] (None = 無限厚)、Rg = 背景の反射率。"""
    K = np.asarray(K, dtype=np.float64)
    a = 1.0 + K / S
    b = np.sqrt(np.maximum(a * a - 1.0, 0.0))
    if X is None:
        return a - b
    bsx = b * S * X
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        coth = np.where(bsx > 1e-8, 1.0 / np.tanh(np.maximum(bsx, 1e-300)), 0.0)
        R = (1.0 - Rg * (a - b * coth)) / (a - Rg + b * coth)
    # b → 0(吸収の無い極限)は R = (S X (1 − Rg) + Rg) / (1 + S X (1 − Rg))(Kubelka 1948 の式 6)
    tiny = bsx <= 1e-8
    if np.any(tiny):
        sx = S * X
        R = np.where(tiny, (sx * (1.0 - Rg) + Rg) / (1.0 + sx * (1.0 - Rg)), R)
    return R


def kubelka_munk_reflectance(absorption, scattering_per_mm=5.0, thickness_mm=1.0, background_reflectance=0.0,
                             diffuse_factor=2.0):
    """散乱する層の拡散反射率を Kubelka–Munk の閉形式で(吸収係数の曲線から)。

    K = *diffuse_factor* · α(拡散光は斜めに通るので平行光の吸収係数の約 2 倍、Kubelka 1948)、
    S = *scattering_per_mm*。*thickness_mm*(既定 1 mm)が None なら無限厚 R∞ = 1 + K/S − √((K/S)² + 2K/S)、
    有限の厚さ X なら背景 R_g の上の層:

        R = [1 − R_g (a − b coth(bSX))] / [a − R_g + b coth(bSX)],  a = 1 + K/S, b = √(a² − 1)

    (Kubelka, J. Opt. Soc. Am. 38, 448 (1948))。極限: X → ∞ で R∞、K → 0 で
    (SX(1 − R_g) + R_g)/(1 + SX(1 − R_g))、R_g = R∞ なら厚さに依らず R∞。逆は K/S = (1 − R∞)²/(2R∞)。

    *absorption* は pairs(λ nm, α 1/mm)(``materials.material_nir_absorption`` の返り値)。
    *scattering_per_mm* は数か、*absorption* と同じ波長の pairs。

    返り値: pairs(λ nm, R)。界面の鏡面反射は含まない(:func:`spectral_reflectance_from_material` が
    Saunderson の補正で足す)。
    """
    op = "kubelka_munk_reflectance"
    a = _curve(absorption, "absorption", op)
    if np.any(a[:, 1] < 0.0):
        raise ValueError("%s: absorption must be >= 0" % op)
    if np.ndim(scattering_per_mm) == 0:
        S = np.full(a.shape[0], _positive(scattering_per_mm, "scattering_per_mm", op))
    else:
        s = _curve(scattering_per_mm, "scattering_per_mm", op)
        if s.shape != a.shape or not np.allclose(s[:, 0], a[:, 0]):
            raise ValueError("%s: a scattering curve must sample the same wavelengths as absorption" % op)
        if np.any(s[:, 1] <= 0.0):
            raise ValueError("%s: scattering must be > 0" % op)
        S = s[:, 1]
    X = None
    if thickness_mm is not None:
        X = _positive(thickness_mm, "thickness_mm", op)
    Rg = float(background_reflectance)
    if not (0.0 <= Rg <= 1.0):
        raise ValueError("%s: background_reflectance must lie in [0, 1], got %r" % (op, background_reflectance))
    f = _positive(diffuse_factor, "diffuse_factor", op)
    return _pairs(a[:, 0], _km_reflectance(f * a[:, 1], S, X, Rg))


def spectral_reflectance_from_material(material="NUT_KERNEL", particle_um=None, thickness_mm=10.0,
                                       background_reflectance=0.05, water_fraction=None,
                                       carbon_black_fraction=0.0, internal_reflectance=0.6,
                                       wl_min_nm=900.0, wl_max_nm=2500.0, n_points=321):
    """材料表の近赤外の吸収帯から、粒(破片)の拡散反射率スペクトルを作る(観察対象の側)。

    1. α(λ) = ``materials.material_nir_absorption``(帯の重ね合わせ、水は表の Hale & Querry)
       + カーボンブラック(``materials.carbon_black_absorption``、*carbon_black_fraction* 質量分率)。
    2. S = S_ref · (d_ref / *particle_um*)(散乱は粒径に反比例、S_ref と d_ref は材料の表の値)。
    3. 層の拡散反射 R_KM = :func:`kubelka_munk_reflectance`(既定は厚さ 10 mm の粒が *background_reflectance*
       の上に載る —— 薄い破片ほどベルトが透ける。None なら無限厚で、背景は効かない)。
    4. 界面: Saunderson (1942) の補正 R = r_s + (1 − r_s)(1 − r_i) R_KM / (1 − r_i R_KM)、
       r_s = ((n − 1)/(n + 1))²(表の n_nir の垂直入射 Fresnel)、r_i = *internal_reflectance*
       (中から見た拡散光の内部反射、0.4〜0.6 が典型)。鏡面の光沢は**波長に平坦**なので、
       黒い樹脂でも 4〜5 % の平らな反射が残り、帯の形が消える。

    返り値: pairs(λ nm, R)。粒が粗い・厚いほど暗く帯が深く、細かいほど明るく浅い(Kubelka–Munk
    の S 依存)。

    出典: Kubelka (1948)、J. L. Saunderson, J. Opt. Soc. Am. 32, 727 (1942)、帯の表は
    ``materials.NIR_BAND_MODELS`` の注。
    """
    op = "spectral_reflectance_from_material"
    import materials as _mat
    alpha = _mat.material_nir_absorption(material, wl_min_nm, wl_max_nm, n_points, water_fraction=water_fraction)
    cb = float(carbon_black_fraction)
    if not (math.isfinite(cb) and 0.0 <= cb <= 1.0):
        raise ValueError("%s: carbon_black_fraction must lie in [0, 1], got %r" % (op, carbon_black_fraction))
    if cb > 0.0:
        alpha[:, 1] += _mat.carbon_black_absorption(cb, wl_min_nm, wl_max_nm, n_points)[:, 1]
    info = _mat.nir_model_info(material)
    s_ref, d_ref = info.get("scattering_per_mm"), info.get("reference_um")
    if s_ref is None or d_ref is None:
        raise ValueError("%s: %s has no scattering data (a component or a liquid); use "
                         "kubelka_munk_reflectance with your own scattering" % (op, info["name"]))
    d = float(d_ref) if particle_um is None else _positive(particle_um, "particle_um", op)
    S = float(s_ref) * float(d_ref) / d
    r_km = _km_reflectance(2.0 * alpha[:, 1], S, None if thickness_mm is None else _positive(thickness_mm, "thickness_mm", op),
                           _unit_interval(background_reflectance, "background_reflectance", op))
    ri = _unit_interval(internal_reflectance, "internal_reflectance", op)
    if ri >= 1.0:
        raise ValueError("%s: internal_reflectance must be < 1" % op)
    n = float(info["n_nir"])
    rs = ((n - 1.0) / (n + 1.0)) ** 2
    R = rs + (1.0 - rs) * (1.0 - ri) * r_km / (1.0 - ri * r_km)
    return _pairs(alpha[:, 0], R)


def _unit_interval(v, name, op):
    x = float(v)
    if not (math.isfinite(x) and 0.0 <= x <= 1.0):
        raise ValueError("%s: %s must lie in [0, 1], got %r" % (op, name, v))
    return x


#: ハイパースペクトルの既定の帯域: 標準の InGaAs の窓 950〜1650 nm を 10 nm おき(71 帯)。
DEFAULT_BAND_CENTERS_NM = tuple(float(c) for c in np.arange(950.0, 1651.0, 10.0))


def hyperspectral_band_weights(wavelengths_nm=None, band_centers_nm=DEFAULT_BAND_CENTERS_NM, band_fwhm_nm=10.0,
                               source_temperature_k=3000.0, irradiance_w_m2=10000.0, f_number=2.0,
                               pixel_um=25.0, exposure_s=1e-3, optics_material="SILICA",
                               optics_thickness_mm=None, qe_cutoff_nm=1700.0):
    """反射率 → 帯域ごとの電子数の**線形写像** W(B × L)。電子数 = W @ R(λ)(雑音前)。

    鎖: ハロゲン(黒体 *source_temperature_k*、ベルト面の 900〜2500 nm の放射照度を
    *irradiance_w_m2* に合わせる)→ Lambert 面の放射輝度 L = E R/π → レンズ(F 値 *f_number*、
    像面照度 π L T/(4N²)、物体は遠方)→ ガラスの内部透過率(``materials.material_transmittance``、
    *optics_material* の厚さ *optics_thickness_mm*(None = 表面反射だけ)—— 光学系も観察対象と同じ材料表を引く)→ 分光の
    帯域(Gauss、半値全幅 *band_fwhm_nm*)→ 光子数(λ/hc)→ InGaAs の QE
    (:func:`ingaas_photodiode_qe`、*qe_cutoff_nm*)× 画素面積 × 露光時間。

    返り値: (B, L) の ndarray。*wavelengths_nm* は反射率の波長格子(nm、昇順、各帯の ±3σ を覆うこと。
    None なら 900〜2500 nm を 5 nm おき = ``spectral_reflectance_from_material`` の既定の格子)。
    """
    op = "hyperspectral_band_weights"
    import materials as _mat
    if wavelengths_nm is None:
        wavelengths_nm = np.linspace(900.0, 2500.0, 321)
    wl = np.asarray(wavelengths_nm, dtype=np.float64)
    if wl.ndim != 1 or wl.size < 3 or not np.all(np.isfinite(wl)) or np.any(np.diff(wl) <= 0.0) or wl[0] <= 0:
        raise ValueError("%s: wavelengths_nm must be a strictly increasing 1-D grid of >= 3 positive values" % op)
    centers = np.atleast_1d(np.asarray(band_centers_nm, dtype=np.float64))
    if centers.ndim != 1 or centers.size < 1 or not np.all(np.isfinite(centers)):
        raise ValueError("%s: band_centers_nm must be a non-empty 1-D list of wavelengths" % op)
    fw = _positive(band_fwhm_nm, "band_fwhm_nm", op)
    sig = fw / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    if centers.min() - 3.0 * sig < wl[0] - 1e-9 or centers.max() + 3.0 * sig > wl[-1] + 1e-9:
        raise ValueError("%s: the bands (%.6g-%.6g nm, +/-3 sigma) are not covered by the wavelength grid "
                         "%.6g-%.6g nm" % (op, centers.min(), centers.max(), wl[0], wl[-1]))
    T = _positive(source_temperature_k, "source_temperature_k", op)
    E0 = _positive(irradiance_w_m2, "irradiance_w_m2", op)
    N = _positive(f_number, "f_number", op)
    pix = _positive(pixel_um, "pixel_um", op) * 1e-6
    t = _positive(exposure_s, "exposure_s", op)
    # 光源: ベルト面の分光放射照度 [W m⁻² nm⁻¹] (900〜2500 nm の積分を E0 に)
    ref = blackbody_spectrum(T, 900.0, 2500.0, 1601)
    scale = E0 / spectral_integral(ref)
    x = 2.0 * PLANCK_H * LIGHT_C ** 2 / (wl * 1e-9) ** 5 / np.expm1(PLANCK_H * LIGHT_C / (wl * 1e-9 * BOLTZMANN_K * T)) * 1e-9
    E = x * scale
    # 光学系: ガラスの透過率(表面反射込み)。0 mm なら 1、None なら表面反射だけ(内部の吸収を数えない)。
    # ★既定の溶融石英(SILICA、Malitson の分散式)は材料表に k が無く、厚さは効かない —— 内部の吸収を入れたいなら
    #   k を持つ硝材の名前と厚さを渡す(材料表の glass の類)。
    tt = 1e-6 if optics_thickness_mm is None else float(optics_thickness_mm)
    if not (math.isfinite(tt) and tt >= 0.0):
        raise ValueError("%s: optics_thickness_mm must be finite and >= 0, got %r" % (op, optics_thickness_mm))
    if tt > 0.0:
        Tg = _mat.material_transmittance(optics_material, tt, float(wl[0]), float(wl[-1]), int(wl.size))
        Topt = np.interp(wl, Tg[:, 0], Tg[:, 1])
    else:
        Topt = np.ones_like(wl)
    qe_curve = ingaas_photodiode_qe(_positive(qe_cutoff_nm, "qe_cutoff_nm", op), wl_min_nm=float(wl[0]),
                                    wl_max_nm=float(wl[-1]), n_points=int(wl.size))
    qe = np.interp(wl, qe_curve[:, 0], qe_curve[:, 1])
    # 像面の分光照度 [W m⁻² nm⁻¹ per unit R] → 画素の光子数 [光子 nm⁻¹ per unit R]
    per_nm = E / math.pi * (math.pi * Topt / (4.0 * N * N)) * pix * pix * t * (wl * 1e-9) / (PLANCK_H * LIGHT_C) * qe
    dl = np.gradient(wl)                                         # 台形則に近い重み(非一様格子でも可)
    filt = np.exp(-0.5 * ((wl[None, :] - centers[:, None]) / sig) ** 2)
    return filt * (per_nm * dl)[None, :]


def hyperspectral_capture(reflectance, band_centers_nm=DEFAULT_BAND_CENTERS_NM, band_fwhm_nm=10.0,
                          source_temperature_k=3000.0, irradiance_w_m2=10000.0, f_number=2.0, pixel_um=25.0,
                          exposure_s=1e-3, optics_material="SILICA", optics_thickness_mm=None,
                          qe_cutoff_nm=1700.0, read_noise_e=30.0, dark_e=0.0):
    """反射率スペクトル 1 本を、ハロゲン × 光学系 × 帯域 × InGaAs で撮ったときの帯域ごとの電子数と雑音。

    電子数 = :func:`hyperspectral_band_weights` @ R、雑音 σ = √(電子数 + 暗電流 + 読出し²)
    (ショット雑音 + 暗電流のショット + 読出し、EMVA 1288 の線形モデル)。決定的(雑音の**大きさ**を返し、
    乱数は引かない)—— 画像に雑音を載せるのは :func:`hyperspectral_capture_cube`。

    *reflectance* は pairs(λ nm, R)。返り値: dict(band_centers_nm, electrons, noise_e, snr,
    white_electrons(R = 1 の白板で同じ設定の電子数 = 平場補正の分母))。
    """
    op = "hyperspectral_capture"
    a = _curve(reflectance, "reflectance", op)
    Wm = hyperspectral_band_weights(a[:, 0], band_centers_nm, band_fwhm_nm, source_temperature_k, irradiance_w_m2,
                                    f_number, pixel_um, exposure_s, optics_material, optics_thickness_mm,
                                    qe_cutoff_nm)
    rd = float(read_noise_e)
    dk = float(dark_e)
    if not (math.isfinite(rd) and rd >= 0.0 and math.isfinite(dk) and dk >= 0.0):
        raise ValueError("%s: read_noise_e and dark_e must be finite and >= 0" % op)
    e = Wm @ a[:, 1]
    white = Wm.sum(axis=1)
    sig = np.sqrt(np.maximum(e, 0.0) + dk + rd * rd)
    with np.errstate(divide="ignore", invalid="ignore"):
        snr = np.where(sig > 0.0, e / np.where(sig > 0.0, sig, 1.0), 0.0)
    return {"band_centers_nm": np.atleast_1d(np.asarray(band_centers_nm, dtype=np.float64)).copy(),
            "electrons": e, "noise_e": sig, "snr": snr, "white_electrons": white}


def hyperspectral_capture_cube(cube, wavelengths_nm, seed=0, read_noise_e=30.0, dark_e=0.0, **chain):
    """反射率のキューブ (H, W, L) を撮って、雑音つきの電子数のキューブ (H, W, B) を返す。

    :func:`hyperspectral_capture` と**同じ線形写像**(:func:`hyperspectral_band_weights`、*chain* はその引数)
    を画素ごとに掛け、Poisson(電子数 + 暗電流) − 暗電流 + N(0, 読出し²) を載せる(*seed* で決定的)。
    返り値: dict(cube (H, W, B) の電子数, clean(雑音前), white_electrons (B,), band_centers_nm)。
    """
    op = "hyperspectral_capture_cube"
    c = np.asarray(cube, dtype=np.float64)
    if c.ndim != 3 or c.shape[2] < 3 or not np.all(np.isfinite(c)):
        raise ValueError("%s: cube must be a finite (H, W, L) reflectance array with L >= 3, got %s" % (op, c.shape))
    wl = np.asarray(wavelengths_nm, dtype=np.float64)
    if wl.shape != (c.shape[2],):
        raise ValueError("%s: wavelengths_nm must have length L = %d" % (op, c.shape[2]))
    Wm = hyperspectral_band_weights(wl, **chain)
    rd, dk = float(read_noise_e), float(dark_e)
    if not (math.isfinite(rd) and rd >= 0.0 and math.isfinite(dk) and dk >= 0.0):
        raise ValueError("%s: read_noise_e and dark_e must be finite and >= 0" % op)
    clean = np.einsum("hwl,bl->hwb", c, Wm, optimize=True)
    rng = np.random.default_rng(seed)
    noisy = rng.poisson(np.maximum(clean, 0.0) + dk).astype(np.float64) - dk + rng.normal(0.0, rd, clean.shape)
    centers = np.atleast_1d(np.asarray(chain.get("band_centers_nm", DEFAULT_BAND_CENTERS_NM), dtype=np.float64))
    return {"cube": noisy, "clean": clean, "white_electrons": Wm.sum(axis=1), "band_centers_nm": centers.copy()}
