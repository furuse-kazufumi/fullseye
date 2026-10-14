# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""filmoptics — 多層膜の分光反射率と、反射スペクトル・色・分光画像からの膜厚測定。

動機(2026-10-15、材料ライブラリの系列「薄膜」): 半導体(Si 上の SiO₂・Si₃N₄・レジスト)、ディスプレイの
コート、AR 膜の膜厚は、反射スペクトルの干渉縞から非接触で測るのが定番(分光干渉式の膜厚計)。単層の
Airy の式は ``matappear.thin_film_reflectance`` にあるが、**膜を何層も重ねる**計算(転送行列)と、
**スペクトル → 膜厚**の逆問題(縞の周期の FFT・モデルあてはめ・画素ごとの膜厚マップ)と、**膜厚 → 見える色**
(ウェハの色見本)が無かった。膜・基板の n,k はすべて材料表 ``materials`` の鍵で指定する —— 観察用の
光学系と観察対象が同じ材料表を引く(Fullseye の設計原則)。

内容(5 op):
  順問題  `multilayer_reflectance`(特性行列 = 転送行列。斜入射・s/p・集光 NA の角度平均・共形な粗さ)
          `film_color`(膜厚 → D65 で見た sRGB・CIELAB。ウェハの干渉色の色見本)
  逆問題  `film_thickness_fft`(縞の周期 → 光学的厚さ。分散は材料表で補正)
          `film_thickness_fit`(転送行列の非線形最小二乗。格子探索で大域、局所で精密化、候補を全部返す)
          `film_thickness_map`(分光画像 / RGB 画像の画素ごとの膜厚。候補の数 = 不定性の地図)

物理(Born & Wolf §1.6、Macleod §2):
  層 j の特性行列 M_j = [[cos δ_j, −i sin δ_j / η_j], [−i η_j sin δ_j, cos δ_j]] (N = n + ik の規約)、δ_j = 2π N_j d_j cos θ_j / λ、
  傾いた光学アドミッタンス η = N cos θ(s)/ N / cos θ(p)。[B, C]ᵀ = Π M_j [1, η_sub]ᵀ、
  r = (η₀B − C)/(η₀B + C)、R = |r|²、T = 4 η₀ Re(η_sub) / |η₀B + C|²。
  集光(NA)の角度平均は、瞳を一様に満たす照明で重みが sin²θ について一様になる(瞳の面積要素 ∝ d(sin²θ))。
  共形な粗さ(すべての界面が同じ高さ h(x) で揺れる、下地の粗さを膜が写す場合)は積層全体の平行移動なので、
  鏡面反射の振幅に ⟨e^{2ik₀n₀cosθ₀h}⟩ が掛かり、R に Debye–Waller の因子 exp(−(4π n₀ σ cos θ₀ / λ)²) が掛かる。

来歴(公開文献のみ):
  * Born & Wolf, *Principles of Optics*, 7th ed. (1999) §1.6.2(層状媒質の特性行列)。
  * Macleod, *Thin-Film Optical Filters*, 4th ed. (2010) §2.2(傾いたアドミッタンス・多層膜の R/T)。
  * Byrnes, "Multilayer optical calculations", arXiv:1603.02720(転送行列の実装の作法・吸収層の枝の選び方)。
  * Pliskin & Conrad, IBM J. Res. Dev. 8(1), 43–51 (1964)(SiO₂ on Si の干渉色の色表)/
    Henrie, Kellis, Schultz & Hawkins, Opt. Express 12(7), 1464–1469 (2004)(色表を計算で作る)。

規約: 波長は nm、膜厚は nm。層は**入射側から**順に ``[(材料, 厚さ nm), ...]``。材料は材料表の鍵(``"SIO2"``、
``"SI3N4"``、``"PMMA"`` …)・材料レコード・実数・複素数 n + ik(理想化した検算用)。基板は半無限。
fail-closed: 材料表に無い鍵、表の波長範囲の外、負・非有限の膜厚、不透明すぎて行列が溢れる層は ValueError。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "multilayer_reflectance", "film_color", "film_thickness_fft", "film_thickness_fit", "film_thickness_map",
]

#: 特性行列の cos/sin が溢れない範囲の |Im δ|(e^300 ≈ 1e130)。超える層は実質的に不透明 → 基板として書く。
_MAX_IM_DELTA = 300.0

#: film_color の既定の可視域 [nm] (CIE の等色関数の主な範囲)。
VIS_MIN_NM, VIS_MAX_NM = 380.0, 780.0


# --------------------------------------------------------------------------- #
# 入力の検査                                                                    #
# --------------------------------------------------------------------------- #
def _finite_nonneg(v, name, op):
    x = float(v)
    if not (math.isfinite(x) and x >= 0.0):
        raise ValueError("%s: %s must be finite and >= 0, got %r" % (op, name, v))
    return x


