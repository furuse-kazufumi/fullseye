# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""temsim — 仮想の透過電子顕微鏡(TEM): 位相コントラストの結像、コントラスト伝達関数(CTF)、焦点外れの推定と補正。

動機(2026-10-15、ユーザー「並行して電子顕微鏡とかも仮想的に作れるかな?」): 走査電子顕微鏡(SEM、``semsim``)は表面の
凹凸を 2 次電子で見る。透過電子顕微鏡は薄い試料を透けた電子の**位相**を、対物レンズの収差と焦点外れで強度に変えて見る
—— 光の位相差顕微鏡と同じ「瞳で位相を強度に変える」コヒーレント結像で、Fullseye の ``coherent.coherent_image`` が
そのまま使える。ここは電子の層(波長・相互作用定数・CTF・Thon リング)だけを持ち、結像の本体と散乱因子は既存の族を使う。

内容(10 op、長さは Å、加速電圧は kV、球面収差 Cs と色収差 Cc は mm、焦点外れは Å で **正 = アンダーフォーカス**):
  電子         `tem_wavelength`(相対論補正つきの波長と相互作用定数 σ)/ `tem_scherzer`(Scherzer 焦点と点分解能)
  伝達関数     `tem_ctf`(2-D、包絡つき)/ `tem_ctf_profile`(1-D の動径曲線と零点)
  試料         `tem_projected_potential`(原子の座標 → 投影ポテンシャル、Mott–Bethe で X 線の散乱因子から)/
               `tem_amorphous_film`(非晶質の膜、Thon リングの標準試料)
  結像         `tem_image_weak_phase`(弱位相物体の線形の像、または ``coherent_image`` の非線形の像。雑音と線量つき)/
               `tem_multislice`(簡易のマルチスライス、厚い試料で弱位相近似が崩れる所)
  推定と補正   `tem_power_spectrum`(タイルの平均のパワースペクトル)/ `tem_ctf_estimate`(Thon リングを当てはめて
               焦点外れと非点収差、不確かさ、決まらなければ拒否)/ `tem_ctf_correct`(位相反転 / ウィーナー)

規約(CTFFIND4 と RELION の規約に合わせた):
  χ(k) = π λ k² Δf(α) − (π/2) Cs λ³ k⁴ + Δφ、 CTF(k) = −sin(χ + arcsin w)(w = 振幅コントラストの割合)
  Δf(α) = ½ [Δf_u + Δf_v + (Δf_u − Δf_v) cos 2(α − θ_ast)]、 α は周波数の向き(+x = 列の向きから +y = 行の向きへ)。
  弱位相物体の像は I ≈ 1 + 2 F⁻¹[ Φ(k) · CTF(k) · E(k) ] / √(1 − w²)(Φ = σ v_z の Fourier 変換)。正のポテンシャル
  (原子)はアンダーフォーカスの低い周波数で**暗く**写る(CTF < 0)。
  包絡(Frank 1973 の準コヒーレント近似): 空間 E_s = exp[−(π α_ill/λ)² (Cs λ³ k³ − Δf λ k)²]、時間 E_t = exp[−½ (π λ δ)² k⁴]
  (α_ill = 照明の半角 rad、δ = 焦点の広がりの rms Å)。

再利用(作り直さない): 結像 = ``coherent.coherent_image``(瞳 = 開口 × e^{iχ} × 包絡)/ 原子の X 線散乱因子 =
``pxrd.FORM_FACTORS``(Waasmaier–Kirfel)を Mott–Bethe で電子へ / 周期の初期値 = ``mathspectral.lomb_scargle``
(動径の標本は k について等間隔なので k² について不等間隔 —— Thon リングは Cs を無視すると k² について周期 1/(λΔf))。

真値(外部): 波長の公表値(200 kV = 2.5079 pm、300 kV = 1.9687 pm)/ CTF の零点の閉形式 / Scherzer の点分解能
0.66 Cs^¼ λ^¾ / 正弦位相格子の回折 = J_n(φ₀)²(Raman–Nath)/ 中性原子の平均内部ポテンシャル(Si 約 13.8 V)。
来歴: Scherzer, J. Appl. Phys. 20, 20 (1949) / Thon, Z. Naturforsch. 21a, 476 (1966) / Frank, Optik 38, 519 (1973) /
Cowley & Moodie, Acta Cryst. 10, 609 (1957) / Kirkland, *Advanced Computing in Electron Microscopy* (2010) /
Rohou & Grigorieff, J. Struct. Biol. 192, 216 (2015)(CTFFIND4 の式だけを使い、コードは使わない)。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "tem_wavelength", "tem_scherzer", "tem_ctf", "tem_ctf_profile",
    "tem_projected_potential", "tem_amorphous_film", "tem_image_weak_phase", "tem_multislice",
    "tem_power_spectrum", "tem_ctf_estimate", "tem_ctf_correct",
]

# CODATA 2018(SI の定義値と推奨値)
_H = 6.62607015e-34            # J s
_M0 = 9.1093837015e-31         # kg
_E = 1.602176634e-19           # C
_C = 299792458.0               # m/s
#: h² / (2π m₀ e) [V Å²] —— 散乱因子 f_e [Å] を投影ポテンシャル [V Å] に変える定数(= 2π a₀ e、47.878)。
POTENTIAL_CONST = _H * _H / (2.0 * math.pi * _M0 * _E) * 1e20
#: Mott–Bethe の定数 1 / (8π² a₀) [Å⁻¹] (f_e = K (Z − f_x(s)) / s²、s = sinθ/λ [Å⁻¹])= 0.023934。
_A0_A = 0.529177210903
MOTT_BETHE_K = 1.0 / (8.0 * math.pi ** 2 * _A0_A)


# --------------------------------------------------------------------------- #
# 引数の検査(fail-closed)                                                       #
# --------------------------------------------------------------------------- #
def _num(v, name, op, lo=None, hi=None, lo_open=False, hi_open=False):
    if isinstance(v, bool):
        raise ValueError("%s: %s must be a number, got a bool" % (op, name))
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, v)) from None
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    if lo is not None and (x < lo or (lo_open and x == lo)):
        raise ValueError("%s: %s must be %s %g, got %r" % (op, name, ">" if lo_open else ">=", lo, v))
    if hi is not None and (x > hi or (hi_open and x == hi)):
        raise ValueError("%s: %s must be %s %g, got %r" % (op, name, "<" if hi_open else "<=", hi, v))
    return x


def _img(a, name, op, min_side=8):
    arr = np.asarray(a)
    if arr.dtype.kind not in "iufb" or arr.ndim != 2:
        raise ValueError("%s: %s must be a real 2-D array, got %s %s" % (op, name, arr.dtype, arr.shape))
    if min(arr.shape) < min_side:
        raise ValueError("%s: %s must be at least %d x %d, got %s" % (op, name, min_side, min_side, arr.shape))
    arr = arr.astype(np.float64)
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s has non-finite values" % (op, name))
    return arr


