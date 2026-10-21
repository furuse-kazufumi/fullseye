# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fiberoptics — ステップ型ファイバとライトガイド(閉じた式と、LP モードの特性方程式の数値解)。

動機(2026-10-14、材料ライブラリの系列「ファイバー」): 検査の照明はライトガイド(ファイバの束)で運ぶことが多く、
NIR 透過検査では光源 → ライトガイド → 対象 → センサの鎖の 1 段になる。ガラスの分散は ``materials`` が持つので、
ここは**導波**(どのモードが通るか・どれだけ広がるか・どれだけ入るか)の層。どの op も材料を名前で受けられる。

内容(7 op):
  材料      `material_group_index`(群屈折率 n − λ dn/dλ)/ `material_gvd`(分散パラメータ D = −(λ/c) d²n/dλ²)
  ファイバ  `fiber_numerical_aperture`(√(n_core² − n_clad²))/ `fiber_v_number`(V = 2πa NA/λ)
            `fiber_lp_modes`(LP_lm の特性方程式 u J_{l−1}(u)/J_l(u) = −w K_{l−1}(w)/K_l(w) を区間ごとに二分法で解く)
            `fiber_mode_field_diameter`(LP01 の場に重なり最大のガウス: 厳密な場から + Marcuse の近似式)
  照明      `fiber_bundle_coupling`(ライトガイドに入る割合 = 充填率 × 端面の Fresnel × NA の受け入れ × 減衰)

真値(外部): LP_lm の遮断は J_{l−1} の零点(LP11 = 2.405、LP21 / LP02 = 3.832 …、単一モードの条件 V < 2.405)、
大きな V でモード数 → V²/2、溶融石英の材料分散の零点 ≈ 1.27 µm、群屈折率 1.55 µm で ≈ 1.462。
来歴: Gloge, Appl. Opt. 10, 2252 (1971)(弱導波の LP モード)/ Marcuse, Bell Syst. Tech. J. 56, 703 (1977)(MFD の近似)/
Snyder & Love, *Optical Waveguide Theory* (1983)。規約: 長さは µm、波長は nm(pairs の λ も nm)。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import special

__all__ = [
    "material_group_index", "material_gvd", "fiber_numerical_aperture", "fiber_v_number",
    "fiber_lp_modes", "fiber_mode_field_diameter", "fiber_bundle_coupling",
]

LIGHT_C_UM_PER_PS = 299.792458        # µm / ps


def _pos(v, name, op):
    x = float(v)
    if not (math.isfinite(x) and x > 0.0):
        raise ValueError("%s: %s must be finite and > 0, got %r" % (op, name, v))
    return x


def _grid(wl_min_nm, wl_max_nm, n_points, op):
    lo, hi, n = float(wl_min_nm), float(wl_max_nm), int(n_points)
    if not (math.isfinite(lo) and math.isfinite(hi)) or lo <= 0.0 or hi <= lo or n < 2:
        raise ValueError("%s: need 0 < wl_min_nm < wl_max_nm and n_points >= 2" % op)
    return np.linspace(lo, hi, n)


def _n_real(material, lam_um, op):
    import materials as _mat
    rec = _mat._record(material, op)
    return _mat._nk(rec, lam_um, op)[0]


def _derivs(material, lam_um, op, h=None):
    """n, dn/dλ, d²n/dλ²(λ は µm)を中心差分で。h は既定 λ·1e-3(表の継ぎ目を跨がない程度に小さく)。"""
    lam = np.asarray(lam_um, dtype=np.float64)
    h = lam * 1e-3 if h is None else h
    n0 = _n_real(material, lam, op)
    np_ = _n_real(material, lam + h, op)
    nm_ = _n_real(material, lam - h, op)
    return n0, (np_ - nm_) / (2 * h), (np_ - 2 * n0 + nm_) / (h * h)


def _index(v, lam_um, name, op):
    if isinstance(v, str):
        return float(_n_real(v, np.array([lam_um]), op)[0])
    return _pos(v, name, op)