def _wavelengths(wavelengths_nm, wl_min_nm, wl_max_nm, n_points, op):
    if wavelengths_nm is not None:
        w = np.asarray(wavelengths_nm, dtype=np.float64)
        if w.ndim != 1 or w.size < 1:
            raise ValueError("%s: wavelengths_nm must be a non-empty 1-D array" % op)
        if not np.all(np.isfinite(w)) or np.any(w <= 0.0):
            raise ValueError("%s: wavelengths_nm must be finite and > 0" % op)
        if w.size > 1 and np.any(np.diff(w) <= 0.0):
            raise ValueError("%s: wavelengths_nm must be strictly increasing" % op)
        return w
    lo, hi, n = float(wl_min_nm), float(wl_max_nm), int(n_points)
    if not (math.isfinite(lo) and math.isfinite(hi)) or lo <= 0.0 or hi <= lo or n < 2:
        raise ValueError("%s: need 0 < wl_min_nm < wl_max_nm and n_points >= 2" % op)
    return np.linspace(lo, hi, n)


def _index(v, lam, name, op):
    """材料の指定 → 波長 lam [nm] での複素屈折率の配列(matappear と同じ解決: 鍵・レコード・数・配列)。"""
    import matappear as _ma
    if isinstance(v, dict):
        import materials as _mat
        rec = _mat._record(v, op)
        n, k = _mat._nk(rec, np.asarray(lam, dtype=np.float64).ravel() / 1000.0, op)[:2]
        return (n + 1j * k).reshape(np.shape(lam))
    return np.broadcast_to(_ma._film_index(v, lam, name, op), np.shape(lam)).astype(np.complex128)


def _ambient(v, lam, op):
    n0 = _index(v, lam, "ambient", op)
    if np.any(n0.imag > 1e-3):
        raise ValueError("%s: the ambient (incident) medium must be transparent (k <= 1e-3): got %r" % (op, v))
    return n0.real.astype(np.complex128)


def _layers(layers, op):
    if layers is None:
        return []
    if isinstance(layers, (str, bytes)) or not hasattr(layers, "__iter__"):
        raise ValueError("%s: layers must be a sequence of (material, thickness_nm) pairs, got %r" % (op, layers))
    out = []
    for i, item in enumerate(layers):
        try:
            mat, d = item
        except (TypeError, ValueError):
            raise ValueError("%s: layer %d must be a (material, thickness_nm) pair, got %r" % (op, i, item)) from None
        out.append((mat, _finite_nonneg(d, "thickness of layer %d" % i, op)))
    return out


def _cos_in(n_layer, n0_sin0):
    """層の中の複素 cos θ̃(減衰する枝 Im(N cos θ̃) ≥ 0)。matappear と同じ選び方。"""
    c = np.sqrt(1.0 - (n0_sin0 / n_layer) ** 2 + 0j)
    return np.where((n_layer * c).imag < 0.0, -c, c)


# --------------------------------------------------------------------------- #
# 心臓部: 特性行列(ブロードキャスト可)                                         #
# --------------------------------------------------------------------------- #
def _stack_rt(lam, n0, layer_n, layer_d, n_sub, sin0, pol, op):
    """R, T(偏光 1 つ)。lam は (..., K)、layer_d の各要素は lam とブロードキャストできる厚さ [nm]。"""
    n0_sin0 = n0 * sin0
    c0 = np.sqrt(1.0 - sin0 ** 2 + 0j)

    def adm(n, c):
        return n * c if pol == "s" else n / c

    eta0 = adm(n0, c0)
    cs = _cos_in(n_sub, n0_sin0)
    eta_s = adm(n_sub, cs)
    m11 = np.ones(np.broadcast(lam, eta_s).shape, dtype=np.complex128)
    m12 = np.zeros_like(m11)
    m21 = np.zeros_like(m11)
    m22 = np.ones_like(m11)
    for n, d in zip(layer_n, layer_d):
        c = _cos_in(n, n0_sin0)
        delta = 2.0 * np.pi * n * c * d / lam
        if np.any(np.abs(delta.imag) > _MAX_IM_DELTA):
            raise ValueError("%s: a layer is optically opaque (|Im delta| > %g); model it as the substrate instead"
                             % (op, _MAX_IM_DELTA))
        eta = adm(n, c)
        cd, sd = np.cos(delta), np.sin(delta)
        # 時間因子 e^{-iωt}(N = n + ik、減衰は Im(N cos θ) ≥ 0)の規約では行列の虚数単位は −i(Macleod の n − ik の共役)
        a11, a12, a21, a22 = cd, -1j * sd / eta, -1j * eta * sd, cd
        m11, m12, m21, m22 = (m11 * a11 + m12 * a21, m11 * a12 + m12 * a22,
                              m21 * a11 + m22 * a21, m21 * a12 + m22 * a22)
    B = m11 + m12 * eta_s
    C = m21 + m22 * eta_s
    den = eta0 * B + C
    r = (eta0 * B - C) / den
    R = np.abs(r) ** 2
    T = 4.0 * eta0.real * eta_s.real / np.abs(den) ** 2
    return R, T