def _shape(shape, op, lo=8, hi=8192):
    try:
        ny, nx = (int(shape), int(shape)) if np.isscalar(shape) else (int(shape[0]), int(shape[1]))
    except (TypeError, ValueError, IndexError):
        raise ValueError("%s: shape must be an int or (ny, nx), got %r" % (op, shape)) from None
    if not (lo <= ny <= hi and lo <= nx <= hi):
        raise ValueError("%s: shape must be within [%d, %d] per side, got %r" % (op, lo, hi, shape))
    return ny, nx


def _seed(seed, op):
    if isinstance(seed, bool) or int(seed) != seed or seed < 0:
        raise ValueError("%s: seed must be a non-negative int, got %r" % (op, seed))
    return int(seed)


# --------------------------------------------------------------------------- #
# 1. 電子                                                                       #
# --------------------------------------------------------------------------- #
def _lam_sigma(kv):
    V = kv * 1e3
    eV = _E * V
    mc2 = _M0 * _C * _C
    lam_m = _H / math.sqrt(2.0 * _M0 * eV * (1.0 + eV / (2.0 * mc2)))
    gamma = 1.0 + eV / mc2
    sigma = 2.0 * math.pi * gamma * _M0 * _E * lam_m / (_H * _H) * 1e-10      # rad / (V Å)
    return lam_m * 1e10, sigma, gamma


def tem_wavelength(kv=300.0):
    """加速電圧 ``kv`` [kV] の電子の波長(相対論補正つき)と相互作用定数を表で返す。

    λ = h / √(2 m₀ e V (1 + eV / 2m₀c²))、σ = 2π γ m₀ e λ / h²(弱位相物体の位相 = σ × 投影ポテンシャル)。
    定数は CODATA 2018。公表値: 200 kV で 2.5079 pm、300 kV で 1.9687 pm(相対論補正を外すと 300 kV で 2.24 pm、
    14 % 長い —— 補正は省けない)。
    返り値: ``wavelength_A`` / ``wavelength_pm`` / ``sigma_rad_per_VA`` / ``gamma``(ローレンツ因子)/ ``beta``(v/c)/
    ``wavelength_nonrel_pm``。
    """
    op = "tem_wavelength"
    kv = _num(kv, "kv", op, lo=0.0, hi=5000.0, lo_open=True)
    lam, sigma, gamma = _lam_sigma(kv)
    nonrel = _H / math.sqrt(2.0 * _M0 * _E * kv * 1e3) * 1e12
    return {"kv": kv, "wavelength_A": lam, "wavelength_pm": lam * 100.0, "sigma_rad_per_VA": sigma,
            "gamma": gamma, "beta": math.sqrt(1.0 - 1.0 / (gamma * gamma)), "wavelength_nonrel_pm": nonrel}


def tem_scherzer(kv=300.0, cs_mm=2.7):
    """Scherzer 焦点と点分解能(表)。

    2 つの定義を並べて返す(本によって違うので、どちらで比べたかを残す):
      ``defocus_A``          = √(4/3 Cs λ)(古典の Scherzer 焦点、Williams & Carter / Reimer)
      ``defocus_extended_A`` = 1.2 √(Cs λ)(Kirkland などの「拡張 Scherzer」)
      ``point_resolution_A`` = その焦点での CTF の最初の零点の逆数(閉形式)。古典の焦点で 0.658 Cs^¼ λ^¾、拡張で 0.645 Cs^¼ λ^¾
      ``point_resolution_formula_A`` = 0.66 Cs^¼ λ^¾(教科書の丸めた式)
    正 = アンダーフォーカス。振幅コントラストは含めない(w = 0 の位相の CTF)。
    """
    op = "tem_scherzer"
    kv = _num(kv, "kv", op, lo=0.0, hi=5000.0, lo_open=True)
    cs = _num(cs_mm, "cs_mm", op, lo=0.0, lo_open=True, hi=100.0) * 1e7          # Å
    lam = _lam_sigma(kv)[0]
    df = math.sqrt(4.0 / 3.0 * cs * lam)
    dfe = 1.2 * math.sqrt(cs * lam)

    def first_zero(d):
        # χ = π λ Δf u − (π/2) Cs λ³ u² が 0 に戻る u(> 0)
        return 1.0 / math.sqrt(2.0 * d / (cs * lam * lam))
    return {"kv": kv, "cs_mm": cs * 1e-7, "wavelength_A": lam,
            "defocus_A": df, "defocus_extended_A": dfe,
            "point_resolution_A": first_zero(df), "point_resolution_extended_A": first_zero(dfe),
            "point_resolution_formula_A": 0.66 * cs ** 0.25 * lam ** 0.75}


# --------------------------------------------------------------------------- #
# 2. CTF                                                                        #
# --------------------------------------------------------------------------- #
def _ctf_args(op, kv, cs_mm, defocus_A, astig_A, astig_angle_deg, amplitude_contrast, phase_shift_deg,
              alpha_mrad, focal_spread_A):
    kv = _num(kv, "kv", op, lo=0.0, hi=5000.0, lo_open=True)
    cs = _num(cs_mm, "cs_mm", op, lo=0.0, hi=100.0) * 1e7
    df = _num(defocus_A, "defocus_A", op, lo=-1e6, hi=1e6)
    # 非点収差の大きさと向きは None = 無し(0)。向きは大きさが 0 なら効かないので、既定を数にしない
    # (台帳の探針は数の既定を持つノブを振って「効かないノブ」を数える)。
    ast = 0.0 if astig_A is None else _num(astig_A, "astig_A", op, lo=0.0, hi=1e5)
    ang = 0.0 if astig_angle_deg is None else math.radians(_num(astig_angle_deg, "astig_angle_deg", op, lo=-360.0, hi=360.0))
    w = _num(amplitude_contrast, "amplitude_contrast", op, lo=0.0, hi=1.0, hi_open=True)
    ps = math.radians(_num(phase_shift_deg, "phase_shift_deg", op, lo=-360.0, hi=360.0))
    a = _num(alpha_mrad, "alpha_mrad", op, lo=0.0, hi=100.0) * 1e-3
    fsp = _num(focal_spread_A, "focal_spread_A", op, lo=0.0, hi=1e5)
    return kv, cs, df, ast, ang, w, ps, a, fsp


def _chi(kx, ky, lam, cs, df_u, df_v, ang, ps):
    k2 = kx * kx + ky * ky
    c2, s2 = math.cos(2.0 * ang), math.sin(2.0 * ang)
    directional = np.empty_like(k2)
    np.divide((kx * kx - ky * ky) * c2 + 2.0 * kx * ky * s2, k2,
              out=directional, where=k2 != 0.0)
    directional[k2 == 0.0] = c2
    dfa = 0.5 * (df_u + df_v + (df_u - df_v) * directional)
    return math.pi * lam * k2 * dfa - 0.5 * math.pi * cs * lam ** 3 * k2 * k2 + ps, dfa


def _envelope(k, dfa, lam, cs, alpha, fsp):
    e = np.ones_like(k)
    if alpha > 0.0:
        e = e * np.exp(-(math.pi * alpha / lam) ** 2 * (cs * lam ** 3 * k ** 3 - dfa * lam * k) ** 2)
    if fsp > 0.0:
        e = e * np.exp(-0.5 * (math.pi * lam * fsp) ** 2 * k ** 4)
    return e