# --------------------------------------------------------------------------- #
# 1. 材料の分散                                                                 #
# --------------------------------------------------------------------------- #
def material_group_index(material="SILICA", wl_min_nm=800.0, wl_max_nm=1700.0, n_points=91):
    """群屈折率 n_g(λ) = n − λ dn/dλ を ``pairs``(λ [nm], n_g)で(材料は ``materials`` の名前)。

    パルスや包絡が進む速さは c / n_g。溶融石英は 1.55 µm で ≈ 1.462(屈折率 1.444 より大きい)。
    表の範囲の端では中心差分の片側が出るので、範囲は表より 0.1 % 内側に取る(外は ValueError)。
    """
    op = "material_group_index"
    wl = _grid(wl_min_nm, wl_max_nm, n_points, op)
    n, d1, _ = _derivs(material, wl / 1000.0, op)
    return np.stack([wl, n - (wl / 1000.0) * d1], axis=1)


def material_gvd(material="SILICA", wl_min_nm=1000.0, wl_max_nm=1700.0, n_points=71):
    """材料分散のパラメータ D(λ) = −(λ/c) d²n/dλ² [ps/(nm·km)] を ``pairs``(λ [nm], D)で。

    D = 0 の波長が材料分散の零点(溶融石英で ≈ 1.27 µm)。正(異常分散)では長い波長が速い。
    """
    op = "material_gvd"
    wl = _grid(wl_min_nm, wl_max_nm, n_points, op)
    lam = wl / 1000.0
    _, _, d2 = _derivs(material, lam, op)
    # D [ps/(nm km)] = -(λ/c) d²n/dλ²: λ µm, d²n/dλ² 1/µm², c µm/ps → ps/µm² ;  1 ps/(µm·µm) = 1e9 ps/(nm·km)/1e3...
    D_ps_per_um2 = -(lam / LIGHT_C_UM_PER_PS) * d2               # ps / (µm · µm)
    return np.stack([wl, D_ps_per_um2 * 1e6], axis=1)            # ps/(µm·µm) = 1e6 ps/(nm·km)


# --------------------------------------------------------------------------- #
# 2. ステップ型ファイバ                                                          #
# --------------------------------------------------------------------------- #
def fiber_numerical_aperture(n_core=1.4682, n_clad=1.4629, wavelength_nm=None):
    """開口数 NA = √(n_core² − n_clad²) と受け入れ半角(度)、比屈折率差 Δ。屈折率は数か材料名。

    wavelength_nm は屈折率を**材料名**で渡したときだけ要る(その波長の n を表から引く)。数で渡すなら使わない。
    返り値: dict(na, acceptance_half_angle_deg, delta, n_core, n_clad)。n_core ≤ n_clad は ValueError(導波しない)。
    """
    op = "fiber_numerical_aperture"
    if (isinstance(n_core, str) or isinstance(n_clad, str)) and wavelength_nm is None:
        raise ValueError("%s: wavelength_nm is required when an index is given as a material name" % op)
    lam = None if wavelength_nm is None else _pos(wavelength_nm, "wavelength_nm", op) / 1000.0
    nc, ncl = _index(n_core, lam, "n_core", op), _index(n_clad, lam, "n_clad", op)
    if nc <= ncl:
        raise ValueError("%s: the core index (%.6g) must exceed the cladding index (%.6g) to guide light" % (op, nc, ncl))
    na = math.sqrt(nc * nc - ncl * ncl)
    return {"na": na, "acceptance_half_angle_deg": math.degrees(math.asin(min(na, 1.0))),
            "delta": (nc * nc - ncl * ncl) / (2 * nc * nc), "n_core": nc, "n_clad": ncl}


def fiber_v_number(core_radius_um=4.1, na=0.12, wavelength_nm=1550.0):
    """規格化周波数 V = 2π a NA / λ と、単一モードかどうか(V < 2.4048 = J0 の最初の零点)。

    返り値: dict(v, single_mode, cutoff_wavelength_nm) —— cutoff は V = 2.4048 になる波長(これより長い波長で単一モード)。
    """
    op = "fiber_v_number"
    a = _pos(core_radius_um, "core_radius_um", op)
    NA = _pos(na, "na", op)
    lam = _pos(wavelength_nm, "wavelength_nm", op) / 1000.0
    j01 = float(special.jn_zeros(0, 1)[0])
    v = 2 * math.pi * a * NA / lam
    return {"v": v, "single_mode": v < j01, "cutoff_wavelength_nm": 2 * math.pi * a * NA / j01 * 1000.0}


def _lp_eq(l, V, u):
    w = np.sqrt(np.maximum(V * V - u * u, 0.0))
    lhs = u * special.jv(l - 1, u) / special.jv(l, u)
    rhs = -w * special.kv(l - 1, w) / special.kv(l, w)
    return lhs - rhs