def _angle_nodes(angle_deg, na, n0_real, op):
    """(sin θ₀ の節, 重み)。NA > 0 は瞳を一様に満たす集光: 重みは sin²θ について一様(Gauss–Legendre 16 点)。"""
    a = float(angle_deg)
    if not (math.isfinite(a) and 0.0 <= a < 90.0):
        raise ValueError("%s: angle_deg must lie in [0, 90): got %r" % (op, angle_deg))
    na = float(na)
    if not (math.isfinite(na) and 0.0 <= na < float(np.min(n0_real))):
        raise ValueError("%s: na must lie in [0, n_ambient): got %r" % (op, na))
    if na > 0.0 and a > 0.0:
        raise ValueError("%s: give either an oblique angle_deg or a focusing na (a cone around the normal), not both" % op)
    if na == 0.0:
        return np.array([math.sin(math.radians(a))]), np.array([1.0])
    x, w = np.polynomial.legendre.leggauss(16)
    u = 0.5 * (x + 1.0) * (na / n0_real.min()) ** 2          # u = sin²θ ∈ [0, (NA/n₀)²]
    return np.sqrt(u), 0.5 * w


def _reflect(lam, n0, layer_n, layer_d, n_sub, angle_deg, na, polarization, roughness_nm, op, want_t=False):
    if polarization not in ("unpolarized", "s", "p"):
        raise ValueError("%s: polarization must be 'unpolarized', 's' or 'p': got %r" % (op, polarization))
    sig = _finite_nonneg(roughness_nm, "roughness_nm", op)
    pols = ("s", "p") if polarization == "unpolarized" else (polarization,)
    sins, ws = _angle_nodes(angle_deg, na, np.atleast_1d(n0.real), op)
    R = 0.0
    T = 0.0
    for s0, w in zip(sins, ws):
        for p in pols:
            r_, t_ = _stack_rt(lam, n0, layer_n, layer_d, n_sub, s0, p, op)
            if sig > 0.0:
                c0 = math.sqrt(1.0 - s0 * s0)
                r_ = r_ * np.exp(-(4.0 * np.pi * n0.real * sig * c0 / lam) ** 2)
            R = R + w * r_ / len(pols)
            T = T + w * t_ / len(pols)
    return (R, T) if want_t else R


def _resolve_stack(layers, substrate, ambient, lam, op):
    ls = _layers(layers, op)
    n0 = _ambient(ambient, lam, op)
    layer_n = [_index(m, lam, "layer material", op) for m, _ in ls]
    layer_d = [d for _, d in ls]
    n_sub = _index(substrate, lam, "substrate", op)
    return n0, layer_n, layer_d, n_sub