def _freq(ny, nx, pixel_A):
    ky = np.fft.fftfreq(ny, d=pixel_A)[:, None] * np.ones((1, nx))
    kx = np.fft.fftfreq(nx, d=pixel_A)[None, :] * np.ones((ny, 1))
    return kx, ky


def _ctf2d(ny, nx, pixel_A, kv, cs, df, ast, ang, w, ps, alpha, fsp, envelope=True):
    lam = _lam_sigma(kv)[0]
    kx, ky = _freq(ny, nx, pixel_A)
    chi, dfa = _chi(kx, ky, lam, cs, df + 0.5 * ast, df - 0.5 * ast, ang, ps)
    ctf = -np.sin(chi + math.asin(w))
    if envelope:
        ctf = ctf * _envelope(np.hypot(kx, ky), dfa, lam, cs, alpha, fsp)
    return ctf, chi


def tem_ctf(shape=256, pixel_A=1.0, kv=300.0, cs_mm=2.7, defocus_A=10000.0, astig_A=0.0, astig_angle_deg=None,
            amplitude_contrast=0.07, phase_shift_deg=0.0, alpha_mrad=0.0, focal_spread_A=0.0, envelope=True):
    """2-D のコントラスト伝達関数(DC が中央の ``fftshift`` 順、形 ``shape``)。

    CTF = −sin(χ + arcsin w) × E_s × E_t。``defocus_A`` は平均の焦点外れ(正 = アンダーフォーカス)、``astig_A`` は
    Δf_u − Δf_v(≥ 0)、``astig_angle_deg`` は Δf_u の軸の向き(+x から +y へ)。``alpha_mrad`` は照明の半角、
    ``focal_spread_A`` は焦点の広がりの rms(どちらも 0 で包絡なし)。``envelope=False`` で包絡を掛けない。
    パワースペクトルのリング(Thon リング)は CTF² の明暗。
    """
    op = "tem_ctf"
    ny, nx = _shape(shape, op)
    px = _num(pixel_A, "pixel_A", op, lo=0.0, lo_open=True, hi=1e4)
    args = _ctf_args(op, kv, cs_mm, defocus_A, astig_A, astig_angle_deg, amplitude_contrast, phase_shift_deg,
                     alpha_mrad, focal_spread_A)
    ctf, _ = _ctf2d(ny, nx, px, *args, envelope=bool(envelope))
    return np.fft.fftshift(ctf)


def _zeros_closed_form(lam, cs, df, w, ps, k_max):
    """χ + arcsin w = nπ を満たす k(閉形式、Cs > 0 は 2 次方程式の小さい根、Cs = 0 は 1 次)。"""
    out = []
    off = math.asin(w) + ps
    for n in range(-2000, 2001):
        c = n * math.pi - off                     # π λ Δf u − (π/2) Cs λ³ u² = c
        if cs > 0.0:
            a2 = 0.5 * math.pi * cs * lam ** 3
            b = math.pi * lam * df
            disc = b * b - 4.0 * a2 * c
            if disc < 0.0:
                continue
            for u in ((b - math.sqrt(disc)) / (2.0 * a2), (b + math.sqrt(disc)) / (2.0 * a2)):
                if u > 0.0 and math.sqrt(u) <= k_max:
                    out.append(math.sqrt(u))
        elif df != 0.0:
            u = c / (math.pi * lam * df)
            if u > 0.0 and math.sqrt(u) <= k_max:
                out.append(math.sqrt(u))
    return sorted(set(round(z, 15) for z in out))


def tem_ctf_profile(k_max=0.5, n_points=1000, kv=300.0, cs_mm=2.7, defocus_A=10000.0, amplitude_contrast=0.07,
                    phase_shift_deg=0.0, alpha_mrad=0.0, focal_spread_A=0.0):
    """1-D の動径の CTF 曲線(包絡つき)と零点の表。

    返り値: ``k``(Å⁻¹、0〜k_max)/ ``ctf``(包絡なし)/ ``ctf_env``(E_s E_t 込み)/ ``envelope_spatial`` /
    ``envelope_temporal`` / ``zeros_A_inv``(閉形式の零点、χ + arcsin w = nπ を解いた k)/ ``information_limit_A``
    (時間包絡が e⁻² になる周波数の逆数、焦点の広がりが 0 なら None)。非点収差の無い動径(Δf 一定)。
    """
    op = "tem_ctf_profile"
    km = _num(k_max, "k_max", op, lo=0.0, lo_open=True, hi=100.0)
    n = int(_num(n_points, "n_points", op, lo=8, hi=1_000_000))
    kv, cs, df, _, _, w, ps, a, fsp = _ctf_args(op, kv, cs_mm, defocus_A, 0.0, 0.0, amplitude_contrast,
                                                phase_shift_deg, alpha_mrad, focal_spread_A)
    lam = _lam_sigma(kv)[0]
    k = np.linspace(0.0, km, n)
    chi = math.pi * lam * df * k * k - 0.5 * math.pi * cs * lam ** 3 * k ** 4 + ps
    ctf = -np.sin(chi + math.asin(w))
    es = _envelope(k, df, lam, cs, a, 0.0)
    et = _envelope(k, df, lam, cs, 0.0, fsp)
    info = None
    if fsp > 0.0:
        info = math.sqrt(0.5 * math.pi * lam * fsp)          # E_t = e^-2 → k⁴ = 4 / (π λ δ)² → d = √(π λ δ / 2)
    return {"k": k, "ctf": ctf, "ctf_env": ctf * es * et, "envelope_spatial": es, "envelope_temporal": et,
            "zeros_A_inv": _zeros_closed_form(lam, cs, df, w, ps, km), "information_limit_A": info,
            "wavelength_A": lam}


# --------------------------------------------------------------------------- #
# 3. 試料: 投影ポテンシャル                                                      #
# --------------------------------------------------------------------------- #
def _electron_form_factor(element, s):
    """電子の原子散乱因子 f_e(s) [Å] (Mott–Bethe、``pxrd.FORM_FACTORS`` の X 線の因子から)。s = sinθ/λ [Å⁻¹]。

    f_e = K (Z_fit − f_x(s)) / s² = K Σ a_i (1 − e^{−b_i s²}) / s²。Z_fit = Σ a_i + c は表の当てはめの全電子数で、
    Z と 1e-2 以下違う(Z で書くと s → 0 で発散する)。f_e(0) = K Σ a_i b_i。内部の関数(台帳 op ではない)。
    """
    import pxrd
    if element not in pxrd.FORM_FACTORS:
        raise ValueError("no X-ray form factor for %r in pxrd.FORM_FACTORS (known: %s)"
                         % (element, ", ".join(sorted(pxrd.FORM_FACTORS))))
    c = pxrd.FORM_FACTORS[element][1]
    s2 = np.asarray(s, dtype=np.float64) ** 2
    out = np.zeros_like(s2)
    small = s2 < 1e-10
    for i in range(5):
        a, b = c[i], c[6 + i]
        with np.errstate(divide="ignore", invalid="ignore"):
            term = np.where(small, a * b, a * (-np.expm1(-b * s2)) / np.where(small, 1.0, s2))
        out = out + term
    return MOTT_BETHE_K * out


