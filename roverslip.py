# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""惑星ローバーの車輪の滑りを不確かさ付きで予測し、滑りのリスクを考えた経路を引く(規則 + 軽い統計、2026-10-06)。

柔らかい土(砂・レゴリス)の上では、車輪が回っても車体はその分だけ進まない。滑り率
``s = 1 − v / (r ω)``(v は車体の速さ、r ω は車輪の周速)は斜面が急になるほど大きくなり、1 に近づくと
ローバーは立ち往生する。地形の幾何(傾き・段差)だけの走行可否(``terrain.traversability``)には
この「土が支えきれない」効果が入っていない。この module は次の連鎖を学習なしの物理と軽い統計で組む:

1. **Bekker の圧力–沈下** ``p = (k_c / b + k_φ) zⁿ`` と、**Wong–Reece の車輪の応力分布**(剛な車輪、
   接地角の数値積分)から、荷重・滑り率ごとの沈下・牽引力(drawbar pull)・駆動トルク。
2. 斜面の角 → 定常の滑り率の曲線(斜面方向の重力成分を牽引力でちょうど支える滑り率)と、登れる最大の角。
3. 実際の滑り率を、地面を見下ろすカメラの像の並進(相互相関 + 勾配法の副画素)と車輪の回転角から測る。
4. 滑り率の不確かさ: ガウス過程(RBF、超パラメータは周辺尤度の格子探索)と分位点回帰(区分線形の基底、
   IRLS)の 2 通り、numpy だけ。
5. CVaR(条件付き期待値で測った上側の尾)を辺ごとの所要時間に入れたコスト地図と、8 近傍の Dijkstra。

一次情報で確かめた定義と式(読んだものだけ):

- **Bekker の圧力–沈下**: ``p = (k_c / b + k_φ) zⁿ``。``k_c`` [kN/m^(n+1)]、``k_φ`` [kN/m^(n+2)]、``b`` は車輪の幅
  (板の短辺)[m]、``z`` は沈下 [m]。
- **Wong–Reece の応力分布**(剛な車輪、半径 r、幅 b、角 θ は車輪の真下から前向きに正): 進入角
  ``θ_f = atan2(sqrt(z (2r − z)), r − z)``(``cos θ_f = 1 − z/r`` と同じ。acos は端で丸めの床があるので使わない)、
  最大応力の角 ``θ_m = (a₀ + a₁ s) θ_f``、離脱角 ``θ_r = (b₀ + b₁ s) θ_f``(b₀ < 0 で車輪の後ろ側も接地)。
  垂直応力は前側 ``σ = k rⁿ (cos θ − cos θ_f)ⁿ``(θ_m ≤ θ ≤ θ_f)、後側は角を
  ``θ′ = θ_f − (θ − θ_r)/(θ_m − θ_r) · (θ_f − θ_m)`` に写して同じ式(θ_r ≤ θ < θ_m)。
  せん断応力は Janosi–Hanamoto ``τ = (c + σ tan φ)(1 − exp(−j/K))``、せん断変位
  ``j(θ) = r [(θ_f − θ) − (1 − s)(sin θ_f − sin θ)]``(j < 0 は逆向きのせん断、制動)。
  力は ``F_z = r b ∫ (σ cos θ + τ sin θ) dθ``、``DP = r b ∫ (τ cos θ − σ sin θ) dθ``、``T = r² b ∫ τ dθ``
  (θ_r から θ_f まで、Gauss–Legendre の数値積分を前側・後側で分けて)。式の形は arXiv:2606.06790 の式 (13)〜(21)
  (Bekker–Wong の定式化の要約)で照合した。
- **閉形式の恒等式**(後側の接地なし ``a₀ = a₁ = b₀ = b₁ = 0`` のとき厳密): τ = 0 なら
  ``DP = −b k z^(n+1) / (n + 1)``(Bekker の締め固め抵抗)、n = 1 なら ``F_z = b k r² (θ_f − sin θ_f cos θ_f) / 2``。
  小さな沈下では Bekker の剛な車輪の近似 ``z = [3W / ((3 − n) b k sqrt(D))]^(2/(2n+1))`` に収束する
  (:func:`bekker_wheel_sinkage`)。
- **定常の滑り**: 質量 m、車輪 N 本、重力 g、斜面の角 β で、1 輪あたり ``F_z = m g cos β / N`` を支えながら
  ``DP = m g sin β / N`` を出す滑り率(斜面の横方向・車輪間の荷重移動は入れない)。
- **CVaR**: 上側 α の尾の期待値。正規分布なら ``CVaR_α = μ + σ φ(Φ⁻¹(α)) / (1 − α)``(α = 0 で平均)。
  分位点の曲線からは ``(1/(1 − α)) ∫_α^1 Q(u) du`` を、当てはめた分位点の段で台形則で近似する。
- **辺の所要時間**: 辺の長さ L を、悲観的な滑り ρ(登り・平地は CVaR(s)、下りは CVaR(−s) = 横滑り・空走の
  大きさ)で割り引いた速さ ``v (1 − ρ)`` で割る。ρ ≥ ``s_max`` の辺は通れない。

土の定数 :data:`SOILS` の出典は各項目に書いた(読んだ表から写した値だけ)。

失敗はすべて ``ValueError``(綴り違い・空・非有限・形の不一致・範囲外)。全部 numpy(scipy は使わない)。

呼び出し例(台帳の op を繋ぐ。tests/test_roverslip.py の test_19 が実行する)::

    import numpy as np
    import roverslip
    wheel = {"r": 0.15, "b": 0.12}                                  # 車輪の半径・幅 [m]
    sc = roverslip.slope_slip_curve(np.array([0.0, 10.0, 20.0, 30.0]), wheel, "dry_sand", mass=50.0, n_wheels=4)
    ok = sc["feasible"]                                             # 30° は登れない(slip = nan、feasible = False)
    rng = np.random.default_rng(0)
    x = rng.uniform(-15, 20, 120)                                   # 走りながら測った傾き [deg]
    y = np.interp(x, sc["slope"][ok], sc["slip"][ok]) + rng.normal(0, 0.02, x.size)   # 測った滑り(例のための合成)
    qr = roverslip.slip_quantile_fit(x, y)                          # 分位点回帰 + 共形の補正
    i, j = np.mgrid[0:24, 0:24]
    dtm = 1.2 * np.exp(-((i - 12) ** 2 + (j - 11) ** 2) / 40.0)     # 高さ 1.2 m の丘、格子 1 m
    cm = roverslip.cvar_cost_map(dtm, 1.0, qr, alpha=0.9)           # CVaR で割り引いた辺の所要時間
    pth = roverslip.risk_aware_path(cm, (1, 1), (22, 22))
    ev = roverslip.path_slip_risk(pth["path"], dtm, 1.0, qr, alpha=0.9)
    print(np.round(sc["slip"][ok], 3), round(sc["max_slope"], 1), pth["reached"], round(ev["length"], 1), round(ev["max_cvar_slip"], 3))
