# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""dualxray — エネルギー弁別 X 線透過による材質の判別(デュアルエナジー / フォトンカウンティング)。

1 枚の X 線透過像は、各画素で ``L = −ln(I/I₀) = Σₘ μₘ tₘ`` という**1 つの数**しか測らない。
厚い軽元素(肉・樹脂)と薄い重元素(骨片・ガラス・金属)は同じ L を作れるので、厚みと材質は
分けられない。2 つのエネルギーで撮ると、μ(E) の形が材質ごとに違う(光電効果は ≈ Z³/E³、
コンプトン散乱は電子密度だけで決まる)ので、方程式が 2 本になって 2 つの未知(2 つの基底物質の
厚み)が解ける —— Alvarez & Macovski(Phys. Med. Biol. 21, 733, 1976)の基底分解。

流れ(既存の op を引いて合成する):

    xray_tube_spectrum           管電圧 → 多色スペクトル(Kramers の厚い陽極 + 陽極の自己吸収 + 特性線 + フィルタ)
    xray_beam_quality            スペクトル → 半価層(空気カーマで重みづけ、IEC の線質と比べる量)
    photon_counting_channels     スペクトル + エネルギーの窓 → チャネル(検出器の吸収・エネルギー分解能・電荷共有)
    dual_kvp_channels            2 つの管電圧のスペクトル → エネルギー積分型の 2 チャネル
    xray_channel_projection      材料ごとの厚み図 → チャネルごとの計数像(Poisson 雑音、photoncount.photon_sample)
    basis_material_decompose     計数像 → 基底物質の厚み図(重みつき最小二乗 = 高計数で最尤、収束しない画素は拒否)
    basis_decomposition_crlb     厚み → 分解の分散の下限(Fisher 情報の逆行列、Roessl & Herrmann 2009 の形)
    r_value_map                  低・高の対数減衰の比 R = L_low / L_high(厚みに依らない材質の指標、単色なら厳密)
    effective_z_map              R と L_high → 実効原子番号(元素の R の曲線と照合、Z ≤ 30)
    dual_energy_separability     2 つの材料(厚みを揃えた交絡の組)→ d′ と誤り率の閉形式

材料の μ/ρ(E) は ``materials`` の X 線の列(NIST SRD 126、Hubbell & Seltzer の表の部分集合)を
名前で引く。数値の直書きはしない。