def _check_atoms(atoms, elements, op):
    P = np.asarray(atoms, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] not in (2, 3) or P.shape[0] < 1:
        raise ValueError("%s: atoms must be (N, 2) or (N, 3) positions in Å, got %s" % (op, P.shape))
    if not np.isfinite(P).all():
        raise ValueError("%s: atoms has non-finite positions" % op)
    if isinstance(elements, str):
        el = [elements] * P.shape[0]
    else:
        el = list(elements)
        if len(el) != P.shape[0]:
            raise ValueError("%s: elements has %d entries for %d atoms" % (op, len(el), P.shape[0]))
    return P[:, :2], el


def _splat(xy, ny, nx, pixel_A):
    """双線形の重みで原子を格子へ置く(周期境界)。Fourier 側では sinc² を割り戻す。"""
    g = np.zeros((ny, nx))
    fx = xy[:, 0] / pixel_A
    fy = xy[:, 1] / pixel_A
    x0 = np.floor(fx).astype(np.int64)
    y0 = np.floor(fy).astype(np.int64)
    tx = fx - x0
    ty = fy - y0
    for dy, wy in ((0, 1.0 - ty), (1, ty)):
        for dx, wx in ((0, 1.0 - tx), (1, tx)):
            np.add.at(g, ((y0 + dy) % ny, (x0 + dx) % nx), wy * wx)
    return g


def tem_projected_potential(atoms, elements="C", shape=256, pixel_A=0.5):
    """原子の座標 → z 方向に投影したポテンシャル v_z(x, y) [V Å] (周期境界、``image2d``)。

    ``atoms`` は (N, 2) か (N, 3) の Å の座標(z は捨てる)、``elements`` は元素名 1 つか N 個の列
    (``pxrd.FORM_FACTORS`` にあるもの: C, O, Si, Al, Mg, Cu, Fe … ── 無いものは ValueError)。
    v_z = (h² / 2π m₀ e) F⁻¹[ f_e(q/2) S(q) ] / 画素の面積、S は原子の構造因子。原子は双線形の重みで格子に置き、
    その伝達(sinc²)を Fourier 側で割り戻す。1 個の原子の v_z の積分は 47.878 × f_e(0) [V Å³]。
    弱位相物体の位相は ``σ × v_z``(``tem_wavelength`` の ``sigma_rad_per_VA``)。
    """
    op = "tem_projected_potential"
    ny, nx = _shape(shape, op)
    px = _num(pixel_A, "pixel_A", op, lo=0.01, hi=100.0)
    xy, el = _check_atoms(atoms, elements, op)
    kx, ky = _freq(ny, nx, px)
    q = np.hypot(kx, ky)
    # 双線形の置き方の伝達(各軸の sinc²)。Nyquist で 0.405 なので割り戻しても発散しない。
    T = (np.sinc(kx * px) ** 2) * (np.sinc(ky * px) ** 2)
    out = np.zeros((ny, nx), dtype=np.complex128)
    element_codes = np.asarray(el)
    groups = {name: np.flatnonzero(element_codes == name) for name in sorted(set(el))}
    for name, idx in groups.items():
        fe = _electron_form_factor(name, q / 2.0)
        out += np.fft.fft2(_splat(xy[idx], ny, nx, px)) * fe / T
    return POTENTIAL_CONST * np.fft.ifft2(out).real / (px * px)


def tem_amorphous_film(shape=256, pixel_A=1.0, thickness_A=100.0, density_g_cm3=2.0, element="C", seed=0,
                       min_distance_A=1.2):
    """非晶質の膜の投影ポテンシャル [V Å] (Thon リングの標準試料、``image2d``)。

    原子を一様乱数で置き(最近接距離 ``min_distance_A`` 未満の対は間引く = ハードコアの近似)、
    ``tem_projected_potential`` で投影する。数密度 = ρ N_A / M(炭素 2.0 g/cm³ で 0.100 Å⁻³)。
    厚さ 100 Å・1 Å/画素の 256² で約 6.6 万原子。``seed`` で決まる(同じ seed は同じ膜)。
    """
    import pxrd
    op = "tem_amorphous_film"
    ny, nx = _shape(shape, op, hi=2048)
    px = _num(pixel_A, "pixel_A", op, lo=0.05, hi=20.0)
    t = _num(thickness_A, "thickness_A", op, lo=0.0, lo_open=True, hi=5000.0)
    rho = _num(density_g_cm3, "density_g_cm3", op, lo=0.0, lo_open=True, hi=25.0)
    dmin = _num(min_distance_A, "min_distance_A", op, lo=0.0, hi=5.0)
    rs = _seed(seed, op)
    if element not in pxrd.ATOMIC_MASS:
        raise ValueError("%s: element %r has no atomic mass in pxrd.ATOMIC_MASS" % (op, element))
    n_density = rho / pxrd.ATOMIC_MASS[element] * 6.02214076e23 * 1e-24          # Å⁻³
    Lx, Ly = nx * px, ny * px
    n = int(round(n_density * Lx * Ly * t))
    if n > 20_000_000:
        raise ValueError("%s: %d atoms is too many (reduce shape, thickness or density)" % (op, n))
    rng = np.random.default_rng(rs)
    P = rng.random((n, 3)) * np.array([Lx, Ly, t])
    if dmin > 0.0 and n > 1:
        from scipy.spatial import cKDTree
        tree = cKDTree(P, boxsize=[Lx, Ly, t * 1e6])
        pairs = tree.query_pairs(dmin, output_type="ndarray")
        keep = np.ones(n, dtype=bool)
        keep[pairs[:, 1]] = False
        P = P[keep]
    return tem_projected_potential(P, element, (ny, nx), px)