"""
from __future__ import annotations

import heapq
import math
from statistics import NormalDist

import numpy as np

__all__ = [
    "SOILS",
    "bekker_pressure", "bekker_wheel_sinkage", "wheel_forces", "wheel_sinkage",
    "wheel_traction_curve", "slope_slip_curve",
    "ground_shift_track", "odometry_slip",
    "slip_gp_fit", "slip_quantile_fit", "slip_predict", "slip_cvar",
    "cvar_cost_map", "risk_aware_path", "path_slip_risk",
]

#: 土の定数。単位: n [-]、kc [kN/m^(n+1)]、kphi [kN/m^(n+2)]、c [kPa]、phi [deg]、K [m] (せん断変形係数)、
#: a0・a1(最大応力の角)、b0・b1(離脱角)。
#: 出典: arXiv:2606.06790v2(2026)の表 2 を 2026-10-06 に PDF から読んで写した。"dry_sand" はその表の
#: 乾いた砂(元の値は Jia, Smith & Peng, Robotica 31 (2013)、c・φ・n は著者らが牽引試験に合わせて調整した値)、
#: "mars_simulant_m90" は同じ表の M90 火星模擬土(元は Oravec et al., Earth and Space 2021、調整なし。
#: a・b は乾いた砂と同じ値を流用と表に注記)。
#: "rigid_ground" は剛な地面の極限(MuJoCo の剛体接触と比べる門のための人工の土、文献値ではない)。
SOILS = {
    "dry_sand": {"n": 1.9, "kc": 10.3, "kphi": 5309.4, "c": 1.2, "phi": 33.3, "K": 0.015,
                 "a0": 0.43, "a1": 0.32, "b0": -0.16, "b1": 0.0,
                 "source": "arXiv:2606.06790 表 2(dry sand、元 Jia+ 2013 Robotica、c・phi・n は調整値)"},
    "mars_simulant_m90": {"n": 1.3, "kc": 572.1, "kphi": 4915.3, "c": 2.0, "phi": 35.0, "K": 0.0254,
                          "a0": 0.43, "a1": 0.32, "b0": -0.16, "b1": 0.0,
                          "source": "arXiv:2606.06790 表 2(M90 Mars simulant、元 Oravec+ 2021)"},
    "rigid_ground": {"n": 1.0, "kc": 0.0, "kphi": 5.0e7, "c": 0.0, "phi": 26.565051177077990, "K": 1.0e-5,
                     "a0": 0.0, "a1": 0.0, "b0": 0.0, "b1": 0.0,
                     "source": "人工(剛な地面の極限、tan φ = 0.5)"},
}

_SOIL_KEYS = ("n", "kc", "kphi", "c", "phi", "K", "a0", "a1", "b0", "b1")
_NQ = 96                                    # 前側・後側それぞれの Gauss–Legendre の点数
_GL = {}


def _gl(nq: int):
    if nq not in _GL:
        _GL[nq] = np.polynomial.legendre.leggauss(nq)
    return _GL[nq]


# ======================================================================================================================
# 入力の検査
def _soil(soil, op: str) -> dict:
    if isinstance(soil, str):
        if soil not in SOILS:
            raise ValueError("%s: soil %r は無い(%s)" % (op, soil, ", ".join(sorted(SOILS))))
        soil = SOILS[soil]
    if not isinstance(soil, dict):
        raise ValueError("%s: soil は名前か dict" % op)
    out = {}
    for k in _SOIL_KEYS:
        if k not in soil:
            raise ValueError("%s: soil に %r が無い" % (op, k))
        v = float(soil[k])
        if not math.isfinite(v):
            raise ValueError("%s: soil[%r] が非有限" % (op, k))
        out[k] = v
    if out["n"] <= 0 or out["kc"] < 0 or out["kphi"] < 0 or out["kc"] + out["kphi"] <= 0:
        raise ValueError("%s: soil の n > 0、kc・kphi ≥ 0(和は正)" % op)
    if out["c"] < 0 or not (0 <= out["phi"] < 90) or out["K"] <= 0:
        raise ValueError("%s: soil の c ≥ 0、0 ≤ phi < 90、K > 0" % op)
    return out


def _wheel(wheel, op: str):
    if not isinstance(wheel, dict) or "r" not in wheel or "b" not in wheel:
        raise ValueError("%s: wheel は {'r': 半径 [m], 'b': 幅 [m]}" % op)
    r, b = float(wheel["r"]), float(wheel["b"])
    if not (math.isfinite(r) and math.isfinite(b) and r > 0 and b > 0):
        raise ValueError("%s: wheel の r・b は正の有限値" % op)
    return r, b


def _finite_pos(x, name: str, op: str, allow_zero: bool = False) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ValueError("%s: %s は数" % (op, name)) from None
    if not math.isfinite(v) or v < 0 or (v == 0 and not allow_zero):
        raise ValueError("%s: %s は正の有限値" % (op, name))
    return v


def _arr(x, name: str, op: str, ndim=None, min_size: int = 1) -> np.ndarray:
    try:
        a = np.asarray(x, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s: %s は数の配列" % (op, name)) from None
    if ndim is not None and a.ndim != ndim:
        raise ValueError("%s: %s は %d 次元" % (op, name, ndim))
    if a.size < min_size:
        raise ValueError("%s: %s が空(少なくとも %d 個)" % (op, name, min_size))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: %s に非有限値" % (op, name))
    return a


# ======================================================================================================================
# 1. Bekker と Wong–Reece
def bekker_pressure(sinkage, width, soil) -> np.ndarray:
    """Bekker の圧力–沈下 ``p = (k_c / b + k_φ) zⁿ`` [kPa]。``sinkage`` [m] はスカラーか配列(≥ 0)、``width`` = b [m]。

    返りは ``sinkage`` と同じ形の配列(スカラーなら 0 次元)。z = 0 で 0、z について単調に増える。
    """
    S = _soil(soil, "bekker_pressure")
    b = _finite_pos(width, "width", "bekker_pressure")
    z = _arr(sinkage, "sinkage", "bekker_pressure")
    if np.any(z < 0):
        raise ValueError("bekker_pressure: sinkage ≥ 0")
    return (S["kc"] / b + S["kphi"]) * z ** S["n"]


def bekker_wheel_sinkage(load, wheel, soil, form: str = "classic") -> float:
    """Bekker の剛な車輪の沈下の近似式 [m]。接地を放物線 ``z(x) = z₀ − x²/D`` で近似し、せん断は入れない。

    ``load`` は 1 輪の垂直荷重 [N]、D = 2r、``k = k_c/b + k_φ``。荷重は ``W = b k sqrt(D) z₀^(n+1/2) · I(n)``、
    ``I(n) = ∫₀¹ (1 − t²)ⁿ dt``。
    ``form = "classic"``: Bekker の教科書の式 ``z = [3W / ((3 − n) b k sqrt(D))]^(2/(2n+1))``。これは
    ``(1 − t²)ⁿ ≈ 1 − n t²`` と置いた ``I(n) ≈ (3 − n)/3`` で、**n = 1 でだけ厳密**(n = 1.9 では I を 21 % 大きく
    見積もり、沈下を 17 % 深く出す —— 2026-10-06 の試作で数値積分と比べて見つけた)。
    ``form = "parabolic"``: 同じ放物線のまま ``I(n) = √π Γ(n+1) / (2 Γ(n + 3/2))`` を厳密に使う。小さな沈下
    (z ≪ D)で :func:`wheel_sinkage` の数値積分(後側の接地なし、τ = 0)に収束する。
    """
    S = _soil(soil, "bekker_wheel_sinkage")
    r, b = _wheel(wheel, "bekker_wheel_sinkage")
    W = _finite_pos(load, "load", "bekker_wheel_sinkage")
    n = S["n"]
    if form == "classic":
        if n >= 3:
            raise ValueError("bekker_wheel_sinkage: classic の式は n < 3 でだけ定義される")
        I = (3.0 - n) / 3.0
    elif form == "parabolic":
        I = math.sqrt(math.pi) * math.gamma(n + 1.0) / (2.0 * math.gamma(n + 1.5))
    else:
        raise ValueError("bekker_wheel_sinkage: form は 'classic' か 'parabolic'")
    k = (S["kc"] / b + S["kphi"]) * 1e3                 # kN → N
    return float((W / (b * k * math.sqrt(2.0 * r) * I)) ** (2.0 / (2.0 * n + 1.0)))


def _angles(z, s, r, S):
    """進入角・最大応力の角・離脱角(配列どうしの放送)。"""
    tf = np.arctan2(np.sqrt(np.maximum(z * (2.0 * r - z), 0.0)), r - z)
    tm = np.clip((S["a0"] + S["a1"] * s) * tf, None, tf)
    tr = np.minimum((S["b0"] + S["b1"] * s) * tf, tm)
    tm = np.maximum(tm, tr)
    return tf, tm, tr


def _forces(z, s, r, b, S, nq: int = _NQ):
    """Wong–Reece の力(配列 z・s を放送、返りは同じ形)。単位 N / N·m。"""
    z = np.asarray(z, np.float64)
    s = np.asarray(s, np.float64)
    z, s = np.broadcast_arrays(z, s)
    tf, tm, tr = _angles(z, s, r, S)
    xg, wg = _gl(nq)
    k = (S["kc"] / b + S["kphi"]) * 1e3                 # N/m^(n+2)
    n = S["n"]
    c = S["c"] * 1e3
    tphi = math.tan(math.radians(S["phi"]))
    K = S["K"]
    cf = np.cos(tf)[..., None]
    sf = np.sin(tf)[..., None]
    tf_ = tf[..., None]
    out = {"Fz": 0.0, "DP": 0.0, "T": 0.0}
    for lo, hi, rear in ((tm, tf, False), (tr, tm, True)):
        half = 0.5 * (hi - lo)[..., None]
        th = 0.5 * (hi + lo)[..., None] + half * xg
        w = half * wg
        if rear:
            den = (tm - tr)[..., None]
            frac = np.divide(th - tr[..., None], den, out=np.zeros_like(th), where=den > 0)
            thp = tf_ - frac * (tf_ - tm[..., None])
        else:
            thp = th
        sig = k * r ** n * np.maximum(np.cos(thp) - cf, 0.0) ** n
        j = r * ((tf_ - th) - (1.0 - s[..., None]) * (sf - np.sin(th)))
        tau = np.sign(j) * (c + sig * tphi) * (1.0 - np.exp(-np.abs(j) / K))
        out["Fz"] = out["Fz"] + r * b * np.sum(w * (sig * np.cos(th) + tau * np.sin(th)), axis=-1)
        out["DP"] = out["DP"] + r * b * np.sum(w * (tau * np.cos(th) - sig * np.sin(th)), axis=-1)
        out["T"] = out["T"] + r * r * b * np.sum(w * tau, axis=-1)
    out.update(theta_f=tf, theta_m=tm, theta_r=tr)
    return out


def wheel_forces(sinkage, slip, wheel, soil, n_quad: int = _NQ) -> dict:
    """沈下 z [m] と滑り率 s で、剛な車輪が土から受ける力(Wong–Reece の応力分布の数値積分)。

    返り値 ``{"Fz", "DP", "T", "theta_f", "theta_m", "theta_r"}``: 垂直力 [N]、牽引力(drawbar pull、前向き正)[N]、
    駆動トルク [N·m]、角 [rad]。``sinkage``・``slip`` はスカラーか同じ形に放送できる配列(0 ≤ z < r、−1 < s < 1)。
    """
    S = _soil(soil, "wheel_forces")
    r, b = _wheel(wheel, "wheel_forces")
    z = _arr(sinkage, "sinkage", "wheel_forces")
    s = _arr(slip, "slip", "wheel_forces")
    if np.any(z < 0) or np.any(z >= r):
        raise ValueError("wheel_forces: 0 ≤ sinkage < r")
    if np.any(np.abs(s) >= 1):
        raise ValueError("wheel_forces: −1 < slip < 1")
    nq = int(n_quad)
    if nq < 8 or nq > 2048:
        raise ValueError("wheel_forces: n_quad は 8〜2048")
    f = _forces(z, s, r, b, S, nq)
    return {k: (float(v) if np.ndim(v) == 0 else np.asarray(v)) for k, v in f.items()}


def _solve_sinkage(load, s, r, b, S, iters: int = 60):
    """F_z(z, s) = load を z について二分法(配列で同時に)。F_z が届かなければ nan。"""
    load, s = np.broadcast_arrays(np.asarray(load, np.float64), np.asarray(s, np.float64))
    lo = np.zeros(load.shape)
    hi = np.full(load.shape, 0.999 * r)
    fhi = _forces(hi, s, r, b, S)["Fz"]
    bad = fhi < load
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        f = _forces(mid, s, r, b, S)["Fz"]
        up = f < load
        lo = np.where(up, mid, lo)
        hi = np.where(up, hi, mid)
    z = 0.5 * (lo + hi)
    return np.where(bad, np.nan, z)


def wheel_sinkage(load, wheel, soil, slip=0.0) -> np.ndarray:
    """1 輪の垂直荷重 ``load`` [N] を滑り率 ``slip`` で支える沈下 z [m] (F_z(z, s) = load の二分法)。

    ``load``・``slip`` は放送できる配列。車輪の半径まで沈んでも支えられない荷重は ValueError。
    """
    S = _soil(soil, "wheel_sinkage")
    r, b = _wheel(wheel, "wheel_sinkage")
    W = _arr(load, "load", "wheel_sinkage")
    s = _arr(slip, "slip", "wheel_sinkage")
    if np.any(W <= 0):
        raise ValueError("wheel_sinkage: load > 0")
    if np.any(np.abs(s) >= 1):
        raise ValueError("wheel_sinkage: −1 < slip < 1")
    z = _solve_sinkage(W, s, r, b, S)
    if np.any(~np.isfinite(z)):
        raise ValueError("wheel_sinkage: 車輪の半径まで沈んでも荷重を支えられない(土が柔らかすぎる・荷重が大きすぎる)")
    return z


def wheel_traction_curve(load, wheel, soil, slips=None) -> dict:
    """1 輪の荷重 ``load`` [N] を一定に保ったときの、滑り率ごとの沈下・牽引力・トルク(牽引–滑り曲線)。

    ``slips`` の既定は 0〜0.95 の 40 点。返り値 ``{"slip", "sinkage", "DP", "T", "DP_over_W", "efficiency"}``
    (``efficiency`` = 牽引の仕事率 / 駆動の仕事率 = DP (1 − s) r / T、T ≤ 0 の点は 0)。
    """
    S = _soil(soil, "wheel_traction_curve")
    r, b = _wheel(wheel, "wheel_traction_curve")
    W = _finite_pos(load, "load", "wheel_traction_curve")
    s = np.linspace(0.0, 0.95, 40) if slips is None else _arr(slips, "slips", "wheel_traction_curve", ndim=1)
    if np.any(np.abs(s) >= 1):
        raise ValueError("wheel_traction_curve: −1 < slip < 1")
    z = _solve_sinkage(np.full(s.shape, W), s, r, b, S)
    if np.any(~np.isfinite(z)):
        raise ValueError("wheel_traction_curve: 荷重を支えられない滑り率がある")
    f = _forces(z, s, r, b, S)
    T = f["T"]
    eff = np.where(T > 0, f["DP"] * (1.0 - s) * r / np.where(T > 0, T, 1.0), 0.0)
    return {"slip": s, "sinkage": z, "DP": f["DP"], "T": T, "DP_over_W": f["DP"] / W, "efficiency": eff}


def slope_slip_curve(slopes_deg, wheel, soil, mass: float, n_wheels: int = 6, gravity: float = 3.72,
                     s_min: float = -0.9, s_max: float = 0.99) -> dict:
    """斜面の角(度、登りが正)ごとに、車体の重さを支えつつ斜面方向の重力成分を牽引力で釣り合わせる定常の滑り率。

    1 輪あたり ``F_z = m g cos β / N``、必要な牽引力 ``m g sin β / N``。滑り率を [s_min, s_max] で二分法
    (内側で沈下も二分法)。``s_max`` でも牽引力が足りない角は ``feasible = False``・``slip = nan``(立ち往生)、
    下りで ``s_min`` でも止まれない角も同じ。既定の重力は火星 3.72 m/s²。
    返り値 ``{"slope", "slip", "sinkage", "feasible", "max_slope"}``(``max_slope`` は登れる最大の角の内挿 [deg]、
    範囲内に限界が無ければ nan)。
    """
    S = _soil(soil, "slope_slip_curve")
    r, b = _wheel(wheel, "slope_slip_curve")
    beta = _arr(slopes_deg, "slopes_deg", "slope_slip_curve", ndim=1)
    if np.any(np.abs(beta) >= 89):
        raise ValueError("slope_slip_curve: |slope| < 89°")
    m = _finite_pos(mass, "mass", "slope_slip_curve")
    g = _finite_pos(gravity, "gravity", "slope_slip_curve")
    N = int(n_wheels)
    if N < 1:
        raise ValueError("slope_slip_curve: n_wheels ≥ 1")
    if not (-1 < s_min < 0 < s_max < 1):
        raise ValueError("slope_slip_curve: −1 < s_min < 0 < s_max < 1")
    br = np.radians(beta)
    Wn = m * g * np.cos(br) / N
    need = m * g * np.sin(br) / N

    def dp(s):
        z = _solve_sinkage(Wn, s, r, b, S, iters=48)
        f = _forces(np.nan_to_num(z, nan=0.5 * r), s, r, b, S)["DP"]
        return np.where(np.isfinite(z), f, -np.inf), z

    lo = np.full(beta.shape, float(s_min))
    hi = np.full(beta.shape, float(s_max))
    dlo, _ = dp(lo)
    dhi, _ = dp(hi)
    feasible = (dlo <= need) & (dhi >= need)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        d, _ = dp(mid)
        up = d < need
        lo = np.where(up, mid, lo)
        hi = np.where(up, hi, mid)
    s = 0.5 * (lo + hi)
    _, z = dp(s)
    s = np.where(feasible, s, np.nan)
    z = np.where(feasible, z, np.nan)
    # 登れる最大の角: 「s_max で出せる牽引 / 必要な牽引」が 1 を跨ぐ角を内挿
    ratio = dhi - need
    max_slope = float("nan")
    up_idx = np.argsort(beta)
    bs, rs = beta[up_idx], ratio[up_idx]
    for i in range(len(bs) - 1):
        if bs[i] >= 0 and rs[i] >= 0 > rs[i + 1]:
            max_slope = float(bs[i] + (bs[i + 1] - bs[i]) * rs[i] / (rs[i] - rs[i + 1]))
            break
    return {"slope": beta, "slip": s, "sinkage": z, "feasible": feasible, "max_slope": max_slope}


# ======================================================================================================================
# 2. 実際の滑り率(視覚オドメトリ + 車輪の回転)
def _bilinear(img, dr, dc):
    """img を (dr, dc) だけずらした位置で双線形に標本化(外は False の印)。"""
    H, W = img.shape
    i, j = np.mgrid[0:H, 0:W].astype(np.float64)
    y, x = i + dr, j + dc
    y0 = np.floor(y).astype(np.int64)
    x0 = np.floor(x).astype(np.int64)
    fy, fx = y - y0, x - x0
    ok = (y0 >= 0) & (x0 >= 0) & (y0 < H - 1) & (x0 < W - 1)
    y0 = np.clip(y0, 0, H - 2)
    x0 = np.clip(x0, 0, W - 2)
    v = (img[y0, x0] * (1 - fy) * (1 - fx) + img[y0 + 1, x0] * fy * (1 - fx)
         + img[y0, x0 + 1] * (1 - fy) * fx + img[y0 + 1, x0 + 1] * fy * fx)
    return v, ok


def _phase_shift(a, b, win, iters: int = 30):
    """b の模様が a に対してどれだけずれたか (drow, dcol) [px]、副画素。

    1) 整数の初期値: Hann 窓をかけた相互相関の山。相互パワースペクトルは振幅の平方根だけで割る(半分の白色化)。
       全部割る位相相関は、帯域制限の模様と窓の組で窓どうしの相関(ずれ 0)に引かれ、試作の測りで 6 px 外れた。
    2) 副画素: 並進だけの Lucas–Kanade(Gauss–Newton、双線形の標本化、縁 4 px を除く)で ``b(x) ≈ a(x − d)`` を解く。
       位相相関の山を局所 DFT で細かくしても窓の偏り(0.5 px 前後)は消えなかったので、勾配法で詰める。
    返り値 (drow, dcol, 正規化した相関の山の高さ)。
    """
    A = np.fft.fft2((a - a.mean()) * win)
    B = np.fft.fft2((b - b.mean()) * win)
    R = np.conj(A) * B
    R /= np.sqrt(np.abs(R)) + 1e-12
    corr = np.fft.ifft2(R).real
    H, W = corr.shape
    i, j = np.unravel_index(int(np.argmax(corr)), corr.shape)
    dr = float(i - H if i > H // 2 else i)
    dc = float(j - W if j > W // 2 else j)
    gy, gx = np.gradient(a)
    m_edge = np.zeros((H, W), dtype=bool)
    m_edge[4:-4, 4:-4] = True
    for _ in range(int(iters)):
        aw, ok = _bilinear(a, -dr, -dc)
        gyw, _ = _bilinear(gy, -dr, -dc)
        gxw, _ = _bilinear(gx, -dr, -dc)
        m = ok & m_edge
        if m.sum() < 16:
            raise ValueError("ground_shift_track: 重なりが小さすぎる(1 コマの移動が大きすぎる)")
        J = np.stack([-gyw[m], -gxw[m]], axis=1)
        delta = np.linalg.lstsq(J, (b - aw)[m], rcond=None)[0]
        dr += float(delta[0])
        dc += float(delta[1])
        if np.max(np.abs(delta)) < 1e-6:
            break
    aw, ok = _bilinear(a, -dr, -dc)
    m = ok & m_edge
    u, v = aw[m] - aw[m].mean(), b[m] - b[m].mean()
    peak = float(u @ v / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-300))
    return dr, dc, peak


def ground_shift_track(frames, pixel_size: float = 1.0) -> dict:
    """地面を見下ろすカメラのコマ列から、隣り合うコマの並進を、窓つきの相互相関(整数)と
    並進の Lucas–Kanade(副画素)で測り、累積する。

    ``frames`` は (T, H, W) の配列か同じ形の 2-D 配列の列(T ≥ 2)。``pixel_size`` は地面での画素の大きさ [m]。
    返り値 ``{"step": (T−1, 2) の (drow, dcol) [m]、"position": (T, 2) の累積 [m]、"peak": (T−1,) 合わせた後の正規化相関}``。
    ``step`` は **像の中で模様が動いた量**(カメラ・車体の移動はその逆向き —— 前に進むと地面は後ろへ流れる)。
    1 コマの移動は像の 1/4 程度まで(相関は周期的なので、半分を越えると折り返す)。
    """
    try:
        F = np.asarray(frames, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("ground_shift_track: frames は同じ形の 2-D 配列の列") from None
    if F.ndim != 3 or F.shape[0] < 2 or min(F.shape[1:]) < 8:
        raise ValueError("ground_shift_track: frames は (T ≥ 2, H ≥ 8, W ≥ 8)")
    if not np.all(np.isfinite(F)):
        raise ValueError("ground_shift_track: frames に非有限値")
    px = _finite_pos(pixel_size, "pixel_size", "ground_shift_track")
    H, W = F.shape[1:]
    win = np.outer(np.hanning(H), np.hanning(W))
    steps, peaks = [], []
    for t in range(F.shape[0] - 1):
        if np.ptp(F[t]) == 0 or np.ptp(F[t + 1]) == 0:
            raise ValueError("ground_shift_track: 定数のコマ %d(模様が無いと並進は決まらない)" % t)
        dr, dc, pk = _phase_shift(F[t], F[t + 1], win)
        steps.append((dr * px, dc * px))
        peaks.append(pk)
    st = np.asarray(steps)
    pos = np.vstack([np.zeros((1, 2)), np.cumsum(st, axis=0)])
    return {"step": st, "position": pos, "peak": np.asarray(peaks)}


def odometry_slip(position, wheel_angle, radius: float, window: int = 1) -> dict:
    """視覚オドメトリの位置の列と車輪の累積回転角から、実際の滑り率 ``s = 1 − Δx / (r Δφ)``。

    ``position`` は (T,) の進んだ距離か (T, 2) の平面の位置 [m]、``wheel_angle`` は (T,) の車輪の累積回転角 [rad]、
    ``radius`` = r [m]。``window`` 個ぶんの区間でまとめて割る(短い区間は雑音を拾う)。車輪がほとんど回らない
    区間(``r Δφ`` が全体の中央値の 1 % 未満)は nan。返り値 ``{"slip": (T − window,), "slip_total": 全区間の 1 個,
    "distance": 区間ごとの車体の移動 [m], "wheel_travel": 区間ごとの r Δφ [m]}``。
    """
    P = _arr(position, "position", "odometry_slip")
    A = _arr(wheel_angle, "wheel_angle", "odometry_slip", ndim=1, min_size=2)
    r = _finite_pos(radius, "radius", "odometry_slip")
    if P.ndim == 1:
        P = P[:, None]
    if P.ndim != 2 or P.shape[0] != A.shape[0]:
        raise ValueError("odometry_slip: position (T,) か (T, 2) と wheel_angle (T,) の T が一致しない")
    w = int(window)
    if w < 1 or w >= A.shape[0]:
        raise ValueError("odometry_slip: 1 ≤ window < T")
    d = np.linalg.norm(P[w:] - P[:-w], axis=1)
    if P.shape[1] == 1:
        d = (P[w:, 0] - P[:-w, 0])                   # 1-D は符号つき(後ずさり = 滑り > 1)
    wt = r * (A[w:] - A[:-w])
    tot_w = r * (A[-1] - A[0])
    if abs(tot_w) <= 0:
        raise ValueError("odometry_slip: 車輪が回っていない(Δφ = 0)")
    med = np.median(np.abs(wt))
    ok = np.abs(wt) > max(0.01 * med, 1e-15)
    s = np.where(ok, 1.0 - d / np.where(ok, wt, 1.0), np.nan)
    dtot = np.linalg.norm(P[-1] - P[0]) if P.shape[1] > 1 else P[-1, 0] - P[0, 0]
    return {"slip": s, "slip_total": float(1.0 - dtot / tot_w), "distance": d, "wheel_travel": wt}


# ======================================================================================================================
# 3. 不確かさ(ガウス過程・分位点回帰)
def _rbf(a, b, ell):
    return np.exp(-0.5 * ((a[:, None] - b[None, :]) / ell) ** 2)


def slip_gp_fit(slopes, slips, length_scales=None, noise_levels=None) -> dict:
    """斜面の角 → 滑り率のガウス過程(RBF の核 + 一様な観測雑音)。超パラメータは対数周辺尤度の格子探索。

    y は平均を引いて標準偏差で割ってから当てはめる(信号の分散 σ_f² = 1 に固定、ℓ と雑音 σ_n を探す)。
    ``length_scales`` の既定は角の範囲の 0.05〜2 倍の 16 段(対数)、``noise_levels`` は 0.01〜1(正規化した y の単位)の
    16 段。返り値は予測に使う dict(``kind = "gp"``、``x``・``alpha``・``L``・``ell``・``noise``・``y_mean``・``y_scale``・
    ``log_marginal_likelihood``)。雑音が角によって変わる(異分散)データでは、帯は全体の平均の幅になる(門の罠)。
    """
    x = _arr(slopes, "slopes", "slip_gp_fit", ndim=1, min_size=3)
    y = _arr(slips, "slips", "slip_gp_fit", ndim=1, min_size=3)
    if x.shape != y.shape:
        raise ValueError("slip_gp_fit: slopes と slips の長さが違う")
    if np.ptp(x) == 0:
        raise ValueError("slip_gp_fit: 角がすべて同じ(関数として当てはめられない)")
    ym, ys = float(y.mean()), float(y.std())
    ys = ys if ys > 0 else 1.0
    yn = (y - ym) / ys
    span = float(np.ptp(x))
    ells = np.geomspace(0.05 * span, 2.0 * span, 16) if length_scales is None else _arr(length_scales, "length_scales", "slip_gp_fit", ndim=1)
    nls = np.geomspace(0.01, 1.0, 16) if noise_levels is None else _arr(noise_levels, "noise_levels", "slip_gp_fit", ndim=1)
    if np.any(ells <= 0) or np.any(nls <= 0):
        raise ValueError("slip_gp_fit: length_scales・noise_levels は正")
    best = None
    n = x.size
    for ell in ells:
        # ℓ ごとに核を 1 回だけ固有分解し、雑音の段は (λ + σ²) の対角で回す(Cholesky を 1 段ずつ回すより速い)
        lam, U = np.linalg.eigh(_rbf(x, x, ell))
        lam = np.maximum(lam, 0.0)
        uy = U.T @ yn
        for sn in nls:
            d = lam + sn * sn + 1e-10
            lml = -0.5 * float(np.sum(uy * uy / d)) - 0.5 * float(np.sum(np.log(d))) - 0.5 * n * math.log(2 * math.pi)
            if best is None or lml > best[0]:
                best = (lml, ell, sn)
    if best is None:
        raise ValueError("slip_gp_fit: 超パラメータの候補が空")
    lml, ell, sn = best
    try:
        L = np.linalg.cholesky(_rbf(x, x, ell) + (sn * sn + 1e-10) * np.eye(n))
    except np.linalg.LinAlgError:
        raise ValueError("slip_gp_fit: 選んだ超パラメータで Cholesky が通らない") from None
    a = np.linalg.solve(L.T, np.linalg.solve(L, yn))
    best = (lml, ell, sn, L, a)
    lml, ell, sn, L, a = best
    return {"kind": "gp", "x": x, "alpha": a, "L": L, "ell": float(ell), "noise": float(sn),
            "y_mean": ym, "y_scale": ys, "log_marginal_likelihood": float(lml), "n": int(n),
            "x_range": (float(x.min()), float(x.max()))}


def _hat_basis(x, knots):
    """区分線形の基底(端は直線で外挿)。"""
    x = np.asarray(x, np.float64)
    k = np.asarray(knots, np.float64)
    B = np.zeros((x.size, k.size))
    xc = np.clip(x, k[0], k[-1])
    idx = np.clip(np.searchsorted(k, xc, side="right") - 1, 0, k.size - 2)
    t = (xc - k[idx]) / (k[idx + 1] - k[idx])
    B[np.arange(x.size), idx] = 1 - t
    B[np.arange(x.size), idx + 1] += t
    # 範囲外は端の区間の傾きで外挿
    lo = x < k[0]
    hi = x > k[-1]
    if np.any(lo):
        t = (x[lo] - k[0]) / (k[1] - k[0])
        B[lo] = 0
        B[lo, 0] = 1 - t
        B[lo, 1] = t
    if np.any(hi):
        t = (x[hi] - k[-2]) / (k[-1] - k[-2])
        B[hi] = 0
        B[hi, -2] = 1 - t
        B[hi, -1] = t
    return B


def slip_quantile_fit(slopes, slips, quantiles=None, n_knots: int = 6, smooth: float = 1e-3, iters: int = 200,
                      calibrate: float = 0.25, level: float = 0.9, seed: int = 0) -> dict:
    """斜面の角 → 滑り率の分位点回帰(区分線形の基底、ピンボール損失を IRLS で、2 階差分の弱い罰則)。

    ``quantiles`` の既定は 0.05, 0.10, …, 0.95 の 19 段。節点は角の分位点に ``n_knots`` 個(データの疎な端に
    節点を置きすぎない)。当てはめの後、角ごとに分位点の曲線を並べ替えて交差を消す(rearrangement)。
    雑音が角で変わってもその角の帯の幅が追従する —— ガウス過程の一様な雑音との違い。
    ``calibrate`` > 0 なら、データのその割合を較正用に取り分けて(``seed`` で決まる無作為の分割)残りで当てはめ、
    両側 ``level`` の帯の幅を共形予測で補正する(Romano, Patterson & Candès 2019 の CQR: 較正点ごとに
    ``E = max(下端 − y, y − 上端)`` を取り、その ``⌈(n + 1) level⌉ / n`` 分位点だけ帯を両側に広げる / 狭める)。
    交換可能なデータなら帯の被覆は有限標本で ``level`` 以上(角ごとの被覆ではなく全体の被覆の保証)。
    IRLS の分位点回帰は標本の中で帯を狭く見積もりがち(試作の測りで名目 90 % に 82〜91 %)なので既定で入れる。
    返り値 ``{"kind": "quantile", "quantiles", "knots", "coef": (段, 節点), "conformal": {level: 幅の補正}}``。
    """
    x = _arr(slopes, "slopes", "slip_quantile_fit", ndim=1, min_size=5)
    y = _arr(slips, "slips", "slip_quantile_fit", ndim=1, min_size=5)
    if x.shape != y.shape:
        raise ValueError("slip_quantile_fit: slopes と slips の長さが違う")
    q = np.round(np.arange(0.05, 0.951, 0.05), 4) if quantiles is None else _arr(quantiles, "quantiles", "slip_quantile_fit", ndim=1)
    if np.any(q <= 0) or np.any(q >= 1) or np.any(np.diff(q) <= 0):
        raise ValueError("slip_quantile_fit: quantiles は (0, 1) で狭義増加")
    x_range = (float(x.min()), float(x.max()))
    cal = float(calibrate)
    if not (0 <= cal < 0.9):
        raise ValueError("slip_quantile_fit: 0 ≤ calibrate < 0.9")
    lv = float(level)
    if not (0 < lv < 1):
        raise ValueError("slip_quantile_fit: 0 < level < 1")
    xc = yc = None
    if cal > 0:
        perm = np.random.default_rng(int(seed)).permutation(x.size)
        nc = int(round(cal * x.size))
        if nc < 5 or x.size - nc < 5:
            raise ValueError("slip_quantile_fit: 較正用と当てはめ用にそれぞれ 5 点以上要る")
        xc, yc = x[perm[:nc]], y[perm[:nc]]
        x, y = x[perm[nc:]], y[perm[nc:]]
        lo_q, hi_q = round((1 - lv) / 2, 6), round((1 + lv) / 2, 6)
        if not (np.any(np.isclose(q, lo_q)) and np.any(np.isclose(q, hi_q))):
            raise ValueError("slip_quantile_fit: 較正する帯の端 %.3f・%.3f が quantiles に無い" % (lo_q, hi_q))
    nk = int(n_knots)
    if nk < 2 or nk > x.size // 2:
        raise ValueError("slip_quantile_fit: 2 ≤ n_knots ≤ データ数 / 2")
    knots = np.unique(np.quantile(x, np.linspace(0, 1, nk)))
    if knots.size < 2:
        raise ValueError("slip_quantile_fit: 角がすべて同じ")
    B = _hat_basis(x, knots)
    D = np.diff(np.eye(knots.size), 2, axis=0) if knots.size >= 3 else np.zeros((0, knots.size))
    lam = float(smooth) * x.size
    coef = np.zeros((q.size, knots.size))
    eps = 1e-6 * (float(np.ptp(y)) or 1.0)
    for qi, tau in enumerate(q):
        beta = np.linalg.lstsq(B, y, rcond=None)[0]
        for _ in range(int(iters)):
            res = y - B @ beta
            w = np.where(res >= 0, tau, 1.0 - tau) / np.maximum(np.abs(res), eps)
            A = B.T @ (w[:, None] * B) + lam * D.T @ D
            nb = np.linalg.solve(A + 1e-12 * np.eye(knots.size), B.T @ (w * y))
            if np.max(np.abs(nb - beta)) < 1e-9:
                beta = nb
                break
            beta = nb
        coef[qi] = beta
    model = {"kind": "quantile", "quantiles": q, "knots": knots, "coef": coef, "n": int(x.size), "conformal": {},
             "x_range": x_range}
    if xc is not None:
        Qc = _qr_curves(model, xc)
        lo = Qc[:, int(np.argmin(np.abs(q - (1 - lv) / 2)))]
        hi = Qc[:, int(np.argmin(np.abs(q - (1 + lv) / 2)))]
        E = np.maximum(lo - yc, yc - hi)
        k = min(int(math.ceil((E.size + 1) * lv)), E.size)
        model["conformal"] = {round(lv, 6): float(np.sort(E)[k - 1])}
        model["n_calibration"] = int(E.size)
    return model


def _model(model, op):
    if not isinstance(model, dict) or model.get("kind") not in ("gp", "quantile"):
        raise ValueError("%s: model は slip_gp_fit か slip_quantile_fit の返り値" % op)
    return model


def _gp_predict(M, x):
    Ks = _rbf(x, M["x"], M["ell"])
    mu = Ks @ M["alpha"]
    v = np.linalg.solve(M["L"], Ks.T)
    var_f = np.maximum(1.0 - np.sum(v * v, axis=0), 0.0)
    var_y = var_f + M["noise"] ** 2
    return M["y_mean"] + M["y_scale"] * mu, M["y_scale"] * np.sqrt(var_y), M["y_scale"] * np.sqrt(var_f)


def _qr_curves(M, x):
    Q = (_hat_basis(x, M["knots"]) @ M["coef"].T)       # (n, 段)
    return np.sort(Q, axis=1)                           # 交差を消す(並べ替え)


def slip_predict(model, slopes, level: float = 0.9) -> dict:
    """滑り率の予測と両側 ``level`` の帯。ガウス過程は観測の予測分布(潜在の分散 + 雑音)、分位点回帰は曲線そのもの。

    返り値 ``{"mean", "std", "lower", "upper", "median", "level"}``(各 (n,))。分位点回帰の ``mean`` は当てはめた
    分位点の平均、``std`` は四分位範囲 / 1.349、帯の端は (1 ± level)/2 の分位点(当てはめた段に無ければ ValueError)に、
    共形の補正(:func:`slip_quantile_fit` の ``conformal``)があればその幅を足す。
    """
    M = _model(model, "slip_predict")
    x = _arr(slopes, "slopes", "slip_predict", ndim=1)
    lv = float(level)
    if not (0 < lv < 1):
        raise ValueError("slip_predict: 0 < level < 1")
    if M["kind"] == "gp":
        mu, sd, _ = _gp_predict(M, x)
        z = NormalDist().inv_cdf(0.5 + lv / 2)
        return {"mean": mu, "std": sd, "lower": mu - z * sd, "upper": mu + z * sd, "median": mu, "level": lv}
    q = M["quantiles"]
    Q = _qr_curves(M, x)
    lo_q, hi_q = (1 - lv) / 2, (1 + lv) / 2

    def pick(u):
        i = np.where(np.isclose(q, u, atol=1e-9))[0]
        if i.size == 0:
            raise ValueError("slip_predict: 分位点 %.3f が当てはめた段に無い(quantiles を足す)" % u)
        return Q[:, i[0]]

    margin = float(M.get("conformal", {}).get(round(lv, 6), 0.0))
    q25 = np.array([np.interp(0.25, q, row) for row in Q])
    q75 = np.array([np.interp(0.75, q, row) for row in Q])
    return {"mean": Q.mean(axis=1), "std": (q75 - q25) / 1.349, "lower": pick(lo_q) - margin, "upper": pick(hi_q) + margin,
            "median": np.array([np.interp(0.5, q, row) for row in Q]), "level": lv}


def slip_cvar(model, slopes, alpha: float = 0.9, sign: float = 1.0) -> np.ndarray:
    """滑り率の CVaR_α(上側 1 − α の尾の条件付き期待値)。``sign = −1`` で −s の CVaR(下りの空走・横滑りの大きさ)。

    ガウス過程は閉形式 ``μ + σ φ(Φ⁻¹(α)) / (1 − α)``(α = 0 で平均、σ は観測の予測分布)。分位点回帰は
    ``(1/(1 − α)) ∫_α^{q_max} Q(u) du`` を当てはめた段で台形則に、``q_max`` より上の尾は最上段の値で埋める
    (尾を細く見積もる向きの近似 —— 段の外の分布は分からない)。返り値 (n,)。
    """
    M = _model(model, "slip_cvar")
    x = _arr(slopes, "slopes", "slip_cvar", ndim=1)
    a = float(alpha)
    if not (0 <= a < 1):
        raise ValueError("slip_cvar: 0 ≤ alpha < 1")
    sg = float(sign)
    if sg not in (1.0, -1.0):
        raise ValueError("slip_cvar: sign は +1 か −1")
    if M["kind"] == "gp":
        mu, sd, _ = _gp_predict(M, x)
        mu = sg * mu
        if a == 0:
            return mu
        za = NormalDist().inv_cdf(a)
        return mu + sd * math.exp(-0.5 * za * za) / math.sqrt(2 * math.pi) / (1 - a)
    q = M["quantiles"]
    Q = sg * _qr_curves(M, x)
    if sg < 0:                                          # −s の分位点 = s の (1 − u) 分位点を反転
        q = 1 - q[::-1]
        Q = Q[:, ::-1]
    if a < q[0]:
        grid = np.concatenate([[a], q])
        vals = np.hstack([Q[:, :1], Q])
    else:
        keep = q >= a
        grid = np.concatenate([[a], q[keep]])
        vals = np.hstack([np.array([np.interp(a, q, row) for row in Q])[:, None], Q[:, keep]])
    integ = np.sum(0.5 * (vals[:, 1:] + vals[:, :-1]) * np.diff(grid), axis=1)
    integ += vals[:, -1] * (1.0 - grid[-1])
    return integ / (1.0 - a)


# ======================================================================================================================
# 4. コスト地図と経路
_PITCH_GRID = np.linspace(-89.0, 89.0, 3561)         # 0.05° 刻み
_OFFS = np.array([(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)])


def cvar_cost_map(dtm, cell: float, model, alpha: float = 0.9, speed: float = 0.05, s_max: float = 0.9,
                  soil_map=None, extrapolate: bool = False) -> dict:
    """数値標高(DTM)から、8 近傍の辺ごとの所要時間 [s] を、辺の傾き(進む向きの符号つき)の滑りの CVaR_α で割り引いて作る。

    ``dtm`` (H, W) [m]、``cell`` [m]。辺 (i, j) → 近傍 k の傾き ``θ = atan2(Δz, 水平距離)``、悲観的な滑り
    ``ρ = CVaR_α(s(θ))``(θ ≥ 0)/ ``CVaR_α(−s(θ))``(θ < 0)、所要時間 ``L / (v (1 − ρ))``、``L`` は 3-D の辺の長さ。
    ``ρ ≥ s_max`` と範囲外は inf。``extrapolate = False``(既定)では、模型を当てはめたデータの角の範囲
    (``x_range``)の外の傾きの辺も inf(分からない斜面は通らない)—— ガウス過程はデータの外で事前の平均に戻るので、
    外挿させると急斜面ほど「滑らない」と答える(門の罠)。``alpha = 0`` なら平均の滑り(リスクに中立)。``model`` は 1 個か、``soil_map``
    (H, W の整数 0..K−1)と組で K 個の list。返り値 ``{"cost": (8, H, W), "risk_slip": (8, H, W), "pitch": (8, H, W) [deg],
    "offsets": (8, 2), "worst_slip": (H, W) 8 方向の ρ の最大, "alpha", "cell"}``。横方向の傾き(横転・横滑り)は入れない。
    """
    Z = _arr(dtm, "dtm", "cvar_cost_map", ndim=2, min_size=4)
    if min(Z.shape) < 2:
        raise ValueError("cvar_cost_map: dtm は 2 × 2 以上")
    h = _finite_pos(cell, "cell", "cvar_cost_map")
    v = _finite_pos(speed, "speed", "cvar_cost_map")
    a = float(alpha)
    if not (0 <= a < 1):
        raise ValueError("cvar_cost_map: 0 ≤ alpha < 1")
    if not (0 < float(s_max) < 1):
        raise ValueError("cvar_cost_map: 0 < s_max < 1")
    models = model if isinstance(model, (list, tuple)) else [model]
    for m in models:
        _model(m, "cvar_cost_map")
    if soil_map is None:
        if len(models) != 1:
            raise ValueError("cvar_cost_map: model が複数なら soil_map が要る")
        Sm = np.zeros(Z.shape, dtype=np.int64)
    else:
        Sm = np.asarray(soil_map)
        if Sm.shape != Z.shape or not np.issubdtype(Sm.dtype, np.integer):
            raise ValueError("cvar_cost_map: soil_map は dtm と同じ形の整数配列")
        if Sm.min() < 0 or Sm.max() >= len(models):
            raise ValueError("cvar_cost_map: soil_map の値は 0..len(model)−1")
    # 辺ごとに模型を呼ぶと 8 × H × W 回の予測になる(ガウス過程で 128² に 4 s)。傾きは 1 次元なので、0.05° 刻みの
    # 表を模型ごとに 1 回作って内挿する(表の外の傾き ±89° は端の値)。
    tables = [(slip_cvar(m, _PITCH_GRID, a, 1.0), slip_cvar(m, _PITCH_GRID, a, -1.0)) for m in models]
    H, W = Z.shape
    cost = np.full((8, H, W), np.inf)
    risk = np.full((8, H, W), np.nan)
    pitch = np.full((8, H, W), np.nan)
    for k, (di, dj) in enumerate(_OFFS):
        i0, i1 = max(0, -di), H - max(0, di)
        j0, j1 = max(0, -dj), W - max(0, dj)
        src = Z[i0:i1, j0:j1]
        dst = Z[i0 + di:i1 + di, j0 + dj:j1 + dj]
        dxy = h * math.hypot(di, dj)
        dz = dst - src
        th = np.degrees(np.arctan2(dz, dxy))
        L = np.sqrt(dxy * dxy + dz * dz)
        rho = np.empty_like(th)
        # 辺の土 = 出発のセルと到着のセルの悪い方(滑りの大きい方)
        soil_a = Sm[i0:i1, j0:j1]
        soil_b = Sm[i0 + di:i1 + di, j0 + dj:j1 + dj]
        flat = th.ravel()
        up = flat >= 0
        best = np.full(flat.shape, -np.inf)
        for si, m in enumerate(models):
            sel = (soil_a.ravel() == si) | (soil_b.ravel() == si)
            if not np.any(sel):
                continue
            tu, td = tables[si]
            rr = np.where(up, np.interp(flat, _PITCH_GRID, tu), np.interp(flat, _PITCH_GRID, td))
            if not extrapolate:
                lo_x, hi_x = models[si].get("x_range", (-np.inf, np.inf))
                rr = np.where((flat < lo_x) | (flat > hi_x), np.inf, rr)
            best = np.where(sel, np.maximum(best, rr), best)
        rho = best.reshape(th.shape)
        rho_eff = np.maximum(rho, 0.0)
        with np.errstate(invalid="ignore"):
            c = np.where(rho < s_max, L / (v * (1.0 - np.minimum(rho_eff, 0.999999))), np.inf)
        cost[k, i0:i1, j0:j1] = c
        risk[k, i0:i1, j0:j1] = rho
        pitch[k, i0:i1, j0:j1] = th
    fin = np.where(np.isfinite(risk), risk, np.nan)
    with np.errstate(all="ignore"):
        worst = np.where(np.all(np.isnan(fin), axis=0), np.nan, np.nanmax(np.where(np.isnan(fin), -np.inf, fin), axis=0))
    return {"cost": cost, "risk_slip": risk, "pitch": pitch, "offsets": _OFFS.copy(), "worst_slip": worst,
            "alpha": a, "cell": h}


def risk_aware_path(cost_map, start, goal) -> dict:
    """:func:`cvar_cost_map` の辺の所要時間の上で、8 近傍の Dijkstra(向きのある辺 —— 登りと下りで違う)。

    ``start``・``goal`` は (行, 列)。返り値 ``{"path": (n, 2) の添字, "cost": 合計の所要時間 [s] (届かなければ inf),
    "reached": bool, "cost_to_come": (H, W)}``。届かないときは ``path`` が空。
    """
    if not isinstance(cost_map, dict) or "cost" not in cost_map:
        raise ValueError("risk_aware_path: cost_map は cvar_cost_map の返り値")
    C = np.asarray(cost_map["cost"], np.float64)
    if C.ndim != 3 or C.shape[0] != 8:
        raise ValueError("risk_aware_path: cost は (8, H, W)")
    if np.any(np.isnan(C)) or np.any(C < 0):
        raise ValueError("risk_aware_path: cost に nan か負の値")
    H, W = C.shape[1:]
    try:
        s = (int(start[0]), int(start[1]))
        g = (int(goal[0]), int(goal[1]))
    except (TypeError, ValueError, IndexError):
        raise ValueError("risk_aware_path: start・goal は (行, 列)") from None
    for p in (s, g):
        if not (0 <= p[0] < H and 0 <= p[1] < W):
            raise ValueError("risk_aware_path: start・goal が地図の外")
    dist = np.full((H, W), np.inf)
    prev = np.full((H, W), -1, dtype=np.int64)
    dist[s] = 0.0
    pq = [(0.0, s[0], s[1])]
    done = np.zeros((H, W), dtype=bool)
    offs = _OFFS.tolist()
    while pq:
        d, i, j = heapq.heappop(pq)
        if done[i, j]:
            continue
        done[i, j] = True
        if (i, j) == g:
            break
        for k in range(8):
            c = C[k, i, j]
            if c == math.inf:
                continue
            ni, nj = i + offs[k][0], j + offs[k][1]
            nd = d + c
            if nd < dist[ni, nj]:
                dist[ni, nj] = nd
                prev[ni, nj] = i * W + j
                heapq.heappush(pq, (nd, ni, nj))
    if not np.isfinite(dist[g]):
        return {"path": np.zeros((0, 2), dtype=np.int64), "cost": math.inf, "reached": False, "cost_to_come": dist}
    path = [g]
    while path[-1] != s:
        p = int(prev[path[-1]])
        path.append((p // W, p % W))
    return {"path": np.asarray(path[::-1], dtype=np.int64), "cost": float(dist[g]), "reached": True,
            "cost_to_come": dist}


def path_slip_risk(path, dtm, cell: float, model, alpha: float = 0.9, speed: float = 0.05, s_max: float = 0.9) -> dict:
    """経路を辺ごとに評価する: 傾き、平均の滑り、CVaR_α の滑り、``s_max`` を越える確率(ガウス過程は正規分布、
    分位点回帰は分位点の曲線の内挿)、平均の滑りでの所要時間と CVaR での所要時間。

    返り値 ``{"length" [m], "time_mean" [s], "time_cvar" [s], "max_pitch" [deg], "max_mean_slip", "max_cvar_slip",
    "p_exceed_max": 辺ごとの越える確率の最大, "p_exceed_any": 辺が独立と置いた 1 − Π(1 − p), "pitch", "mean_slip",
    "cvar_slip", "p_exceed"}``(後ろ 4 つは辺ごと)。下りの辺は −s で測る。
    """
    P = np.asarray(path)
    if P.ndim != 2 or P.shape[1] != 2 or P.shape[0] < 2:
        raise ValueError("path_slip_risk: path は (n ≥ 2, 2) の添字")
    Z = _arr(dtm, "dtm", "path_slip_risk", ndim=2)
    h = _finite_pos(cell, "cell", "path_slip_risk")
    v = _finite_pos(speed, "speed", "path_slip_risk")
    M = _model(model, "path_slip_risk")
    P = P.astype(np.int64)
    if P.min() < 0 or np.any(P.max(axis=0) >= np.array(Z.shape)):
        raise ValueError("path_slip_risk: path が地図の外")
    step = np.diff(P, axis=0)
    if np.any(np.abs(step).max(axis=1) != 1):
        raise ValueError("path_slip_risk: path は 8 近傍で隣り合う添字の列")
    dz = Z[P[1:, 0], P[1:, 1]] - Z[P[:-1, 0], P[:-1, 1]]
    dxy = h * np.hypot(step[:, 0], step[:, 1])
    th = np.degrees(np.arctan2(dz, dxy))
    L = np.hypot(dxy, dz)
    up = th >= 0
    pred = slip_predict(M, th)
    mean_s = np.where(up, pred["mean"], -pred["mean"])
    cv = np.where(up, slip_cvar(M, th, alpha, 1.0), slip_cvar(M, th, alpha, -1.0))
    if M["kind"] == "gp":
        nd = NormalDist()
        p = np.array([1 - nd.cdf((s_max - m) / max(sd, 1e-12)) for m, sd in zip(mean_s, pred["std"])])
    else:
        q = M["quantiles"]
        Q = _qr_curves(M, th)
        p = np.empty(th.size)
        for i in range(th.size):
            row = Q[i] if up[i] else -Q[i][::-1]
            qq = q if up[i] else 1 - q[::-1]
            p[i] = 1.0 - float(np.interp(s_max, row, qq, left=0.0, right=1.0))
    eff_m = np.clip(mean_s, 0.0, 0.999999)
    eff_c = np.clip(cv, 0.0, 0.999999)
    t_mean = float(np.sum(np.where(mean_s < s_max, L / (v * (1 - eff_m)), np.inf)))
    t_cvar = float(np.sum(np.where(cv < s_max, L / (v * (1 - eff_c)), np.inf)))
    p = np.clip(p, 0.0, 1.0)
    return {"length": float(L.sum()), "time_mean": t_mean, "time_cvar": t_cvar, "max_pitch": float(np.max(np.abs(th))),
            "max_mean_slip": float(mean_s.max()), "max_cvar_slip": float(cv.max()), "p_exceed_max": float(p.max()),
            "p_exceed_any": float(1 - np.prod(1 - p)), "pitch": th, "mean_slip": mean_s, "cvar_slip": cv, "p_exceed": p}


# ======================================================================================================================
# 付録: 剛体の車輪の物理シミュレータとの比較(op ではない。門と PoC が使う。mujoco は関数の中で import)
def _mujoco_slope_slip(slopes_deg, mu: float, radius: float, width: float, load_mass: float,
                       omega: float = 2.0, gravity: float = 3.72, t_end: float = 3.0, dt: float = 0.001) -> np.ndarray:
    """剛な円柱の車輪 1 本を剛な斜面の上で一定の角速度 ``omega`` で回し、定常の滑り率 ``1 − v/(r ω)`` を返す。

    斜面は重力の向きを傾けて表す(+x が登り)。車輪は x・z の並進と y まわりの回転の 3 自由度、質量
    ``load_mass``(1 輪が受け持つ車体の質量)。後半 1/3 の平均速度で測る。滑り落ちると s > 1。
    土の沈下・せん断変形は無い(剛体の接触 + Coulomb 摩擦)—— 柔らかい土とは一致しない領域を測るための相手。
    """
    import mujoco                                        # noqa: PLC0415 (任意の依存)
    xml = """