**入っていないもの(正直に)**: 散乱線(グリッド・散乱除去なし、細いビームの減衰を仮定)、
検出器の K 蛍光の逃げ(CdTe の 23〜31 keV の逃げのピーク)、パイルアップ、画素間の電荷共有の
二重計数(ここでの電荷共有は 1 画素の中で低いエネルギーへ移る尾だけ)、陽極のヒール効果。
X 線管のスペクトルは物理の簡易模型で、公表の線質(半価層)との差を ``tests/test_dualxray.py`` が数える。
"""
from __future__ import annotations

import math

import numpy as np

import materials
import photoncount

__all__ = [
    "xray_tube_spectrum", "xray_beam_quality", "photon_counting_channels", "dual_kvp_channels",
    "xray_channel_projection", "basis_material_decompose", "basis_decomposition_crlb",
    "r_value_map", "effective_z_map", "dual_energy_separability",
]

#: 陽極の材料: (Z, A [g/mol], 密度 [g/cm³], K 端 [keV], K 線 ((名前, keV, 相対強度), …))
#: K 線のエネルギーと相対強度は X-ray Data Booklet(LBNL, 2009)表 1-2 / 1-3、K 端は表 1-1。
ANODES = {
    "W": (74, 183.84, 19.3, 69.525,
          (("Ka2", 57.9817, 58.0), ("Ka1", 59.31824, 100.0), ("Kb3", 66.9514, 11.0),
           ("Kb1", 67.2443, 22.0), ("Kb2", 69.067, 8.0))),
}
# 模型の 4 定数(2026-10-15、``tools/fit_xray_tube_constants.py``)。物理の形は Kramers + Kanaya–Okayama の深さ +
# 自己吸収 + Green–Cosslett 型の特性線で、強さと深さの尺度だけを、別の公開の物理模型(オープンソースの X 線管スペクトル計算、MIT、
# Poludniowski ら、Med. Phys. 48, 3630 (2021))の W 陽極 12°・Al 2.5 mm のスペクトル(40〜150 kV)に合わせた:
#   * 光子が生まれる深さ = DEPTH_FRACTION × (E₀/100 keV)^(−DEPTH_EXPONENT) × (R(E₀) − R(T))。電子は拡散と
#     後方散乱で到達深さより浅いところで光子を出す(1 のままだと 150 kV の半価層が 33 % 硬い)。
#   * K 線の総光子数 = K_SCALE × (U − 1)^K_EXPONENT × 自己吸収前の制動放射の総光子数(U = E₀/E_K)。
# 合わせた後の制動放射の形の差(全変動距離)は 0.8〜3 %。**外部真値の門**は合わせに使っていない IEC 61267 の
# 線質の半価層(RQR / RQA、tests/test_dualxray.py)。
DEPTH_FRACTION = 0.25
DEPTH_EXPONENT = 0.95
K_SCALE = 0.035
K_EXPONENT = 1.15

MAX_PIXELS = 4_000_000
#: 基底分解の内部定数(引数にしない)。反復の上限、収束とみなす更新幅 [cm]、それより厚い解は「飛んだ」として拒否する
#: 厚さ(単位 cm。100 cm の水は 80 kV で e^{-20} —— 計数が 0 になる厚さで、測った値ではありえない)。
DECOMP_MAX_ITER = 60
DECOMP_TOL_CM = 1e-6
DECOMP_MAX_THICKNESS_CM = 100.0
MAX_CHANNELS = 16
MAX_BASIS = 3


# --------------------------------------------------------------------------- #
# 入力の検査                                                                    #
# --------------------------------------------------------------------------- #
def _f(v, name, op, lo=None, hi=None, lo_open=False):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, v))
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    if lo is not None and (x < lo or (lo_open and x <= lo)):
        raise ValueError("%s: %s must be %s %g, got %r" % (op, name, ">" if lo_open else ">=", lo, v))
    if hi is not None and x > hi:
        raise ValueError("%s: %s must be <= %g, got %r" % (op, name, hi, v))
    return x


def _spectrum(spec, op):
    a = np.asarray(spec, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 2 or a.shape[0] < 3 or not np.all(np.isfinite(a)):
        raise ValueError("%s: spectrum must be finite pairs (E keV, photons per keV), shape (K, 2), K >= 3" % op)
    E, phi = a[:, 0], a[:, 1]
    if np.any(np.diff(E) <= 0) or E[0] <= 0:
        raise ValueError("%s: spectrum energies must be positive and strictly increasing" % op)
    if np.any(phi < 0) or not np.any(phi > 0):
        raise ValueError("%s: spectrum must be >= 0 with some positive entries" % op)
    dE = np.gradient(E)
    return E, phi, dE


def _channels(ch, op):
    if not isinstance(ch, dict) or not {"energy_kev", "weights", "gain", "mode"} <= set(ch):
        raise ValueError("%s: channels must come from photon_counting_channels / dual_kvp_channels" % op)
    E = np.asarray(ch["energy_kev"], dtype=np.float64)
    W = np.asarray(ch["weights"], dtype=np.float64)
    g = np.asarray(ch["gain"], dtype=np.float64)
    if W.ndim != 2 or W.shape[1] != E.size or g.shape != E.shape or W.shape[0] < 1 or W.shape[0] > MAX_CHANNELS:
        raise ValueError("%s: channels have inconsistent shapes" % op)
    if not (np.all(np.isfinite(W)) and np.all(W >= 0) and np.all(np.isfinite(g)) and np.all(g > 0)):
        raise ValueError("%s: channel weights must be finite and >= 0" % op)
    if np.any(W.sum(axis=1) <= 0):
        raise ValueError("%s: a channel has no sensitivity (empty energy window)" % op)
    return E, W, g


def _mu_table(materials_list, E, op):
    """材料名の列 → (M, K) の線減衰係数(単位 1/cm。materials の X 線の列)。"""
    if isinstance(materials_list, (str, dict)):
        materials_list = [materials_list]
    rows = []
    for m in materials_list:
        try:
            src = materials._xray_source(m, op)
            mu = materials._xray_mu_rho(src, E, 1, op)
        except ValueError as exc:
            raise ValueError(str(exc))
        if src["density_g_cm3"] is None:
            raise ValueError("%s: material %r has no density (pass {'composition': ..., 'density_g_cm3': ...})" % (op, m))
        rows.append(mu * src["density_g_cm3"])
    return np.array(rows)


def _names(materials_list):
    if isinstance(materials_list, (str, dict)):
        materials_list = [materials_list]
    return [m if isinstance(m, str) else str(m.get("name", "custom")) for m in materials_list]


# --------------------------------------------------------------------------- #
# 線源                                                                          #
# --------------------------------------------------------------------------- #
def _ko_range_um(t_kev, z, a, rho):
    """Kanaya–Okayama の電子の到達深さ(単位 µm。J. Phys. D 5, 43, 1972)。"""
    return 0.0276 * a * np.power(t_kev, 1.67) / (z ** 0.889 * rho)


def xray_tube_spectrum(kvp: float = 80.0, anode: str = "W", takeoff_deg: float = 12.0,
                       filtration=(("AL", 2.5),), e_min_kev: float = 5.0, de_kev: float = 0.5,
                       characteristic: bool = True, self_absorption: bool = True) -> np.ndarray:
    """X 線管の光子スペクトルを ``pairs``(E [keV], 光子数 / keV)で返す(Σ φ ΔE = 1 に正規化)。

    模型(厚い陽極):
      * 制動放射は Kramers の薄い標的の断面積 ∝ 1/(T·E) を、電子が T = E₀ から E まで減速する
        あいだ積分する。減速は到達深さ x(T) = R(E₀) − R(T)(Kanaya–Okayama の R ∝ T^1.67)で表す。
        自己吸収が無ければ積分は Kramers の式 φ(E) ∝ (E₀ − E)/E そのものになる(門で確かめる)。
      * 陽極の自己吸収: 深さ x で生まれた光子は取り出し角 θ の方向へ x/sin θ だけ陽極の中を通る
        (μ は materials の X 線の列から W を引く)。
      * 特性線(管電圧が K 端より高いとき): Kα₂ / Kα₁ / Kβ₁ / Kβ₂(X-ray Data Booklet の
        エネルギーと相対強度)、総数は (U − 1)^K_EXPONENT(K_EXPONENT = 1.15、U = E₀/E_K)に比例。各線は 1 つのビンに入る。
      * フィルタ: ``filtration`` = ((材料, 厚さ mm), …)。既定の Al 2.5 mm は管の固有ろ過の代表値。

    ``kvp`` は 15〜300 kV、``de_kev`` はビン幅(0.05〜5 keV)。返り値の E はビンの中心。
    特性線の強さは簡易模型(``K_SCALE``)で、実測のスペクトルとは数 % ずれる。線質の門は
    ``xray_beam_quality`` の半価層を公表の線質と比べる。
    """
    op = "xray_tube_spectrum"
    E0 = _f(kvp, "kvp", op, 15.0, 300.0)
    th = _f(takeoff_deg, "takeoff_deg", op, 1.0, 90.0)
    lo = _f(e_min_kev, "e_min_kev", op, 1.0, E0 - 1.0)
    de = _f(de_kev, "de_kev", op, 0.05, 5.0)
    if anode not in ANODES:
        raise ValueError("%s: anode must be one of %s, got %r" % (op, sorted(ANODES), anode))
    z, a, rho, ek, lines = ANODES[anode]
    nb = int(math.floor((E0 - lo) / de + 1e-9))
    if nb < 3:
        raise ValueError("%s: fewer than 3 energy bins between e_min_kev and kvp" % op)
    E = lo + (np.arange(nb) + 0.5) * de
    # 制動放射: φ(E) = (1/E) ∫_E^{E0} exp(−μ_W(E) ρ x(T)/sinθ) dT
    sin_t = math.sin(math.radians(th))
    mu_w = materials._xray_mu_rho(materials._xray_source(anode, op), E, 1, op) * rho  # 1/cm
    n_t = 256
    phi = np.empty_like(E)
    att_mean = np.empty_like(E)
    for i, e in enumerate(E):
        T = np.linspace(e, E0, n_t)
        if self_absorption:
            x_cm = DEPTH_FRACTION * (E0 / 100.0) ** (-DEPTH_EXPONENT) * (_ko_range_um(E0, z, a, rho) - _ko_range_um(T, z, a, rho)) * 1e-4
            f = np.exp(-mu_w[i] * x_cm / sin_t)
        else:
            f = np.ones_like(T)
        integ = float(np.trapezoid(f, T)) if hasattr(np, "trapezoid") else float(np.trapz(f, T))
        phi[i] = integ / e
        att_mean[i] = integ / max(E0 - e, 1e-12)
    brems_total = float(np.sum(phi) * de)
    if characteristic and E0 > ek:
        u = E0 / ek
        n_k = K_SCALE * (u - 1.0) ** K_EXPONENT * float(np.sum((E0 - E) / E) * de)
        rel = np.array([w for _, _, w in lines])
        for (_name, el, _w), frac in zip(lines, rel / rel.sum()):
            k = int(np.clip(np.floor((el - lo) / de), 0, nb - 1))
            phi[k] += n_k * frac * att_mean[k] / de
    tot_unfiltered = float(np.sum(phi) * de)
    for item in (filtration or ()):
        try:
            mat, t_mm = item
        except (TypeError, ValueError):
            raise ValueError("%s: filtration must be ((material, thickness_mm), ...), got %r" % (op, item))
        t = _f(t_mm, "filtration thickness_mm", op, 0.0, 1000.0)
        mu = _mu_table([mat], E, op)[0]
        phi = phi * np.exp(-mu * t * 0.1)
    tot = float(np.sum(phi) * de)
    # ★2026-10-15 探針で見つけた: Pb 50 mm でも e^{-130} は 0 にならず、正規化すると「ほぼ何も通らない」スペクトルが
    #   ふつうの顔で返っていた。透過が 1e-12 を切ったら値を返さず拒否する。
    if not tot > 1e-12 * tot_unfiltered or brems_total <= 0:
        raise ValueError("%s: the filtration transmits %.3g of the photons (< 1e-12) - nothing would reach "
                         "the object" % (op, tot / tot_unfiltered if tot_unfiltered > 0 else 0.0))
    return np.stack([E, phi / tot], axis=1)


def xray_beam_quality(spectrum, material: str = "AL") -> dict:
    """スペクトルの線質: 第 1・第 2 半価層、均等度、平均エネルギー、実効エネルギーを返す。

    半価層は**空気カーマ**が半分になる吸収体の厚さ(線量計で測る量の定義どおり):
    K(x) ∝ Σ φ(E) E (μ_en/ρ)_air(E) e^{−μ(E) x}。HVL₁ は K(x) = K(0)/2、HVL₂ は K(x) = K(0)/4 から
    HVL₁ を引いたもの、均等度 = HVL₁/HVL₂(単色なら 1)。実効エネルギーは単色で同じ HVL₁ を
    与えるエネルギー(μ(E_eff) = ln 2/HVL₁)。``material`` は吸収体(既定 Al、Cu も使う)。

    返り値: dict(hvl1_mm, hvl2_mm, homogeneity, mean_energy_kev(光子数の平均), effective_energy_kev,
    material)。公表の線質(IEC 61267 の RQA 系列など)と比べる量。
    """
    op = "xray_beam_quality"
    E, phi, dE = _spectrum(spectrum, op)
    mu = _mu_table([material], E, op)[0]
    air = materials._xray_mu_rho(materials._xray_source("AIR", op), E, 2, op)
    w = phi * dE * E * air

    def kerma(x_mm):
        return float(np.sum(w * np.exp(-mu * x_mm * 0.1)))

    k0 = kerma(0.0)

    def solve(frac):
        lo_x, hi_x = 0.0, 1.0
        while kerma(hi_x) > frac * k0:
            hi_x *= 2.0
            if hi_x > 1e5:
                raise ValueError("%s: the absorber does not reduce the kerma to %g within 100 m" % (op, frac))
        for _ in range(200):
            mid = 0.5 * (lo_x + hi_x)
            if kerma(mid) > frac * k0:
                lo_x = mid
            else:
                hi_x = mid
        return 0.5 * (lo_x + hi_x)

    h1 = solve(0.5)
    h2 = solve(0.25) - h1
    mu_target = math.log(2.0) / (h1 * 0.1)
    # 実効エネルギー: μ(E) は(端を除き)単調減少なので、スペクトルの範囲で μ = μ_target を探す
    Eg = np.geomspace(max(E[0], materials.XRAY_E_MIN_KEV), E[-1], 4000)
    mug = _mu_table([material], Eg, op)[0]
    idx = np.where((mug[:-1] - mu_target) * (mug[1:] - mu_target) <= 0)[0]
    e_eff = None
    if idx.size:
        j = idx[-1]
        t = (mug[j] - mu_target) / (mug[j] - mug[j + 1]) if mug[j] != mug[j + 1] else 0.0
        e_eff = float(Eg[j] + t * (Eg[j + 1] - Eg[j]))
    return {"hvl1_mm": h1, "hvl2_mm": h2, "homogeneity": h1 / h2,
            "mean_energy_kev": float(np.sum(phi * dE * E) / np.sum(phi * dE)),
            "effective_energy_kev": e_eff, "material": material}


# --------------------------------------------------------------------------- #
# 検出器のチャネル                                                              #
# --------------------------------------------------------------------------- #
def _absorption_efficiency(detector, thickness_mm, E, op):
    mu = _mu_table([detector], E, op)[0]
    return 1.0 - np.exp(-mu * thickness_mm * 0.1)


def photon_counting_channels(spectrum, thresholds_kev=(20.0, 50.0), detector: str = "CDTE",
                             detector_mm: float = 2.0, energy_resolution_fwhm_kev: float = 0.0,
                             charge_sharing: float = 0.0, upper_kev=None) -> dict:
    """フォトンカウンティング検出器のエネルギーの窓 → チャネル(1 光子 1 カウント)。

    ``thresholds_kev`` = (T₁, T₂, …): チャネル c は堆積エネルギーが [T_c, T_{c+1}) の光子を数える
    (最後の窓の上限は ``upper_kev``、既定は無限大)。検出器の応答:
      * 吸収効率 1 − e^{−μ d}(``detector`` の X 線の列、既定 CdTe 2 mm)。
      * エネルギー分解能: 堆積エネルギーに FWHM ``energy_resolution_fwhm_kev`` のガウスのぼけ。
      * 電荷共有: 割合 ``charge_sharing`` の光子は電荷の一部しか集まらず、堆積エネルギーが
        [0, E] に一様に散らばる(低いエネルギーへの尾。1 画素の中の模型で、隣の画素への二重計数は
        入れない)。
    返り値: dict(energy_kev, weights (C, K) = 入射光子 1 個がチャネル c に数えられる確率 × スペクトル
    のビンの重み, gain = 1(計数), mode = "counting", labels, thresholds_kev, response)。
    窓が 1 つも光子を拾わないときは ValueError。
    """
    op = "photon_counting_channels"
    E, phi, dE = _spectrum(spectrum, op)
    th = [float(t) for t in np.atleast_1d(np.asarray(thresholds_kev, dtype=np.float64))]
    if len(th) < 1 or len(th) > MAX_CHANNELS or any(not math.isfinite(t) or t < 0 for t in th) \
            or any(b <= a for a, b in zip(th, th[1:])):
        raise ValueError("%s: thresholds_kev must be 1..%d increasing finite values >= 0" % (op, MAX_CHANNELS))
    up = math.inf if upper_kev is None else _f(upper_kev, "upper_kev", op, th[-1], lo_open=True)
    edges = th + [up]
    d = _f(detector_mm, "detector_mm", op, 0.0, 100.0, lo_open=True)
    fw = _f(energy_resolution_fwhm_kev, "energy_resolution_fwhm_kev", op, 0.0, 100.0)
    cs = _f(charge_sharing, "charge_sharing", op, 0.0, 1.0)
    qe = _absorption_efficiency(detector, d, E, op)
    sig = fw / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    P = np.zeros((len(th), E.size))
    for c in range(len(th)):
        a, b = edges[c], edges[c + 1]
        if sig > 0:
            from math import erf
            cdf = np.vectorize(lambda x, m: 0.5 * (1.0 + erf((x - m) / (sig * math.sqrt(2.0)))))
            p_full = (cdf(b, E) if math.isfinite(b) else 1.0) - cdf(a, E)
        else:
            p_full = ((E >= a) & (E < b)).astype(np.float64)
        # 一様な尾 [0, E] のうち [a, b) に入る割合
        p_tail = np.clip((np.minimum(b, E) - np.minimum(a, E)) / E, 0.0, 1.0)
        P[c] = (1.0 - cs) * p_full + cs * p_tail
    W = (phi * dE)[None, :] * qe[None, :] * P
    if np.any(W.sum(axis=1) <= 0):
        raise ValueError("%s: an energy window [%s) counts no photons of this spectrum" % (op, edges))
    labels = ["%g-%s keV" % (edges[c], "inf" if not math.isfinite(edges[c + 1]) else "%g" % edges[c + 1])
              for c in range(len(th))]
    return {"energy_kev": E, "weights": W, "gain": np.ones_like(E), "mode": "counting", "labels": labels,
            "thresholds_kev": tuple(th), "upper_kev": None if not math.isfinite(up) else up,
            "response": {"detector": detector, "detector_mm": d, "energy_resolution_fwhm_kev": fw,
                         "charge_sharing": cs}}


def dual_kvp_channels(spectrum_low, spectrum_high, detector: str = "CSI", detector_mm: float = 0.6) -> dict:
    """2 つの管電圧で撮るエネルギー積分型(シンチレータ)の 2 チャネル。

    信号は吸収した光子のエネルギーの和(gain = E)。分散は Σ φ E² e^{−μt}(複合 Poisson、
    Swank の雑音の増えは入れない)。2 つのスペクトルは同じエネルギーの格子に載せる(線形補間、
    範囲の外は 0)。返り値の形は :func:`photon_counting_channels` と同じ(mode = "integrating")。
    """
    op = "dual_kvp_channels"
    El, pl, dl = _spectrum(spectrum_low, op)
    Eh, ph, dh = _spectrum(spectrum_high, op)
    de = float(min(np.min(dl), np.min(dh)))
    E = np.arange(min(El[0], Eh[0]), max(El[-1], Eh[-1]) + 0.5 * de, de)
    d = _f(detector_mm, "detector_mm", op, 0.0, 100.0, lo_open=True)
    qe = _absorption_efficiency(detector, d, E, op)
    W = []
    for Es, ps in ((El, pl), (Eh, ph)):
        s = np.interp(E, Es, ps, left=0.0, right=0.0)
        s = s / (np.sum(s) * de)
        W.append(s * de * qe)
    return {"energy_kev": E, "weights": np.array(W), "gain": E.copy(), "mode": "integrating",
            "labels": ["low kVp", "high kVp"], "thresholds_kev": None, "upper_kev": None,
            "response": {"detector": detector, "detector_mm": d}}


# --------------------------------------------------------------------------- #
# 投影と雑音                                                                    #
# --------------------------------------------------------------------------- #
def _stack(thickness, n_mat, op):
    t = np.asarray(thickness, dtype=np.float64)
    if t.ndim == 2 and n_mat == 1:
        t = t[None]
    if t.ndim == 1 and t.size == n_mat:
        t = t[:, None, None]
    if t.ndim != 3 or t.shape[0] != n_mat:
        raise ValueError("%s: thickness must be (M, H, W) with one map per material (M=%d), got %s"
                         % (op, n_mat, t.shape))
    if not np.all(np.isfinite(t)) or np.any(t < 0):
        raise ValueError("%s: thickness [cm] must be finite and >= 0" % op)
    if t.shape[1] * t.shape[2] > MAX_PIXELS:
        raise ValueError("%s: image larger than %d pixels" % (op, MAX_PIXELS))
    return t


def _expected(t, mu, E, W, g, n0):
    """平均と分散: mean_c = n0 Σ_k W g A_k、var_c = n0 Σ_k W g² A_k(A = e^{−Σ μ t})。"""
    M, H, Wd = t.shape
    A = np.exp(-np.tensordot(mu.T, t.reshape(M, -1), axes=(1, 0)))        # (K, P)
    mean = n0 * (W * g[None, :]) @ A
    var = n0 * (W * (g * g)[None, :]) @ A
    return mean.reshape(-1, H, Wd), var.reshape(-1, H, Wd)


def xray_channel_projection(thickness, materials_list=("MUSCLE_ICRU44",), channels=None,
                            photons_per_pixel: float = 1e5, noise: bool = True, seed: int = 0) -> np.ndarray:
    """材料ごとの厚み図 → チャネルごとの信号の像 (C, H, W)。

    ``thickness``: (M, H, W)、単位 cm(``materials_list`` の材料ごとに 1 枚、重なりは足し算 = 細いビームの
    Beer–Lambert)。``photons_per_pixel``: 1 画素に入射する光子の数(全エネルギー、検出器の前)。
    計数(counting)のチャネルは平均 n₀ Σ W e^{−μt} の Poisson 標本(``photoncount.photon_sample``、
    チャネルごとに seed から決まる別の乱数列)。積分型(integrating)は平均と分散 Σ W E² e^{−μt}
    のガウス(複合 Poisson の近似)。``noise=False`` は平均そのもの。
    空き(厚み 0)の平均は ``channels`` から決まるので、分解の op は同じ ``channels`` と
    ``photons_per_pixel`` を受けて自分で計算する(白の撮影を別に渡すこともできる)。
    """
    op = "xray_channel_projection"
    if channels is None:
        channels = _default_channels()
    E, W, g = _channels(channels, op)
    names = _names(materials_list)
    t = _stack(thickness, len(names), op)
    mu = _mu_table(materials_list, E, op)
    n0 = _f(photons_per_pixel, "photons_per_pixel", op, 0.0, 1e12, lo_open=True)
    sd = int(seed)
    if sd < 0 or sd != seed:
        raise ValueError("%s: seed must be a non-negative integer" % op)
    mean, var = _expected(t, mu, E, W, g, n0)
    if not noise:
        return mean
    out = np.empty_like(mean)
    for c in range(mean.shape[0]):
        if channels["mode"] == "counting":
            out[c] = photoncount.photon_sample(mean[c], photons_per_unit=1.0, seed=sd * MAX_CHANNELS + c)
        else:
            rng = np.random.default_rng([sd, c, 7919])
            out[c] = mean[c] + np.sqrt(var[c]) * rng.standard_normal(mean[c].shape)
    return out


def _default_channels() -> dict:
    """既定のチャネル: 80 kV・Al 2.5 mm の W 管、CdTe 2 mm のフォトンカウンティング、窓 20 / 45 keV。"""
    return photon_counting_channels(xray_tube_spectrum(80.0), thresholds_kev=(20.0, 45.0))


def _channel_index(v, name, n_channels, op):
    """窓の番号(負は後ろから)。整数でない値(0.5 など)は黙って切り捨てずに拒否する。"""
    if isinstance(v, bool) or not float(v).is_integer():
        raise ValueError("%s: %s must be an integer channel index, got %r" % (op, name, v))
    i = int(v)
    if not -n_channels <= i < n_channels:
        raise ValueError("%s: %s=%d is outside the %d channels" % (op, name, i, n_channels))
    return i % n_channels


def _log_signal(signal, channels, n0, flat, op):
    if channels is None:
        channels = _default_channels()
    s = np.asarray(signal, dtype=np.float64)
    E, W, g = _channels(channels, op)
    if s.ndim == 2:
        s = s[:, :, None]
    if s.ndim != 3 or s.shape[0] != W.shape[0]:
        raise ValueError("%s: signal must be (C, H, W) with C = %d channels" % (op, W.shape[0]))
    if flat is None:
        f = n0 * (W * g[None, :]).sum(axis=1)
        f = f[:, None, None] * np.ones_like(s)
    else:
        f = np.asarray(flat, dtype=np.float64)
        if f.ndim == 1:
            f = f[:, None, None] * np.ones_like(s)
        if f.shape != s.shape or not np.all(np.isfinite(f)) or np.any(f <= 0):
            raise ValueError("%s: flat must be positive with the shape of signal (or one value per channel)" % op)
    ok = np.isfinite(s) & (s > 0)
    L = np.full(s.shape, np.nan)
    L[ok] = -np.log(s[ok] / f[ok])
    return L, ok.all(axis=0)


# --------------------------------------------------------------------------- #
# 基底分解                                                                      #
# --------------------------------------------------------------------------- #
def basis_material_decompose(signal, channels=None, basis=("WATER", "AL"), photons_per_pixel: float = 1e5,
                             flat=None) -> dict:
    """チャネルの信号 → 基底物質の厚み図(Alvarez–Macovski / Lehmann の基底分解)。

    各画素で、多色の順方向模型 L_c(b) = −ln(Σ_k W_ck g_k e^{−Σ_j μ_j(E_k) b_j} / Σ_k W_ck g_k)
    を測った L_c に合わせる b(基底ごとの厚み [cm])を、分散 var(L_c) ≈ var_c/mean_c² で重みをつけた
    Gauss–Newton で解く(チャネル数 = 基底の数なら連立方程式の厳密解、多ければ重みつき最小二乗
    = 高計数での最尤)。初期値は空きのスペクトルの実効 μ の線形解。
    基底の厚みは負になりうる(水と Al の基底でポリエチレンは Al が負)—— 物理の厚みではなく
    「同じ減衰を作る基底の組合せ」。

    **拒否(fail-closed)**: 信号が 0 以下・非有限の画素、:data:`DECOMP_MAX_ITER` 回で :data:`DECOMP_TOL_CM` に
    収束しない画素、|b| > :data:`DECOMP_MAX_THICKNESS_CM` に飛ぶ画素は NaN にして ``rejected`` に数える
    (黙って値を返さない)。反復の上限・収束の幅・厚さの上限は引数にしない —— Gauss–Newton は 3〜6 回で
    1e-6 cm に収束し、どの値にしても解ける画素の答えは変わらない(効かないノブは置かない、2026-10-18)。
    チャネル数 < 基底の数は ValueError(解が決まらない)。

    返り値: dict(thickness (B, H, W) [cm], basis, rejected (H, W) bool, n_rejected, iterations,
    residual (H, W) = 重みつき残差の二乗和)。``opstomography.call`` は thickness だけを返す。
    """
    op = "basis_material_decompose"
    if channels is None:
        channels = _default_channels()
    E, W, g = _channels(channels, op)
    names = _names(basis)
    B, C = len(names), W.shape[0]
    if B < 1 or B > MAX_BASIS:
        raise ValueError("%s: 1..%d basis materials" % (op, MAX_BASIS))
    if C < B:
        raise ValueError("%s: %d channels cannot determine %d basis thicknesses" % (op, C, B))
    mu = _mu_table(basis, E, op)                                           # (B, K)
    n0 = _f(photons_per_pixel, "photons_per_pixel", op, 0.0, 1e12, lo_open=True)
    L, ok = _log_signal(signal, channels, n0, flat, op)
    H, Wd = L.shape[1:]
    P = H * Wd
    Lp = L.reshape(C, P)
    Wg = W * g[None, :]
    Wg2 = W * (g * g)[None, :]
    s0 = Wg.sum(axis=1)
    mu_eff0 = (Wg @ mu.T) / s0[:, None]                                    # (C, B)
    b = np.zeros((B, P))
    good = ok.reshape(P).copy()
    if good.any():
        b[:, good] = np.linalg.lstsq(mu_eff0, Lp[:, good], rcond=None)[0]
    conv = np.zeros(P, dtype=bool)
    it_used = np.zeros(P, dtype=np.int64)
    resid = np.full(P, np.nan)
    mi, tol, bmax = DECOMP_MAX_ITER, DECOMP_TOL_CM, DECOMP_MAX_THICKNESS_CM
    active = good.copy()
    for it in range(1, mi + 1):
        idx = np.where(active)[0]
        if idx.size == 0:
            break
        bb = b[:, idx]
        A = np.exp(-(mu.T @ bb))                                           # (K, n)
        S = Wg @ A                                                         # (C, n)
        V = Wg2 @ A
        if np.any(S <= 0):
            bad = idx[np.any(S <= 0, axis=0)]
            active[bad] = False
            good[bad] = False
            continue
        Lm = -np.log(S / s0[:, None])
        # dL_c/db_j = Σ_k Wg A μ_j / S
        J = np.einsum("ck,kn,bk->ncb", Wg, A, mu) / S.T[:, :, None]         # (n, C, B)
        var_L = n0 * V / (n0 * S) ** 2                                     # (C, n)
        w = 1.0 / np.maximum(var_L.T, 1e-300)                              # (n, C)
        r = (Lp[:, idx] - Lm).T                                            # (n, C)
        JTw = J.transpose(0, 2, 1) * w[:, None, :]                          # (n, B, C)
        Hm = JTw @ J
        gr = (JTw @ r[:, :, None])[:, :, 0]
        try:
            step = np.linalg.solve(Hm, gr[:, :, None])[:, :, 0]
        except np.linalg.LinAlgError:
            det = np.linalg.det(Hm)
            sing = np.abs(det) < 1e-300
            step = np.zeros_like(gr)
            ns = ~sing
            if ns.any():
                step[ns] = np.linalg.solve(Hm[ns], gr[ns][:, :, None])[:, :, 0]
            active[idx[sing]] = False
            good[idx[sing]] = False
        b[:, idx] = bb + step.T
        it_used[idx] = it
        small = np.max(np.abs(step), axis=1) < tol
        blown = np.max(np.abs(b[:, idx]), axis=0) > bmax
        resid[idx] = np.sum(r * r * w, axis=1)
        conv[idx[small & ~blown]] = True
        active[idx[small | blown]] = False
        good[idx[blown]] = False
    accepted = good & conv
    b[:, ~accepted] = np.nan
    resid[~accepted] = np.nan
    rej = ~accepted.reshape(H, Wd)
    return {"thickness": b.reshape(B, H, Wd), "basis": names, "rejected": rej, "n_rejected": int(rej.sum()),
            "iterations": int(it_used.max()) if P else 0, "residual": resid.reshape(H, Wd)}


def basis_decomposition_crlb(thickness_cm=(5.0, 0.0), basis=("WATER", "AL"), channels=None,
                             photons_per_pixel: float = 1e5) -> dict:
    """基底の厚み b での分解の分散の下限(Cramér–Rao)を閉形式で返す。

    Fisher 情報 F = Σ_c (1/var_c) ∇mean_c ∇mean_cᵀ、∂mean_c/∂b_j = −n₀ Σ_k W g μ_j e^{−μ·b}
    (計数では var_c = mean_c で Poisson の Fisher 情報そのもの、Roessl & Herrmann 2009 の式)。
    CRLB = F⁻¹。返り値: dict(cov (B, B) [cm²], sigma_cm (B,), correlation, expected (C,), basis,
    condition(F の条件数 —— 2 つの基底の μ(E) が似ているほど大きい))。
    F が特異(チャネル < 基底、または同じ材料を 2 回)なら ValueError。
    """
    op = "basis_decomposition_crlb"
    if channels is None:
        channels = _default_channels()
    E, W, g = _channels(channels, op)
    names = _names(basis)
    mu = _mu_table(basis, E, op)
    b = np.asarray(thickness_cm, dtype=np.float64).reshape(-1)
    if b.size != len(names) or not np.all(np.isfinite(b)):
        raise ValueError("%s: thickness_cm needs one finite value per basis material" % op)
    n0 = _f(photons_per_pixel, "photons_per_pixel", op, 0.0, 1e12, lo_open=True)
    A = np.exp(-(mu.T @ b))
    mean = n0 * (W * g) @ A
    var = n0 * (W * g * g) @ A
    grad = -n0 * (W * g * A[None, :]) @ mu.T                               # (C, B)
    F = (grad.T / var[None, :]) @ grad
    cond = float(np.linalg.cond(F))
    if not np.isfinite(cond) or cond > 1e14:
        raise ValueError("%s: Fisher information is singular (condition %.3g) - the basis is not "
                         "separable with these channels" % (op, cond))
    cov = np.linalg.inv(F)
    sd = np.sqrt(np.diag(cov))
    return {"cov": cov, "sigma_cm": sd, "correlation": cov / np.outer(sd, sd), "expected": mean,
            "basis": names, "condition": cond}


# --------------------------------------------------------------------------- #
# 材質の指標                                                                    #
# --------------------------------------------------------------------------- #
def r_value_map(signal, channels=None, photons_per_pixel: float = 1e5, low: int = 0, high: int = -1,
                flat=None, min_log: float = 0.02) -> np.ndarray:
    """R = L_low / L_high(低エネルギーと高エネルギーの対数減衰の比)の像を返す。

    単色なら R = μ(E_low)/μ(E_high) で**厚みに依らず材質だけで決まる**(Z が大きいほど光電効果で
    低エネルギーの μ が大きく、R が大きい)。多色ではビーム硬化で厚みとともに少し動く —— その動き
    が「厚い軽元素と薄い重元素」の交絡の源。L_high < ``min_log`` の画素(ほぼ素通しで比が雑音だけ
    になる)と信号が 0 以下の画素は NaN(拒否)。
    """
    op = "r_value_map"
    n0 = _f(photons_per_pixel, "photons_per_pixel", op, 0.0, 1e12, lo_open=True)
    L, ok = _log_signal(signal, channels, n0, flat, op)
    C = L.shape[0]
    lo_i, hi_i = _channel_index(low, "low", C, op), _channel_index(high, "high", C, op)
    if lo_i == hi_i:
        raise ValueError("%s: low/high must be two different channel indices (C=%d)" % (op, C))
    ml = _f(min_log, "min_log", op, 0.0, 10.0, lo_open=True)
    Ll, Lh = L[lo_i], L[hi_i]
    R = np.full(Ll.shape, np.nan)
    m = ok & np.isfinite(Lh) & (Lh >= ml)
    R[m] = Ll[m] / Lh[m]
    return R


#: 実効 Z の照合に使う元素(K 端が 10 keV より下で、R が Z について単調になる範囲)。
#: ★2026-10-15 探針で見つけた: Fe(26)より上は R がほとんど同じになる(80 kV・窓 20/45 keV の薄い板で
#:   Fe 4.403 / Ni 4.417 / Cu 4.418 / Zn 4.416 —— Cu と Zn は逆転する)。区別できない範囲を照合に入れると、
#:   単調性の検査で拒否するか、雑音で Z が 26〜30 を飛び回る。照合は Fe までにし、それより重い R は範囲の外(NaN)。
EFFECTIVE_Z_REFERENCES = (1, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 19, 20, 22, 24, 25, 26)


def _r_curves(channels, low, high, op, n_t=240):
    """元素ごとに、質量厚さの格子で (L_high, R) の曲線を作る。"""
    E, W, g = _channels(channels, op)
    Wg = W * g[None, :]
    s0 = Wg.sum(axis=1)
    curves = []
    for z in EFFECTIVE_Z_REFERENCES:
        src = materials._xray_source(materials._XE[z]["symbol"], op)
        mr = materials._xray_mu_rho(src, E, 1, op)                         # cm²/g
        ts = np.geomspace(1e-4, 200.0, n_t)                                # g/cm²
        S = Wg @ np.exp(-np.outer(mr, ts))                                 # (C, n_t)
        ok = np.all(S > 1e-300 * s0[:, None], axis=0)                      # 厚すぎて計数が 0 に潰れる点は使わない
        L = -np.log(S[:, ok] / s0[:, None])
        curves.append((z, L[high], L[low] / L[high]))
    return curves


def effective_z_map(signal, channels=None, photons_per_pixel: float = 1e5, low: int = 0, high: int = -1,
                    flat=None, min_log: float = 0.05) -> np.ndarray:
    """デュアルエナジーの像から実効原子番号の像を推定する(R を元素の曲線と照合)。

    各元素 Z(:data:`EFFECTIVE_Z_REFERENCES`、H〜Fe)について、同じチャネルで質量厚さを振った
    (L_high, R) の曲線を作り、画素の L_high での R_Z を読む。画素の R を挟む 2 つの元素の間を
    Z について線形に補間した値が実効 Z。厚みの効果(ビーム硬化)は「同じ L_high で比べる」ことで
    打ち消す —— 厚い軽元素と薄い重元素が同じ L_high でも R で分かれる。

    **拒否**: L_high < ``min_log``、R が H より小さいか Fe より大きい(範囲の外 —— Fe より重い元素は R が
    ほとんど同じで Z を区別できず、さらに重い金属は K 端がスペクトルの中にあって R が単調でない)画素は NaN。照合の曲線が Z について単調で
    ない(窓の選び方で K 端が入る)ときは ValueError。
    """
    op = "effective_z_map"
    n0 = _f(photons_per_pixel, "photons_per_pixel", op, 0.0, 1e12, lo_open=True)
    L, ok = _log_signal(signal, channels, n0, flat, op)
    C = L.shape[0]
    lo_i, hi_i = _channel_index(low, "low", C, op), _channel_index(high, "high", C, op)
    if lo_i == hi_i:
        raise ValueError("%s: low/high must be two different channels" % op)
    ml = _f(min_log, "min_log", op, 0.0, 10.0, lo_open=True)
    curves = _r_curves(channels if channels is not None else _default_channels(), lo_i, hi_i, op)
    Lh = L[hi_i]
    R = L[lo_i] / np.where(Lh > 0, Lh, np.nan)
    m = ok & np.isfinite(Lh) & (Lh >= ml) & np.isfinite(R)
    lh = Lh[m]
    Rz = np.empty((len(curves), lh.size))
    zs = np.array([z for z, _, _ in curves], dtype=np.float64)
    for i, (z, lhc, rc) in enumerate(curves):
        if lh.size and (lh.max() > lhc[-1] or lh.min() < lhc[0]):
            # 曲線の外の L_high は端の値で埋めずに拒否する
            pass
        Rz[i] = np.interp(lh, lhc, rc, left=np.nan, right=np.nan)
    if lh.size and np.any(np.diff(Rz, axis=0) <= 0):
        bad = np.where(np.any(np.diff(Rz, axis=0) <= 0, axis=1))[0]
        if np.any(np.isfinite(np.diff(Rz, axis=0)[bad])):
            raise ValueError("%s: R is not monotone in Z between Z=%s with these channels (an absorption edge "
                             "inside the windows?)" % (op, [int(zs[j]) for j in bad[:3]]))
    r = R[m]
    out_m = np.full(r.shape, np.nan)
    # Z について線形補間: R_Z(i) <= r < R_Z(i+1)
    for i in range(len(curves) - 1):
        a, b2 = Rz[i], Rz[i + 1]
        sel = (r >= a) & (r < b2) & np.isfinite(a) & np.isfinite(b2)
        out_m[sel] = zs[i] + (r[sel] - a[sel]) / (b2[sel] - a[sel]) * (zs[i + 1] - zs[i])
    out = np.full(Lh.shape, np.nan)
    out[m] = out_m
    return out


def dual_energy_separability(material_a="POLYETHYLENE", thickness_a_cm: float = 1.0, material_b="AL",
                             thickness_b_cm=None, channels=None, photons_per_pixel: float = 1e5,
                             background=None, n_pixels: int = 1) -> dict:
    """2 つの材料(厚み)が、チャネルの対数減衰でどれだけ分けられるか(d′ と誤り率の閉形式)。

    ``thickness_b_cm=None`` は**交絡の組**: b の厚みを、最後(最も高いエネルギー)のチャネルで a と
    同じ L になるように決める(単一エネルギーの像では区別できない組)。``background`` =
    (材料, 厚さ cm) は両方に重なる共通の母材(肉の中の異物)。``n_pixels`` 個の画素を平均した
    領域で判定する(d′ は √n 倍)。

    各材料の L ベクトル(チャネルごと)は平均 μ_a, μ_b、共分散は Poisson の差分近似
    Σ = diag(var_c/mean_c²)/n。判別は等事前確率の線形判別(LDA)で、d′² = Δᵀ Σ̄⁻¹ Δ、
    誤り率 = Φ(−d′/2)。比べのため、1 チャネルだけで判定したときの d′ も返す(交絡の組では最後の
    チャネルの d′ は 0)。

    返り値: dict(thickness_b_cm, L_a, L_b, R_a, R_b, d_prime, error_rate, d_prime_single (C,),
    error_rate_single (C,), sigma_L (C,), n_pixels)。
    """
    op = "dual_energy_separability"
    if channels is None:
        channels = _default_channels()
    E, W, g = _channels(channels, op)
    n0 = _f(photons_per_pixel, "photons_per_pixel", op, 0.0, 1e12, lo_open=True)
    ta = _f(thickness_a_cm, "thickness_a_cm", op, 0.0, 1000.0)
    npx = int(n_pixels)
    if npx < 1 or npx != n_pixels:
        raise ValueError("%s: n_pixels must be a positive integer" % op)
    mu_a = _mu_table([material_a], E, op)[0]
    mu_b = _mu_table([material_b], E, op)[0]
    mu_bg = np.zeros_like(E)
    if background is not None:
        try:
            bmat, bt = background
        except (TypeError, ValueError):
            raise ValueError("%s: background must be (material, thickness_cm)" % op)
        mu_bg = _mu_table([bmat], E, op)[0] * _f(bt, "background thickness", op, 0.0, 1000.0)
    Wg, Wg2 = W * g[None, :], W * (g * g)[None, :]
    s0 = Wg.sum(axis=1)

    def stats(att):
        A = np.exp(-att)
        S = Wg @ A
        V = Wg2 @ A
        return -np.log(S / s0), V / (n0 * S * S)          # var(L_c) = var_c / mean_c²

    La, va = stats(mu_a * ta + mu_bg)
    Lbg, _ = stats(mu_bg)
    if thickness_b_cm is None:
        target = La[-1]
        lo_t, hi_t = 0.0, 1.0
        while stats(mu_b * hi_t + mu_bg)[0][-1] < target:
            hi_t *= 2.0
            if hi_t > 1e4:
                raise ValueError("%s: no thickness of %r matches the last-channel attenuation" % (op, material_b))
        for _ in range(200):
            mid = 0.5 * (lo_t + hi_t)
            if stats(mu_b * mid + mu_bg)[0][-1] < target:
                lo_t = mid
            else:
                hi_t = mid
        tb = 0.5 * (lo_t + hi_t)
    else:
        tb = _f(thickness_b_cm, "thickness_b_cm", op, 0.0, 1000.0)
    Lb, vb = stats(mu_b * tb + mu_bg)
    # var(L_c) ≈ var_c / mean_c²(n0 は stats の中で割ってある)
    cov = np.diag(0.5 * (va + vb)) / npx
    d = Lb - La
    dp = float(math.sqrt(max(float(d @ np.linalg.solve(cov, d)), 0.0)))
    sl = np.sqrt(np.diag(cov))
    dps = np.abs(d) / sl

    def phi(x):
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    Ra = (La - Lbg) / (La[-1] - Lbg[-1]) if La[-1] - Lbg[-1] > 0 else np.full_like(La, np.nan)
    Rb = (Lb - Lbg) / (Lb[-1] - Lbg[-1]) if Lb[-1] - Lbg[-1] > 0 else np.full_like(Lb, np.nan)
    return {"thickness_a_cm": ta, "thickness_b_cm": tb, "L_a": La, "L_b": Lb, "R_a": Ra, "R_b": Rb,
            "d_prime": dp, "error_rate": phi(-dp / 2.0), "d_prime_single": dps,
            "error_rate_single": np.array([phi(-x / 2.0) for x in dps]), "sigma_L": sl, "n_pixels": npx,
            "cov_L": cov}