# --------------------------------------------------------------------------- #
# 4. 結像                                                                       #
# --------------------------------------------------------------------------- #
def tem_image_weak_phase(potential, pixel_A=1.0, kv=300.0, cs_mm=2.7, defocus_A=10000.0, astig_A=0.0,
                         astig_angle_deg=None, amplitude_contrast=0.07, phase_shift_deg=0.0, alpha_mrad=0.0,
                         focal_spread_A=0.0, aperture_A_inv=None, mode="linear", dose_e_per_A2=None, seed=0):
    """投影ポテンシャル v_z [V Å] から TEM の明視野像(平均 1 の強度、``image2d``)。

    ``mode="linear"``: 弱位相物体近似 I = 1 + 2 F⁻¹[ F(σ v_z) · CTF · E ] / √(1 − w²)(位相が 1 rad より十分小さいとき)。
    ``mode="coherent"``: 透過関数 exp(iσ v_z − a σ v_z)(a = w / √(1 − w²))を ``coherent.coherent_image`` に
    瞳 = 開口 × e^{iχ} × 包絡(準コヒーレント)で渡す —— 位相が大きいと線形の像からずれる(その差が弱位相近似の誤差)。
    ``aperture_A_inv`` は対物絞りの半径 [Å⁻¹] (None = 無し)。``dose_e_per_A2`` を与えると画素あたり
    dose × 画素面積 の電子の Poisson 雑音を足し、平均 1 に戻して返す(``seed`` で決まる)。
    """
    op = "tem_image_weak_phase"
    v = _img(potential, "potential", op)
    ny, nx = v.shape
    px = _num(pixel_A, "pixel_A", op, lo=0.01, hi=1e4)
    kv_, cs, df, ast, ang, w, ps, a, fsp = _ctf_args(op, kv, cs_mm, defocus_A, astig_A, astig_angle_deg,
                                                     amplitude_contrast, phase_shift_deg, alpha_mrad, focal_spread_A)
    if mode not in ("linear", "coherent"):
        raise ValueError("%s: mode must be 'linear' or 'coherent', got %r" % (op, mode))
    lam, sigma, _ = _lam_sigma(kv_)
    phi = sigma * v
    kx, ky = _freq(ny, nx, px)
    k = np.hypot(kx, ky)
    ap = np.ones_like(k)
    if aperture_A_inv is not None:
        r = _num(aperture_A_inv, "aperture_A_inv", op, lo=0.0, lo_open=True, hi=1e3)
        ap = (k <= r).astype(np.float64)
    chi, dfa = _chi(kx, ky, lam, cs, df + 0.5 * ast, df - 0.5 * ast, ang, ps)
    env = _envelope(k, dfa, lam, cs, a, fsp)
    if mode == "linear":
        ctf = -np.sin(chi + math.asin(w)) * env * ap
        I = 1.0 + 2.0 * np.fft.ifft2(np.fft.fft2(phi) * ctf).real / math.sqrt(1.0 - w * w)
    else:
        import coherent
        amp_ratio = w / math.sqrt(1.0 - w * w)
        pupil = np.fft.fftshift(ap * env * np.exp(1j * chi))
        I = coherent.coherent_image(np.exp(-amp_ratio * phi), phase=phi, pupil=pupil)
    if dose_e_per_A2 is not None:
        d = _num(dose_e_per_A2, "dose_e_per_A2", op, lo=0.0, lo_open=True, hi=1e9)
        n_e = d * px * px
        rng = np.random.default_rng(_seed(seed, op))
        I = rng.poisson(np.clip(I, 0.0, None) * n_e).astype(np.float64) / n_e
    return I


def tem_multislice(slices, pixel_A=0.5, kv=300.0, slice_thickness_A=2.0, bandlimit=2.0 / 3.0):
    """簡易のマルチスライス(Cowley–Moodie、Kirkland の形): 出射波を返す(表)。

    ``slices`` = (n_slices, ny, nx) の各スライスの投影ポテンシャル [V Å] (2-D なら 1 枚)。
    ψ_{n+1} = F⁻¹[ P(k) F[ t_n ψ_n ] ]、t_n = exp(iσ v_n)、P = exp(−iπ λ Δz k²)(Fresnel の伝播)、
    透過関数と伝播関数は ``bandlimit`` × Nyquist で切る(2/3 = 掛け算のエイリアスを避ける Kirkland の規則)。
    返り値: ``exit_wave``(複素)/ ``intensity``(|ψ|²)/ ``total_intensity``(帯域で切った分だけ 1 より小さい)/
    ``projection_wave``(全スライスを足した 1 枚の位相物体 exp(iσ Σ v) —— 薄い極限の比較用)。
    像にするには出射波を ``coherent.coherent_image`` か ``tem_ctf`` の瞳に通す。
    """
    op = "tem_multislice"
    S = np.asarray(slices)
    if S.ndim == 2:
        S = S[None]
    if S.ndim != 3 or S.dtype.kind not in "iuf" or min(S.shape[1:]) < 8 or S.shape[0] < 1:
        raise ValueError("%s: slices must be a real (n, ny, nx) array with ny, nx >= 8, got %s %s"
                         % (op, S.dtype, S.shape))
    if not np.isfinite(S).all():
        raise ValueError("%s: slices has non-finite values" % op)
    px = _num(pixel_A, "pixel_A", op, lo=0.01, hi=100.0)
    kv = _num(kv, "kv", op, lo=0.0, hi=5000.0, lo_open=True)
    dz = _num(slice_thickness_A, "slice_thickness_A", op, lo=0.0, hi=1e5)
    bl = _num(bandlimit, "bandlimit", op, lo=0.0, lo_open=True, hi=1.0)
    lam, sigma, _ = _lam_sigma(kv)
    _, ny, nx = S.shape
    kx, ky = _freq(ny, nx, px)
    k2 = kx * kx + ky * ky
    kmax = bl * 0.5 / px
    mask = (k2 <= kmax * kmax).astype(np.float64)
    P = np.exp(-1j * math.pi * lam * dz * k2) * mask
    psi = np.ones((ny, nx), dtype=np.complex128)
    projected = np.zeros((ny, nx), dtype=np.float64)
    for v in S:
        v = np.asarray(v, dtype=np.float64)
        projected += v
        t = np.fft.ifft2(np.fft.fft2(np.exp(1j * sigma * v)) * mask)
        psi = np.fft.ifft2(np.fft.fft2(t * psi) * P)
    proj = np.fft.ifft2(np.fft.fft2(np.exp(1j * sigma * projected)) * mask)
    inten = psi.real ** 2 + psi.imag ** 2
    return {"exit_wave": psi, "intensity": inten, "total_intensity": float(inten.mean()),
            "projection_wave": proj, "wavelength_A": lam, "sigma_rad_per_VA": sigma,
            "thickness_A": dz * S.shape[0]}


# --------------------------------------------------------------------------- #
# 5. パワースペクトルと CTF の推定                                               #
# --------------------------------------------------------------------------- #
def _tiles(img, tile, overlap):
    ny, nx = img.shape
    step = max(1, int(round(tile * (1.0 - overlap))))
    ys = list(range(0, ny - tile + 1, step))
    xs = list(range(0, nx - tile + 1, step))
    return [(y, x) for y in ys for x in xs]


def _tile_spectra(img, tile, overlap):
    win = np.outer(np.hanning(tile), np.hanning(tile))
    out = []
    for (y, x) in _tiles(img, tile, overlap):
        t = img[y:y + tile, x:x + tile]
        t = (t - t.mean()) * win
        F = np.fft.fft2(t)
        out.append(F.real ** 2 + F.imag ** 2)
    return out


def _auto_tile(shape, tile):
    if tile is not None:
        return tile
    # 平均するタイルが少ないと 2-D のスペクトルが粗く、非点収差の当てはめが別の谷に落ちる(1024² で 512 のタイル
    # 9 枚のとき 25000 Å・非点 1500 Å を 25862 Å・28° と取り違えて拒否された、2026-10-15)。そこでタイルが
    # 短辺に 3 枚入るまで小さくする(256 が下限、それより小さい像は短辺の半分)。
    m = min(shape)
    t = 512
    while t > 256 and m < 3 * t:
        t //= 2
    while t > 16 and t > m // 2:
        t //= 2
    return t