# --------------------------------------------------------------------------- #
# 1. 順問題                                                                     #
# --------------------------------------------------------------------------- #
def multilayer_reflectance(layers=(("SIO2", 100.0),), substrate="SI", wl_min_nm=400.0, wl_max_nm=800.0,
                           n_points=201, angle_deg=0.0, polarization="unpolarized", na=0.0, roughness_nm=0.0,
                           ambient=1.0, quantity="reflectance", wavelengths_nm=None):
    """多層膜の分光反射率(または透過率・吸収率)を ``pairs``(λ [nm], 値)で返す。特性行列(転送行列)の厳密解。

    layers:       入射側から順の ``[(材料, 厚さ nm), ...]``。材料は材料表の鍵(``"SIO2"`` / ``"SI3N4"`` / ``"PMMA"``
                  / ``"TIO2"`` …)・材料レコード・実数・複素数 n + ik。空にすると基板だけ(裸の面の Fresnel)。
    substrate:    基板(半無限)。既定は材料表の Si(Green 2008、k つき)。
    wl_min_nm / wl_max_nm / n_points: 波長の等間隔格子。``wavelengths_nm`` を渡せばそちらを使う(昇順)。
    angle_deg:    入射角(入射側の媒質の中)。
    polarization: "unpolarized"(s と p の平均)/ "s" / "p"。
    na:           集光の開口数(> 0 なら法線まわりの円錐で角度平均。瞳を一様に満たす照明 = 重みは sin²θ に一様)。
                  angle_deg と同時には指定できない。
    roughness_nm: 共形な粗さの RMS σ。R に exp(−(4π n₀ σ cos θ₀ / λ)²)(Debye–Waller)が掛かる。
    ambient:      入射側の媒質(実数か材料表の鍵、透明であること)。液浸なら ``"WATER"``。
    quantity:     "reflectance" / "transmittance"(基板の中へ入る割合)/ "absorptance"(層での吸収 = 1 − R − T)。
                  粗さ > 0 では T と A を出さない(散乱光の行き先をこのモデルは持たない → ValueError)。

    返り値: (K, 2) の pairs。

    真値: 1 層なら ``matappear.thin_film_reflectance``(Airy の式、別実装)と一致する。膜厚 0 は裸の基板の Fresnel、
    λ/4 の AR 膜(n = √n_sub)は設計波長で R = 0、(HL)^N の鏡は閉形式 ((1 − q)/(1 + q))²、q = (n_s/n₀)(n_H/n_L)^{2N}(H が入射側)。
    吸収の無い積層では R + T = 1。

    >>> p = multilayer_reflectance([("SIO2", 500.0)], "SI", 400.0, 800.0, 5)
    >>> p.shape
    (5, 2)
    """
    op = "multilayer_reflectance"
    if quantity not in ("reflectance", "transmittance", "absorptance"):
        raise ValueError("%s: quantity must be 'reflectance', 'transmittance' or 'absorptance': got %r" % (op, quantity))
    lam = _wavelengths(wavelengths_nm, wl_min_nm, wl_max_nm, n_points, op)
    if quantity != "reflectance" and float(roughness_nm) != 0.0:
        raise ValueError("%s: transmittance/absorptance are not modelled with roughness_nm > 0" % op)
    n0, layer_n, layer_d, n_sub = _resolve_stack(layers, substrate, ambient, lam, op)
    R, T = _reflect(lam, n0, layer_n, layer_d, n_sub, angle_deg, na, polarization, roughness_nm, op, want_t=True)
    val = {"reflectance": R, "transmittance": T, "absorptance": 1.0 - R - T}[quantity]
    return np.column_stack([lam, np.real(val)])