def fiber_lp_modes(v_number=6.0, max_modes=None):
    """弱導波のステップ型ファイバの LP_lm モード: 特性方程式を解き、各モードの u・w・規格化伝搬定数 b を返す(``table``)。

    u J_{l−1}(u)/J_l(u) = −w K_{l−1}(w)/K_l(w)、u² + w² = V²(Gloge 1971)。l ごとに u の区間を J_l の零点と
    J_{l−1} の零点(= 遮断)で区切り、符号の変わる区間を二分法で解く(80 回、区間幅の 1e-24 倍)。
    返り値: dict(modes = [{"l", "m", "u", "w", "b", "cutoff_v", "degeneracy"}], n_modes(縮退込みの総数)、
    count_approx = V²/2)。縮退: l = 0 は 2(偏光)、l ≥ 1 は 4(偏光 × cos/sin)。

    ★限界: LP0m(m ≥ 2)は遮断の直上で束縛が指数関数的に弱い(w ∝ e^{−1/(…)}、V − u が e^{−数百})ので、
    遮断から V で約 0.05 以内では浮動小数で根が表せず、数えない(n_modes が 2 少ない)。LP_lm(l ≥ 1)の近づき方は
    代数的なので遮断の 0.001 上から解ける(PoC ``poc_fiber_light_guide`` の門)。
    """
    op = "fiber_lp_modes"
    V = _pos(v_number, "v_number", op)
    if V > 200.0:
        raise ValueError("%s: V = %.4g is beyond the solver's range (<= 200)" % (op, V))
    modes = []
    n_roots = max(2, int(math.ceil(V / math.pi)) + 2)
    previous_poles = None
    for l in range(0, 400):
        # 遮断: LP0m = 0 と J1 の零点、LP1m = J0 の零点、LPlm(l ≥ 2)= J_{l−1} の零点(0 を除く)
        if l == 0:
            cutoffs = [0.0] + list(special.jn_zeros(1, n_roots))
        elif l == 1:
            cutoffs = list(previous_poles)
        else:
            cutoffs = list(previous_poles)
        cutoffs = [c for c in cutoffs if c < V]
        if not cutoffs:
            break
        poles = special.jn_zeros(l, n_roots)                 # u は (遮断, 次の J_l の零点) にちょうど 1 つ
        previous_poles = poles
        for m, c in enumerate(cutoffs, start=1):
            pole_i = int(np.searchsorted(poles, c + 1e-12, side="right"))
            nxt = float(poles[pole_i]) if pole_i < poles.size else V
            lo, hi = c + 1e-12, min(nxt, V) - 1e-12
            if hi <= lo:
                continue
            flo, fhi = _lp_eq(l, V, lo), _lp_eq(l, V, hi)
            if not (np.isfinite(flo) and np.isfinite(fhi)) or flo * fhi > 0:
                continue
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                if mid == lo or mid == hi:
                    break
                fm = _lp_eq(l, V, mid)
                if flo * fm <= 0:
                    hi, fhi = mid, fm
                else:
                    lo, flo = mid, fm
            u = 0.5 * (lo + hi)
            w = math.sqrt(max(V * V - u * u, 0.0))
            modes.append({"l": l, "m": m, "u": u, "w": w, "b": 1.0 - (u / V) ** 2, "cutoff_v": c,
                          "degeneracy": 2 if l == 0 else 4})
            if max_modes is not None and len(modes) >= int(max_modes):
                break
        if max_modes is not None and len(modes) >= int(max_modes):
            break
    modes.sort(key=lambda d: -d["b"])
    return {"modes": modes, "n_modes": int(sum(d["degeneracy"] for d in modes)), "count_approx": V * V / 2.0, "v": V}