def tem_power_spectrum(image, tile=None, overlap=0.5):
    """タイルに切った periodogram の平均(Welch、Hann 窓)を ``fftshift`` 順の 2-D で返す(``image2d``)。

    ``tile`` は正方のタイルの辺(既定: 短辺に 3 枚入る 512 か 256、小さい像は短辺の半分以下の 2 の冪)、``overlap`` はタイルの重なり(0〜0.9)。
    Thon リングは雑音の多い 1 枚の periodogram では見えにくく、タイルを平均すると見える。
    """
    op = "tem_power_spectrum"
    img = _img(image, "image", op, min_side=16)
    t = int(_num(_auto_tile(img.shape, tile), "tile", op, lo=16, hi=min(img.shape)))
    ov = _num(overlap, "overlap", op, lo=0.0, hi=0.9)
    spectra = _tile_spectra(img, t, ov)
    total = spectra[0].copy()
    for spectrum in spectra[1:]:
        total += spectrum
    return np.fft.fftshift(total / len(spectra))


def _radial(ps_unshift, pixel_A, k_lo, k_hi, nbins):
    n = ps_unshift.shape[0]
    kx, ky = _freq(n, n, pixel_A)
    k = np.hypot(kx, ky)
    edges = np.linspace(k_lo, k_hi, nbins + 1)
    idx = np.digitize(k.ravel(), edges) - 1
    ok = (idx >= 0) & (idx < nbins)
    cnt = np.bincount(idx[ok], minlength=nbins)
    s = np.bincount(idx[ok], ps_unshift.ravel()[ok], minlength=nbins)
    centres = 0.5 * (edges[1:] + edges[:-1])
    with np.errstate(invalid="ignore", divide="ignore"):
        prof = s / cnt
    good = cnt > 0
    return centres[good], prof[good]


def _smooth_u(u, y, width_u):
    """u(= k²)の上で幅 ``width_u`` の移動平均(不等間隔の標本を一様な格子に写して箱を掛け、戻す)。"""
    if width_u <= 0 or u.size < 4:
        return y.copy()
    grid = np.linspace(u[0], u[-1], max(64, 8 * u.size))
    yg = np.interp(grid, u, y)
    du = grid[1] - grid[0]
    n = max(1, int(round(width_u / du)))
    if n >= grid.size:
        return np.full_like(y, yg.mean())
    ker = np.ones(n) / n
    pad = np.concatenate([yg[n - 1:0:-1], yg, yg[-2:-n - 1:-1]]) if n > 1 else yg
    sm = np.convolve(pad, ker, mode="same")[n - 1:n - 1 + grid.size] if n > 1 else yg
    return np.interp(u, grid, sm)


def _background(k, amp, lam, df_guess):
    """背景(リングを均した曲線)と、局所の振れ幅で割った平坦な信号。幅はリングの周期 1/(λΔf) の 1 個分(u 上)。"""
    u = k * k
    period = 1.0 / (lam * max(df_guess, 1.0))
    bg = _smooth_u(u, amp, period)
    d = amp - bg
    rms = np.sqrt(np.maximum(_smooth_u(u, d * d, 2.0 * period), 1e-300))
    return bg, d / rms


def _model_1d(k, lam, cs, df, w, ps):
    chi = math.pi * lam * df * k * k - 0.5 * math.pi * cs * lam ** 3 * k ** 4 + ps
    return np.sin(chi + math.asin(w)) ** 2


def _ncc(a, b):
    a = a - a.mean()
    b = b - b.mean()
    den = math.sqrt(float(np.dot(a, a) * np.dot(b, b)))
    return float(np.dot(a, b) / den) if den > 0 else 0.0


def _lomb_guess(k, amp, lam, cs, df_lo, df_hi):
    """k² について周期 1/(λΔf) の振動を Lomb–Scargle(``mathspectral``)で探し、Δf の初期値にする。

    Cs の項は k⁴ なので、u = k² − Cs λ² k⁴ / (2Δf) と曲がる —— 初期値としては k² の周期で足りる(後で全模型で詰める)。
    """
    import mathspectral
    u = k * k
    # 低次の多項式で背景を外してから
    A = np.vander(u / u.max(), 5)
    coef, *_ = np.linalg.lstsq(A, amp, rcond=None)
    y = amp - A @ coef
    freqs = np.linspace(lam * df_lo, lam * df_hi, 600)
    ls = mathspectral.lomb_scargle(u, y, freqs)
    return ls["peak_freq"] / lam, ls


def _fit_1d(k, flat, lam, cs, w, ps, df_lo, df_hi, k_max):
    step = 1.0 / (8.0 * lam * k_max * k_max)
    grid = np.arange(df_lo, df_hi + step, step)
    scores = np.array([_ncc(flat, _model_1d(k, lam, cs, d, w, ps)) for d in grid])
    i = int(np.argmax(np.round(scores, 12)))
    from scipy.optimize import minimize_scalar
    lo, hi = grid[max(0, i - 2)], grid[min(grid.size - 1, i + 2)]
    r = minimize_scalar(lambda d: -_ncc(flat, _model_1d(k, lam, cs, d, w, ps)), bounds=(lo, hi), method="bounded",
                        options={"xatol": 0.05})
    return float(r.x), float(-r.fun), grid, scores


def _annulus(n, pixel_A, k_lo, k_hi, stride):
    kx, ky = _freq(n, n, pixel_A)
    k = np.hypot(kx, ky)
    m = (k >= k_lo) & (k <= k_hi)
    # 半平面だけ使う(パワースペクトルは原点対称)
    m &= (ky > 0) | ((ky == 0) & (kx > 0))
    if stride > 1:
        sub = np.zeros_like(m)
        sub[::stride, ::stride] = True
        m &= sub
    return kx[m], ky[m], m