def _lab(xyz):
    """XYZ(白 = D65、Y = 1)→ CIELAB(CIE 15:2004)。"""
    import matappear as _ma
    t = np.asarray(xyz, dtype=np.float64) / _ma._D65_XYZ
    e = (6.0 / 29.0) ** 3
    f = np.where(t > e, np.cbrt(np.maximum(t, e)), t / (3.0 * (6.0 / 29.0) ** 2) + 4.0 / 29.0)
    L = 116.0 * f[..., 1] - 16.0
    a = 500.0 * (f[..., 0] - f[..., 1])
    b = 200.0 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def _srgb_gamma(lin):
    x = np.clip(lin, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def film_color(film="SIO2", substrate="SI", thickness_min_nm=0.0, thickness_max_nm=1000.0, n_points=101,
               under=(), angle_deg=0.0, na=0.0, wl_min_nm=VIS_MIN_NM, wl_max_nm=VIS_MAX_NM, ambient=1.0,
               exposure=1.0, illuminant=None):
    """膜厚を振ったときの干渉色(ウェハの色見本)。D65 の照明・CIE 1931 の等色関数で見た色を返す。

    film:       膜の材料(材料表の鍵など)。``under`` があればその上に乗る最上層。
    substrate:  基板。
    thickness_min_nm / thickness_max_nm / n_points: 膜厚の格子。
    under:      膜と基板の間の層 ``[(材料, 厚さ nm), ...]``(入射側から順)。
    angle_deg / na / ambient: :func:`multilayer_reflectance` と同じ。
    wl_min_nm / wl_max_nm: 色を積む波長の範囲(既定 380〜780 nm。材料表の範囲が足りなければ ValueError)。
    exposure:   線形 sRGB に掛ける露出(見本を明るく見せたいとき。CIELAB と色相は露出 1 の値)。
    illuminant: 照明の分光分布 ``pairs``(λ [nm], 相対値)。None は D65(``matappear`` の平滑近似)。
                白(反射率 1)が sRGB の白に落ちるよう同じ照明で正規化する(白色順応)。輝線の多い蛍光灯では
                厚い膜の色が残る —— 連続光では縞が帯域内で平均されて灰色に近づく。

    返り値 dict:
      thickness_nm (N,) / reflectance (N, K) と wavelength_nm (K,) / linear_srgb (N, 3)(白 = 1、負は色域外)/
      srgb (N, 3)(ガンマ済み・0〜1 に切った表示用)/ lab (N, 3)(CIELAB、白 = D65)/ hue_deg (N,)(a*b* の色相角)/
      chroma (N,)。

    ★色は膜厚について**周期的に繰り返す**(SiO₂ on Si では光学的厚さ n d が約 λ/2 ≈ 190 nm 進むごとに似た色に戻る)
    —— 色だけでは膜厚が一意に決まらない(:func:`film_thickness_map` の ``n_candidates``)。
    """
    op = "film_color"
    lo, hi, n = float(thickness_min_nm), float(thickness_max_nm), int(n_points)
    if not (math.isfinite(lo) and math.isfinite(hi)) or lo < 0.0 or hi <= lo or n < 2:
        raise ValueError("%s: need 0 <= thickness_min_nm < thickness_max_nm and n_points >= 2" % op)
    d = np.linspace(lo, hi, n)
    ex = float(exposure)
    if not (math.isfinite(ex) and ex > 0.0):
        raise ValueError("%s: exposure must be finite and > 0" % op)
    lam = _wavelengths(None, wl_min_nm, wl_max_nm, int(round(float(wl_max_nm) - float(wl_min_nm))) + 1, op)
    stack = [(film, 0.0)] + list(_layers(under, op))
    n0, layer_n, layer_d, n_sub = _resolve_stack(stack, substrate, ambient, lam, op)
    layer_d = [d[:, None]] + layer_d[1:]
    R = _reflect(lam[None, :], n0, layer_n, layer_d, n_sub, angle_deg, na, "unpolarized", 0.0, op)
    ill = None
    if illuminant is not None:
        sp = np.asarray(illuminant, dtype=np.float64)
        if sp.ndim != 2 or sp.shape[1] != 2 or sp.shape[0] < 2 or not np.all(np.isfinite(sp)) or np.any(sp[:, 1] < 0):
            raise ValueError("%s: illuminant must be pairs (lambda nm, value >= 0)" % op)
        if sp[0, 0] > lam[0] or sp[-1, 0] < lam[-1] or np.any(np.diff(sp[:, 0]) <= 0):
            raise ValueError("%s: illuminant must be increasing and cover %g-%g nm" % (op, lam[0], lam[-1]))
        ill = np.interp(lam, sp[:, 0], sp[:, 1])
        if not np.any(ill > 0):
            raise ValueError("%s: illuminant is zero over the band" % op)
    import matappear as _ma
    lin = _ma.spectrum_to_srgb(lam, R, ill)
    xyz = lin @ np.linalg.inv(_ma._XYZ_TO_SRGB).T
    lab = _lab(xyz)
    return {"thickness_nm": d, "wavelength_nm": lam, "reflectance": R, "linear_srgb": lin * ex,
            "srgb": _srgb_gamma(lin * ex), "lab": lab,
            "hue_deg": np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360.0,
            "chroma": np.hypot(lab[:, 1], lab[:, 2])}


# --------------------------------------------------------------------------- #
# 2. 逆問題                                                                     #
# --------------------------------------------------------------------------- #
def _spectrum(spectrum, op, min_points=8):
    a = np.asarray(spectrum, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 2 or a.shape[0] < min_points:
        raise ValueError("%s: spectrum must be pairs (lambda nm, value) with >= %d rows, got shape %s"
                         % (op, min_points, a.shape))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: spectrum contains non-finite values" % op)
    if np.any(a[:, 0] <= 0.0) or np.any(np.diff(a[:, 0]) <= 0.0):
        raise ValueError("%s: spectrum wavelengths must be > 0 and strictly increasing" % op)
    return a[:, 0], a[:, 1]


def film_thickness_fft(spectrum, film="SIO2", window="hann", pad_factor=16):
    """反射スペクトルの干渉縞の周期 → 膜厚(FFT 法)。分散は材料表の n(λ) で補正する。

    spectrum:   ``pairs``(λ [nm], R)。等間隔でなくてよい。
    film:       膜の材料(鍵・数値)。縞の位相は 4π n(λ) d / λ = 2π d x、x = 2 n(λ)/λ [1/nm] なので、x の等間隔格子に
                取り直してから FFT すると、ピークの周波数がそのまま膜厚 d [nm] になる(分散の補正込み)。
    window:     "hann"(既定、漏れが小さい)/ "rect"(主ローブが細い)。
    pad_factor: ゼロ詰めの倍率(ピークの位置を細かく読む。分解能は増えない)。

    返り値 dict: thickness_nm / peak_amplitude / span_x(x の幅 Δx [1/nm])/ n_fringes(= d·Δx、帯域に入る縞の本数)/
      resolution_nm(= 1/Δx、2 つの膜厚を見分ける幅)/ min_thickness_nm(この窓の主ローブの半幅 = 測れる下限の閉形式:
      hann 2/Δx、rect 1/Δx)/ reliable(d ≥ min_thickness_nm)/ frequency_nm と magnitude(FFT の振幅スペクトル)。

    ★下限は閉形式で先に分かる: 帯域 λ₁〜λ₂ の縞の本数は 2 n̄ d (1/λ₁ − 1/λ₂)。窓の主ローブ(DC の山)より
    ピークが外に出ないと、FFT 法は DC に引きずられて**系統的に外れる**(薄い膜ではモデルあてはめを使う)。
    """
    op = "film_thickness_fft"
    lam, R = _spectrum(spectrum, op)
    if window not in ("hann", "rect"):
        raise ValueError("%s: window must be 'hann' or 'rect': got %r" % (op, window))
    pf = int(pad_factor)
    if pf < 1 or pf > 256:
        raise ValueError("%s: pad_factor must lie in [1, 256]: got %r" % (op, pad_factor))
    n = np.real(_index(film, lam, "film", op))
    x = 2.0 * n / lam
    order = np.argsort(x)
    xs, rs = x[order], R[order]
    if np.any(np.diff(xs) <= 0.0):
        raise ValueError("%s: 2 n(lambda)/lambda must be monotonic over the band (anomalous dispersion?)" % op)
    m = lam.size
    xu = np.linspace(xs[0], xs[-1], m)
    ru = np.interp(xu, xs, rs)
    ru = ru - ru.mean()
    w = np.hanning(m) if window == "hann" else np.ones(m)
    span = float(xs[-1] - xs[0])
    dx = span / (m - 1)
    nfft = int(2 ** math.ceil(math.log2(m * pf)))
    mag = np.abs(np.fft.rfft(ru * w, nfft))
    freq = np.fft.rfftfreq(nfft, dx)                      # [nm]
    lobe = (2.0 if window == "hann" else 1.0) / span
    ok = freq > 0.5 / span
    if not np.any(ok) or not np.any(mag[ok] > 0):
        raise ValueError("%s: the spectrum has no fringe (flat after removing the mean)" % op)
    idx = np.flatnonzero(ok)
    i = int(idx[np.argmax(mag[ok])])
    f = float(freq[i])
    if 0 < i < mag.size - 1:
        a, b, c = np.log(mag[i - 1:i + 2] + 1e-300)
        den = a - 2.0 * b + c
        if den < 0:
            f = float(freq[i] + 0.5 * (a - c) / den * (freq[1] - freq[0]))
    return {"thickness_nm": f, "peak_amplitude": float(mag[i]) / max(float(np.sum(w)), 1e-300) * 2.0,
            "span_x": span, "n_fringes": f * span, "resolution_nm": 1.0 / span, "min_thickness_nm": lobe,
            "reliable": bool(f >= lobe), "frequency_nm": freq, "magnitude": mag}


def _model_lut(lam, film, substrate, under, d_grid, angle_deg, na, ambient, roughness_nm, op):
    stack = [(film, 0.0)] + list(_layers(under, op))
    n0, layer_n, layer_d, n_sub = _resolve_stack(stack, substrate, ambient, lam, op)
    layer_d = [np.asarray(d_grid, dtype=np.float64)[:, None]] + layer_d[1:]
    return _reflect(lam[None, :], n0, layer_n, layer_d, n_sub, angle_deg, na, "unpolarized", roughness_nm, op)


def _local_minima(cost):
    c = np.asarray(cost)
    left = np.r_[np.inf, c[:-1]]
    right = np.r_[c[1:], np.inf]
    return np.flatnonzero((c <= left) & (c < right))


def _grid_step(lam, film, op, d_hi):
    nmax = float(np.max(np.real(_index(film, lam, "film", op))))
    return max(0.25, min(float(lam.min()) / (32.0 * nmax), d_hi / 64.0))


def film_thickness_fit(spectrum, film="SIO2", substrate="SI", thickness_min_nm=0.0, thickness_max_nm=3000.0,
                       under=(), angle_deg=0.0, na=0.0, fit_scale=False, ambient=1.0, roughness_nm=0.0):
    """反射スペクトルに転送行列のモデルをあてはめて膜厚を出す(非線形最小二乗、大域の格子探索 → 局所の精密化)。

    spectrum:     ``pairs``(λ [nm], R)。
    film / substrate / under: モデルの積層(材料表の鍵)。最上層 ``film`` の厚さを未知数にする。
    thickness_min_nm / thickness_max_nm: 探す範囲。格子は位相が λ_min で π/8 進む刻み(局所解に落ちない)。
    angle_deg / na / ambient / roughness_nm: 測定の条件(:func:`multilayer_reflectance` と同じ)。モデル側の
                  条件を実測と違えると膜厚が偏る —— その偏りを測るのが PoC の章。
    fit_scale:    True なら反射率の倍率 a も同時に(閉形式で)あてはめる(反射率の絶対値の校正が無い装置)。

    返り値 dict: thickness_nm / rmse / scale / candidates(局所解の [(膜厚, rmse), ...] を rmse の昇順)/
      second_rmse_ratio(2 番目の候補の rmse ÷ 最良。1 に近いほど一意でない)。

    ★薄い膜(縞が 1 本未満)でも、絶対反射率の形から膜厚が決まる —— FFT 法が破綻する領域で使える。
    ただし材料(n)を取り違えると、光学的厚さ n d を保ったまま d が n の比だけ偏る。
    """
    op = "film_thickness_fit"
    lam, R = _spectrum(spectrum, op)
    lo, hi = float(thickness_min_nm), float(thickness_max_nm)
    if not (math.isfinite(lo) and math.isfinite(hi)) or lo < 0.0 or hi <= lo:
        raise ValueError("%s: need 0 <= thickness_min_nm < thickness_max_nm" % op)
    step = _grid_step(lam, film, op, hi - lo)
    grid = np.arange(lo, hi + 0.5 * step, step)
    grid[-1] = min(grid[-1], hi)
    args = (lam, film, substrate, under)
    kw = dict(angle_deg=angle_deg, na=na, ambient=ambient, roughness_nm=roughness_nm, op=op)

    def cost_of(d):
        M = _model_lut(*args, np.atleast_1d(d), **kw)
        if fit_scale:
            a = np.sum(M * R, axis=1) / np.maximum(np.sum(M * M, axis=1), 1e-300)
        else:
            a = np.ones(M.shape[0])
        return np.sqrt(np.mean((a[:, None] * M - R) ** 2, axis=1)), a

    c, _ = cost_of(grid)
    mins = _local_minima(c)
    cands = []
    for i in mins:
        a_, b_ = grid[max(i - 1, 0)], grid[min(i + 1, grid.size - 1)]
        gr = 0.5 * (math.sqrt(5.0) - 1.0)
        x1, x2 = b_ - gr * (b_ - a_), a_ + gr * (b_ - a_)
        f1, f2 = cost_of(x1)[0][0], cost_of(x2)[0][0]
        for _ in range(60):                               # 黄金分割(区間は格子 2 刻み = 単峰)
            if f1 < f2:
                b_, x2, f2 = x2, x1, f1
                x1 = b_ - gr * (b_ - a_)
                f1 = cost_of(x1)[0][0]
            else:
                a_, x1, f1 = x1, x2, f2
                x2 = a_ + gr * (b_ - a_)
                f2 = cost_of(x2)[0][0]
            if b_ - a_ < 1e-6:
                break
        dbest = 0.5 * (a_ + b_)
        cc, aa = cost_of(dbest)
        cands.append((float(dbest), float(cc[0]), float(aa[0])))
    cands.sort(key=lambda t: t[1])
    best = cands[0]
    ratio = cands[1][1] / max(best[1], 1e-300) if len(cands) > 1 else math.inf
    return {"thickness_nm": best[0], "rmse": best[1], "scale": best[2],
            "candidates": [(d, r) for d, r, _ in cands], "second_rmse_ratio": float(ratio),
            "grid_step_nm": float(step)}


def film_thickness_map(images, wavelengths_nm=(450.0, 500.0, 550.0, 600.0, 650.0, 700.0), film="SIO2",
                       substrate="SI", thickness_min_nm=0.0, thickness_max_nm=1500.0, mode="spectral",
                       under=(), ambiguity_rms=0.01, step_nm=1.0, normalize=False, chunk=4096):
    """分光画像(帯域ごとの反射率)か RGB 画像から、画素ごとの膜厚を出す(早見表 + 放物線の精密化)。

    images:          (B, H, W) の帯域画像の列。``mode="spectral"`` なら各帯域は ``wavelengths_nm`` の波長での
                     反射率(狭帯域の分光カメラ)、``mode="srgb"`` なら B = 3 で :func:`film_color` と同じ
                     線形 sRGB(D65・CIE 1931 の等色関数、Luther 条件を満たす理想の RGB カメラ)。
    wavelengths_nm:  分光モードの帯域の中心 [nm] (B 個、昇順)。srgb モードでは使わない。
    film / substrate / under: 積層(材料表の鍵)。最上層 ``film`` の厚さを求める。
    thickness_min_nm / thickness_max_nm / step_nm: 早見表の膜厚の範囲と刻み。
    ambiguity_rms:     「同じくらい合う候補」の閾: 画素の RMS 残差が最良 + この値以下の局所解を数える。
                     既定 0.01 は反射率 1 % の雑音の目安。
    normalize:       True なら画素と早見表をどちらも長さ 1 に揃えてから比べる(明るさ = 照明・露出・反射率の倍率が
                     分からないときに、色の向き(分光の形)だけで照合する)。rmse は長さ 1 の単位になる。
    chunk:           1 回に照合する画素の数(メモリの上限)。

    返り値 dict: thickness (H, W) / rmse (H, W) / n_candidates (H, W)(閾の中に入った局所解の数。
      ★1 より大きい画素は**色(帯域)だけでは膜厚が決まらない** —— RGB では色が膜厚について周期的に繰り返すので
      ここが 2 以上になる)/ lut_thickness_nm(早見表の膜厚)。
    """
    op = "film_thickness_map"
    cube = np.asarray(images, dtype=np.float64)
    if cube.ndim != 3 or cube.shape[0] < 1 or cube.shape[1] < 1 or cube.shape[2] < 1:
        raise ValueError("%s: images must be a (B, H, W) stack of band images, got shape %s" % (op, cube.shape))
    if not np.all(np.isfinite(cube)):
        raise ValueError("%s: images contain non-finite values" % op)
    if mode not in ("spectral", "srgb"):
        raise ValueError("%s: mode must be 'spectral' or 'srgb': got %r" % (op, mode))
    lo, hi, st = float(thickness_min_nm), float(thickness_max_nm), float(step_nm)
    if not (math.isfinite(lo) and math.isfinite(hi) and math.isfinite(st)) or lo < 0.0 or hi <= lo or st <= 0.0:
        raise ValueError("%s: need 0 <= thickness_min_nm < thickness_max_nm and step_nm > 0" % op)
    if (hi - lo) / st > 200000:
        raise ValueError("%s: too many look-up thicknesses (range / step > 200000)" % op)
    tol = _finite_nonneg(ambiguity_rms, "ambiguity_rms", op)
    ck = int(chunk)
    if ck < 1:
        raise ValueError("%s: chunk must be >= 1" % op)
    grid = np.arange(lo, hi + 0.5 * st, st)
    if mode == "spectral":
        lam = _wavelengths(wavelengths_nm, 0, 0, 0, op)
        if lam.size != cube.shape[0]:
            raise ValueError("%s: %d band images but %d wavelengths" % (op, cube.shape[0], lam.size))
        lut = _model_lut(lam, film, substrate, under, grid, 0.0, 0.0, 1.0, 0.0, op)          # (N, B)
    else:
        if cube.shape[0] != 3:
            raise ValueError("%s: mode='srgb' needs exactly 3 band images (linear R, G, B), got %d" % (op, cube.shape[0]))
        fc = film_color(film, substrate, lo, hi, grid.size, under=under)
        grid = fc["thickness_nm"]
        lut = fc["linear_srgb"]
    B, H, W = cube.shape
    px = cube.reshape(B, -1).T                                                                 # (P, B)
    if normalize:
        lut = lut / np.maximum(np.linalg.norm(lut, axis=1, keepdims=True), 1e-300)
        px = px / np.maximum(np.linalg.norm(px, axis=1, keepdims=True), 1e-300)
    lut2 = np.sum(lut * lut, axis=1)
    thick = np.empty(px.shape[0])
    rmse = np.empty(px.shape[0])
    ncand = np.empty(px.shape[0], dtype=np.int64)
    for s in range(0, px.shape[0], ck):
        p = px[s:s + ck]
        sse = np.maximum(np.sum(p * p, axis=1)[:, None] - 2.0 * p @ lut.T + lut2[None, :], 0.0)  # (P, N)
        rm = np.sqrt(sse / B)
        j = np.argmin(rm, axis=1)
        jj = np.clip(j, 1, grid.size - 2)
        a, b, c = rm[np.arange(j.size), jj - 1], rm[np.arange(j.size), jj], rm[np.arange(j.size), jj + 1]
        den = a - 2.0 * b + c
        off = np.where((den > 1e-300) & (j == jj), 0.5 * (a - c) / np.where(den > 1e-300, den, 1.0), 0.0)
        thick[s:s + ck] = grid[jj] + np.clip(off, -0.5, 0.5) * st if grid.size > 2 else grid[j]
        thick[s:s + ck] = np.where(j == jj, thick[s:s + ck], grid[j])
        best = rm[np.arange(j.size), j]
        rmse[s:s + ck] = best
        left = np.concatenate([np.full((rm.shape[0], 1), np.inf), rm[:, :-1]], axis=1)
        right = np.concatenate([rm[:, 1:], np.full((rm.shape[0], 1), np.inf)], axis=1)
        is_min = (rm <= left) & (rm < right)
        ncand[s:s + ck] = np.sum(is_min & (rm <= best[:, None] + tol), axis=1)
    return {"thickness": thick.reshape(H, W), "rmse": rmse.reshape(H, W), "n_candidates": ncand.reshape(H, W),
            "lut_thickness_nm": grid}