def fiber_mode_field_diameter(core_radius_um=4.1, v_number=2.2):
    """LP01 の場の直径(MFD)[µm] —— 厳密な場に**重なりが最大のガウス**を当てたときの 1/e² 直径。

    厳密: LP01 の固有値 (u, w) から場 E(r) = J0(ur/a)/J0(u)(r ≤ a)、K0(wr/a)/K0(w)(r > a)を作り、
    ガウス exp(−r²/w₀²) との重なり |∫E·G r dr|² / (∫E² r dr ∫G² r dr) を最大にする w₀ を黄金分割で探す(MFD = 2w₀)。
    近似: Marcuse 1977 の w₀/a = 0.65 + 1.619 V^{−3/2} + 2.879 V^{−6}(この同じ定義への当てはめ式)。
    もう 1 つの定義 Petermann I(2 次モーメント、w² = 2∫E² r³ dr / ∫E² r dr)は裾の指数関数を重く数えるので大きく出る
    —— 定義が違えば MFD は 10 % 違う(V = 1.2)ことを隠さないため両方返す。
    返り値: dict(mfd_um, mfd_marcuse_um, relative_difference, mfd_petermann1_um, overlap, u, w)。
    """
    op = "fiber_mode_field_diameter"
    a = _pos(core_radius_um, "core_radius_um", op)
    V = _pos(v_number, "v_number", op)
    lp = fiber_lp_modes(V, max_modes=1)["modes"]
    m0 = [d for d in lp if d["l"] == 0 and d["m"] == 1][0]
    u, w = m0["u"], m0["w"]
    r_in = np.linspace(0.0, 1.0, 4001)
    r_out = 1.0 + np.geomspace(1e-6, 40.0 / max(w, 1e-3), 8001)
    e = np.concatenate([special.jv(0, u * r_in) / special.jv(0, u), special.kv(0, w * r_out) / special.kv(0, w)])
    r = np.concatenate([r_in, r_out])
    ee = np.trapezoid(e * e * r, r)

    def overlap(w0):
        g = np.exp(-(r / w0) ** 2)
        return np.trapezoid(e * g * r, r) ** 2 / (ee * np.trapezoid(g * g * r, r))

    lo, hi = 0.2, 20.0
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    x1, x2 = hi - gr * (hi - lo), lo + gr * (hi - lo)
    f1, f2 = overlap(x1), overlap(x2)
    for _ in range(120):
        if f1 > f2:
            hi, x2, f2 = x2, x1, f1
            x1 = hi - gr * (hi - lo)
            f1 = overlap(x1)
        else:
            lo, x1, f1 = x1, x2, f2
            x2 = lo + gr * (hi - lo)
            f2 = overlap(x2)
    w_best = 0.5 * (lo + hi)
    p1 = math.sqrt(2.0 * np.trapezoid(e * e * r ** 3, r) / ee)
    marc = 2.0 * a * (0.65 + 1.619 * V ** -1.5 + 2.879 * V ** -6)
    mfd = 2.0 * w_best * a
    return {"mfd_um": mfd, "mfd_marcuse_um": marc, "relative_difference": marc / mfd - 1.0,
            "mfd_petermann1_um": 2.0 * p1 * a, "overlap": float(overlap(w_best)), "u": u, "w": w}


# --------------------------------------------------------------------------- #
# 3. ライトガイド                                                                #
# --------------------------------------------------------------------------- #
def fiber_bundle_coupling(source_na=0.5, fiber_na=0.55, packing_fraction=0.8, n_core=1.62,
                          length_m=1.0, attenuation_db_per_m=0.3, lambertian=True):
    """ライトガイド(ファイバの束)に入って出る光の割合。

    = 充填率(コアの面積の割合)× 入口と出口の端面の Fresnel 透過 ((1 − R)²、R = ((n−1)/(n+1))²)
      × NA の受け入れ(Lambert 光源なら (NA_fiber / NA_source)² を 1 で頭打ち —— sin²θ に比例する立体角の割合)
      × 減衰 10^{−αL/10}。返り値: dict(transmission と各因子)。
    """
    op = "fiber_bundle_coupling"
    sna, fna = _pos(source_na, "source_na", op), _pos(fiber_na, "fiber_na", op)
    pf = float(packing_fraction)
    if not (0.0 < pf <= 1.0):
        raise ValueError("%s: packing_fraction must lie in (0, 1], got %r" % (op, packing_fraction))
    if sna > 1.0 or fna > 1.0:
        raise ValueError("%s: numerical apertures must be <= 1 in air" % op)
    n = _pos(n_core, "n_core", op)
    L = float(length_m)
    att = float(attenuation_db_per_m)
    if not (math.isfinite(L) and L >= 0.0 and math.isfinite(att) and att >= 0.0):
        raise ValueError("%s: length_m and attenuation_db_per_m must be finite and >= 0" % op)
    R = ((n - 1) / (n + 1)) ** 2
    accept = min(1.0, (fna / sna) ** 2) if lambertian else (1.0 if fna >= sna else 0.0)
    fres = (1 - R) ** 2
    loss = 10 ** (-att * L / 10.0)
    return {"transmission": pf * fres * accept * loss, "packing": pf, "fresnel": fres, "acceptance": accept,
            "attenuation": loss}