def tem_ctf_estimate(image, pixel_A=1.0, kv=300.0, cs_mm=2.7, amplitude_contrast=0.07, phase_shift_deg=0.0,
                     defocus_min_A=3000.0, defocus_max_A=50000.0, k_min=1.0 / 30.0, k_max=None, tile=None,
                     overlap=0.5, astigmatism=True, min_rings=3, min_peak_z=8.0, on_fail="raise"):
    """顕微鏡写真のパワースペクトルの Thon リングから焦点外れ(と非点収差)を推定する(表)。

    手順: (1) タイルの平均のパワースペクトル(``tem_power_spectrum`` と同じ)→ 振幅スペクトル √PS。
    (2) 動径平均を k について等間隔に取り、k² について不等間隔の標本に Lomb–Scargle(``mathspectral``)を掛けて
    リングの周期 1/(λΔf) から初期値。(3) 背景 = u = k² の上でリング 1 周期の移動平均、振れ幅で割って平坦にする。
    (4) Δf を格子で掃き(位相が k_max で π/8 ずつ動く刻み)、CTF² との正規化相互相関(CTFFIND4 の採点の考え方)が
    最大の所を有界の 1 次元探索で詰める。(5) ``astigmatism=True`` なら 2-D の環の上で (Δf_u, Δf_v, θ) を Nelder–Mead で
    詰める(決まった 4 方向から出発、乱数なし)。(6) 不確かさ = タイルを 8 組に分けた jackknife の標準誤差(Δf の平均)。

    **拒否**(``on_fail="raise"`` で ValueError、``"report"`` で ``accepted=False`` の表): 相関の最大が掃いた格子の
    中央値から MAD の ``min_peak_z`` 倍に届かない(リングが雑音に埋もれた)、帯域 [k_min, k_max] に零点が
    ``min_rings`` 個無い(周期が決まらない)、最大が探索範囲の端(範囲の外にある疑い)。
    返り値: ``defocus_A``(平均)/ ``defocus_u_A`` ≥ ``defocus_v_A`` / ``astig_angle_deg``(Δf_u の軸、0〜180)/
    ``defocus_sigma_A``(jackknife)/ ``score``(2-D の相関)/ ``score_1d`` / ``peak_z`` / ``n_rings`` /
    ``fit_resolution_A``(局所の相関が 0.3 を下回る最初の周波数の逆数)/ ``initial_lomb_A`` / ``accepted`` / ``reason`` /
    曲線 ``k`` と ``flat``(平坦にした動径平均)と ``model``。
    """
    op = "tem_ctf_estimate"
    img = _img(image, "image", op, min_side=64)
    px = _num(pixel_A, "pixel_A", op, lo=0.01, hi=1e4)
    kv = _num(kv, "kv", op, lo=0.0, hi=5000.0, lo_open=True)
    cs = _num(cs_mm, "cs_mm", op, lo=0.0, hi=100.0) * 1e7
    w = _num(amplitude_contrast, "amplitude_contrast", op, lo=0.0, hi=1.0, hi_open=True)
    ps = math.radians(_num(phase_shift_deg, "phase_shift_deg", op, lo=-360.0, hi=360.0))
    dlo = _num(defocus_min_A, "defocus_min_A", op, lo=0.0, lo_open=True, hi=1e6)
    dhi = _num(defocus_max_A, "defocus_max_A", op, lo=0.0, lo_open=True, hi=1e6)
    if dhi <= dlo:
        raise ValueError("%s: need defocus_min_A < defocus_max_A, got %g and %g" % (op, dlo, dhi))
    nyq = 0.5 / px
    klo = _num(k_min, "k_min", op, lo=0.0, lo_open=True, hi=nyq)
    khi = _num(min(0.25, 0.9 * nyq) if k_max is None else k_max, "k_max", op, lo=0.0, lo_open=True, hi=nyq)
    if khi <= klo:
        raise ValueError("%s: need k_min < k_max <= Nyquist (%g), got %g and %g" % (op, nyq, klo, khi))
    if on_fail not in ("raise", "report"):
        raise ValueError("%s: on_fail must be 'raise' or 'report', got %r" % (op, on_fail))
    nr = int(_num(min_rings, "min_rings", op, lo=1, hi=1000))
    zmin = _num(min_peak_z, "min_peak_z", op, lo=0.0, hi=1e6)
    t = int(_num(_auto_tile(img.shape, tile), "tile", op, lo=32, hi=min(img.shape)))
    ov = _num(overlap, "overlap", op, lo=0.0, hi=0.9)
    lam = _lam_sigma(kv)[0]

    spectra = _tile_spectra(img, t, ov)
    amp2d = np.sqrt(np.mean(spectra, axis=0))
    k_req = khi
    for _round in range(2):
        nb = max(32, int((khi - klo) * t * px * 2))
        k, prof = _radial(amp2d, px, klo, khi, nb)
        if k.size < 16:
            raise ValueError("%s: only %d radial samples in [k_min, k_max]; use a larger tile or wider band" % (op, k.size))
        df0, _ls = _lomb_guess(k, prof, lam, cs, dlo, dhi)
        _, flat = _background(k, prof, lam, df0)
        df1, s1, grid, scores = _fit_1d(k, flat, lam, cs, w, ps, dlo, dhi, khi)
        # 背景の幅を推定した Δf で作り直して、もう 1 回
        _, flat = _background(k, prof, lam, df1)
        df1, s1, grid, scores = _fit_1d(k, flat, lam, cs, w, ps, dlo, dhi, khi)
        # リングの間隔 1/(2 λ Δf k) がタイルの周波数の刻み 1/(t px) の 4 倍を割る所から先は、窓で均されて見えない
        # (Hann 窓のスペクトルの幅は 2 刻み)。そこで帯域の上端を下げて 1 回だけやり直す。
        k_alias = t * px / (4.0 * lam * df1 * 1.15)
        if k_alias >= khi or k_alias <= 2.0 * klo:
            break
        khi = k_alias
    med = float(np.median(scores))
    mad = float(np.median(np.abs(scores - med))) * 1.4826
    z1 = (s1 - med) / mad if mad > 0 else float("inf")
    step = grid[1] - grid[0]

    # 2-D: 振幅スペクトルから背景(動径)を引き、振れ幅で割った環の上の観測
    stride = max(1, t // 256)
    kxs, kys, m = _annulus(t, px, klo, khi, stride)
    kk = np.hypot(kxs, kys)
    alpha = np.arctan2(kys, kxs)
    k2 = kk * kk

    def observe(a2d):
        kr, pr = _radial(a2d, px, klo, khi, nb)
        bg, _ = _background(kr, pr, lam, df1)
        d1 = pr - bg
        rms = np.sqrt(np.maximum(_smooth_u(kr * kr, d1 * d1, 2.0 / (lam * df1)), 1e-300))
        return (a2d[m] - np.interp(kk, kr, bg)) / np.interp(kk, kr, rms)

    def score2(p, obs):
        mean, half, ang = p
        dfa = mean + half * np.cos(2.0 * (alpha - ang))
        chi = math.pi * lam * k2 * dfa - 0.5 * math.pi * cs * lam ** 3 * k2 * k2 + ps
        return _ncc(obs, np.sin(chi + math.asin(w)) ** 2)

    from scipy.optimize import minimize

    def refine(obs, starts, h0):
        best = None
        for (d0, a0) in starts:
            simplex = [[d0, h0, a0], [d0 + 0.3 * h0, h0, a0], [d0, 2.0 * h0, a0], [d0, h0, a0 + 0.3]]
            r = minimize(lambda p: -score2(p, obs), x0=simplex[0], method="Nelder-Mead",
                         options={"xatol": 0.5, "fatol": 1e-10, "maxiter": 4000, "initial_simplex": simplex})
            if best is None or round(r.fun, 12) < round(best.fun, 12):
                best = r
        mean, half, ang = best.x
        if half < 0:
            half, ang = -half, ang + 0.5 * math.pi
        return float(mean), float(half), float(ang % math.pi), float(-best.fun)

    obs0 = observe(amp2d)
    h0 = max(100.0, 0.01 * df1)
    if astigmatism:
        # 出発点: 1-D の相関の山の上位 3 つ(丸めた値で比べ、同点は格子の順)× 4 方向
        peaks = [i for i in range(1, scores.size - 1) if scores[i] >= scores[i - 1] and scores[i] >= scores[i + 1]]
        peaks = sorted(peaks, key=lambda i: (-round(float(scores[i]), 9), i))[:3] or [int(np.argmax(scores))]
        cands = [df1] + [float(grid[i]) for i in peaks if abs(float(grid[i]) - df1) > 2 * step]
        starts = [(d0, a0) for d0 in cands for a0 in (0.0, 0.25 * math.pi, 0.5 * math.pi, 0.75 * math.pi)]
        mean, half, ang, s2 = refine(obs0, starts, h0)
        scan = np.array([score2((g, half, ang), obs0) for g in grid])
    else:
        mean, half, ang = df1, 0.0, 0.0
        s2 = score2((mean, 0.0, 0.0), obs0)
        scan = scores
    med2 = float(np.median(scan))
    mad2 = float(np.median(np.abs(scan - med2))) * 1.4826
    peak_z = ((s2 if astigmatism else s1) - med2) / mad2 if mad2 > 0 else float("inf")
    du, dv, th = mean + half, mean - half, math.degrees(ang) % 180.0

    zeros = [z for z in _zeros_closed_form(lam, cs, mean, w, ps, khi) if z >= klo]
    reasons = []
    if peak_z < zmin:
        reasons.append("rings not visible: correlation peak %.1f MAD above the median (need %.1f)" % (peak_z, zmin))
    if len(zeros) < nr:
        reasons.append("only %d CTF zeros in [k_min, k_max] (need %d)" % (len(zeros), nr))
    if dv <= dlo + step or du >= dhi - step:
        reasons.append("defocus %.0f..%.0f Å touches the edge of the search range [%.0f, %.0f]" % (dv, du, dlo, dhi))

    # 当てはまりの分解能: 環を k で区切り、区画ごとの相関が 0.3 を下回る最初の区画
    dfa = mean + half * np.cos(2.0 * (alpha - ang))
    model2 = np.sin(math.pi * lam * k2 * dfa - 0.5 * math.pi * cs * lam ** 3 * k2 * k2 + ps + math.asin(w)) ** 2
    nseg = max(4, len(zeros) // 2)
    edges = np.linspace(klo, khi, nseg + 1)
    fit_res = 1.0 / khi
    for a_, b_ in zip(edges[:-1], edges[1:]):
        sel = (kk >= a_) & (kk < b_)
        if sel.sum() >= 32 and _ncc(obs0[sel], model2[sel]) < 0.3:
            fit_res = 1.0 / float(a_)
            break

    # 不確かさ: タイルを 8 組に分けた jackknife(1 組を抜いた平均スペクトルで当てはめ直す)
    sig = sig_ast = float("nan")
    G = min(8, len(spectra))
    if G >= 2 and not reasons:
        total = np.sum(spectra, axis=0)
        est = []
        for g in range(G):
            grp = spectra[g::G]
            a_g = np.sqrt((total - np.sum(grp, axis=0)) / (len(spectra) - len(grp)))
            o_g = observe(a_g)
            if astigmatism:
                mg, hg, _, _ = refine(o_g, [(mean, ang)], max(half, h0))
            else:
                from scipy.optimize import minimize_scalar
                r = minimize_scalar(lambda d: -score2((d, 0.0, 0.0), o_g), bounds=(mean - 2 * step, mean + 2 * step),
                                    method="bounded", options={"xatol": 0.05})
                mg, hg = float(r.x), 0.0
            est.append((mg, 2.0 * hg))
        est = np.array(est)
        jk = lambda col: float(math.sqrt((G - 1) / G * np.sum((col - col.mean()) ** 2)))   # noqa: E731
        sig, sig_ast = jk(est[:, 0]), jk(est[:, 1])

    accepted = not reasons
    out = {"accepted": accepted, "reason": "; ".join(reasons) if reasons else "ok",
           "defocus_A": 0.5 * (du + dv), "defocus_u_A": du, "defocus_v_A": dv, "astig_angle_deg": th,
           "defocus_1d_A": df1, "defocus_sigma_A": sig, "astig_sigma_A": sig_ast, "score": s2, "score_1d": s1,
           "peak_z": peak_z, "peak_z_1d": z1,
           "n_rings": len(zeros), "fit_resolution_A": fit_res, "k_max_used": khi, "k_max_requested": k_req, "initial_lomb_A": df0, "tile": t,
           "n_tiles": len(spectra), "k": k, "flat": flat, "model": _model_1d(k, lam, cs, df1, w, ps),
           "defocus_grid_A": grid, "defocus_scores": scores, "wavelength_A": lam}
    if not accepted and on_fail == "raise":
        raise ValueError("%s: refused — %s" % (op, out["reason"]))
    return out


def tem_ctf_correct(image, pixel_A=1.0, kv=300.0, cs_mm=2.7, defocus_A=10000.0, astig_A=None, astig_angle_deg=None,
                    amplitude_contrast=0.07, phase_shift_deg=0.0, method="phase_flip", snr=None):
    """CTF の補正(``image2d``)。``method="phase_flip"``: F⁻¹[ F(I − ⟨I⟩) · sign(CTF) ] (位相反転、振幅はそのまま)/
    ``"wiener"``: F⁻¹[ F(I − ⟨I⟩) · CTF / (CTF² + 1/snr) ]。

    補正後は正のポテンシャル(原子)が**明るく**写る向き(I − 1 ≈ 2 Φ CTF に sign(CTF) か CTF を掛けるので)。
    焦点外れを間違えると、零点の外側で符号を逆に掛けて像が壊れる(PoC の探針)。包絡は掛けない(位相反転は振幅を
    戻さない、ウィーナーは ``snr`` が高周波の増幅を抑える)。``snr`` はウィーナーだけの引数(None = 10、
    位相反転に渡すと ValueError)。``astig_A`` / ``astig_angle_deg`` は None = 非点収差なし。
    """
    op = "tem_ctf_correct"
    img = _img(image, "image", op)
    ny, nx = img.shape
    px = _num(pixel_A, "pixel_A", op, lo=0.01, hi=1e4)
    args = _ctf_args(op, kv, cs_mm, defocus_A, astig_A, astig_angle_deg, amplitude_contrast, phase_shift_deg, 0.0, 0.0)
    if method not in ("phase_flip", "wiener"):
        raise ValueError("%s: method must be 'phase_flip' or 'wiener', got %r" % (op, method))
    ctf, _ = _ctf2d(ny, nx, px, *args, envelope=False)
    F = np.fft.fft2(img - img.mean())
    if method == "phase_flip":
        if snr is not None:
            raise ValueError("%s: snr applies to method='wiener' only" % op)
        return np.fft.ifft2(F * np.sign(ctf)).real
    s = 10.0 if snr is None else _num(snr, "snr", op, lo=0.0, lo_open=True, hi=1e9)
    return np.fft.ifft2(F * ctf / (ctf * ctf + 1.0 / s)).real