<mujoco>
  <option timestep="%g" integrator="implicitfast" cone="elliptic" impratio="10"/>
  <worldbody>
    <geom name="ground" type="plane" size="50 5 0.1" friction="%g 0.005 0.0001"/>
    <body name="wheel" pos="0 0 %g">
      <joint name="x" type="slide" axis="1 0 0"/>
      <joint name="z" type="slide" axis="0 0 1"/>
      <joint name="spin" type="hinge" axis="0 1 0"/>
      <geom type="cylinder" size="%g %g" euler="90 0 0" mass="%g" friction="%g 0.005 0.0001"/>
    </body>
  </worldbody>
  <actuator><velocity joint="spin" kv="%g"/></actuator>
</mujoco>""" % (dt, mu, radius, radius, width / 2, load_mass, mu, 50.0 * load_mass * radius * radius)
    out = []
    for beta in np.atleast_1d(np.asarray(slopes_deg, np.float64)):
        m = mujoco.MjModel.from_xml_string(xml)
        b = math.radians(float(beta))
        m.opt.gravity[:] = (-gravity * math.sin(b), 0.0, -gravity * math.cos(b))
        d = mujoco.MjData(m)
        d.ctrl[0] = omega
        n = int(round(t_end / dt))
        xs, ws = [], []
        for i in range(n):
            mujoco.mj_step(m, d)
            if i >= 2 * n // 3:
                xs.append(d.qpos[0])
                ws.append(d.qpos[2])
        v = (xs[-1] - xs[0]) / ((len(xs) - 1) * dt)
        w = (ws[-1] - ws[0]) / ((len(ws) - 1) * dt)
        out.append(1.0 - v / (radius * w) if abs(w) > 1e-9 else float("nan"))
    return np.asarray(out)
