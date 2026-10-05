# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""粉体の山を画像で測る —— 安息角・体積・質量・流動性・排出率(規則だけ、学習なし、2026-10-05)。

物理シミュ × Fullseye 系列(pegsim / tacsim / tacslip / tactorque / puck / pegfail に続く)。先行研究の粉体計量
(Kadokawa, Hamaya, Tanaka, IROS 2023, doi 10.1109/iros55552.2023.10342463)は秤の質量だけを観測に使い、視覚は無い。ここは **山の形(側面像・高さ図)から質量と流動性を読む**
側を埋める。真値は 3 系統の外部の式と公表値:

- 円錐: ``V = (π/3) R² H``、``H = R tan φ``、``m = ρ_b V``(閉形式)。
- Beverloo の排出則(Beverloo, Leniger, van de Velde, Chem. Eng. Sci. 15 (1961) 260–269,
  doi 10.1016/0009-2509(61)85030-6): ``W = C ρ_b √g (D₀ − k d)^{5/2}``、``C ≈ 0.58``、``k ≈ 1.4``
  (Nedderman, Statics and Kinematics of Granular Materials, 1992 の整理)。
- 流動性区分: USP 一般章 <1174> Powder Flow の表 "Flow Properties and Corresponding Angles of
  Repose"(出典 Carr, R.L., Chem. Eng. 72 (1965) 163–168)。
- ガラス球の安息角の公表値: 1 mm ガラス球の積み上げ実験 25.2 ± 0.8 度(6 回、左右 12 測定の
  平均の標準偏差; Sunday, Murdoch, Tardivel, Schwartz, Michel, MNRAS 2020, arXiv 2009.10448 §5.4)。
  同論文の DEM は球-球の摩擦 0.16、転がり摩擦 0.09 で 25.3 ± 0.1 度を再現(§5.5)。

座標の約束: 画像は ``(H, W)`` の float で **行 0 が上**。側面像は「粉の被覆率」(0 = 背景、1 = 粉、
縁は反エイリアスの中間値)。高さ図は ``(H, W)`` の高さ [m]、``pitch`` は 1 画素の辺 [m]。角度は度。
失敗はすべて ``ValueError``(山が写っていない / 縁で切れている / 綴り違い / 不足の引数)。

mg 級の計量は画像の体積分解能(1 画素³ × ρ_b)が mg を桁で超えるので無理 —— **g 級の砕石・ビーズ
で成立、mg 級は秤に譲る**(docstring に明記するという台帳の規律)。

読めなかった一次情報(正直に): Al-Hashemi & Al-Amoudi, *Powder Technology* 330 (2018) 397–417(材料別の安息角の
レビュー、CC BY 4.0)は本文の表を取得できず **未収録**。Zhou, Xu, Yu, Zulli, *Powder Technology* 125 (2002) 45–54 の
経験式も **未読**で数を引用していない。公表値として使えるのは上の 1 mm ガラス球の 25.2 ± 0.8 度だけ。

第 2 実装 = 剛体球の山(MuJoCo 3.x、optional): :func:`heap_scene_mjcf` が MJCF 文字列を作り(mujoco 不要、台帳に載る)、
:func:`heap_mujoco_pour` / :func:`heap_mujoco_discharge` が走らせる(mujoco が要るので facade だけ、台帳の外)。
剛体の軟接触で付着は無く、転がり摩擦の模型も DEM と違う —— 実測では公表値より 3 度ほど低く出て、その理由
(模型 / 山が 5 粒径しか無い / 正方孔の異方性)は切り分けていない。合成の側面像の縁の模型は計測の模型と同じなので、
雑音なしの往復 0.0000 度は配管の検査でしかない。独立な被験者は MuJoCo の球と雑音だけ。
"""
from __future__ import annotations

import math

import numpy as np

import demops
import measure

__all__ = [
    "USP1174_REPOSE_TABLE", "USP1174_LOWER_BOUND", "GLASS_BEADS_REPOSE_PUBLISHED", "G_STD",
    "heap_volume_cone", "heap_mass", "heap_volume_heightmap",
    "beverloo_rate", "beverloo_fit", "discharge_synth", "dispense_mass_from_video", "hopper_discharge_rate",
    "spoon_tilt_critical", "spoon_tilt_dispense",
    "powder_flowability_class",
    "heap_synth_cone", "cone_profile_px",
    "repose_angle_silhouette", "repose_angle_heightmap", "datum_tilt_check",
    "container_synth", "container_fill_level",
    "heap_spheres_select", "spheres_to_heightmap", "spheres_to_silhouette", "spheres_render_shaded", "heap_scene_mjcf",
    "heap_mujoco_pour", "heap_mujoco_discharge",
]

G_STD = 9.80665

#: USP <1174> Table 1(Carr 1965)。(上限 [度], 区分)。表は 25–30 / 31–35 / 36–40 / 41–45 / 46–55 /
#: 56–65 / >66 と **整数の度**で書かれているので、角を四捨五入して整数にしてから引く(30.4 → 30 = excellent、
#: 30.5 → 31 = good)。66 は表に無い(65 と >66 の間)—— 隙間は "very, very poor" 側に入れる(上限 65 を含む)。
#: 25 度未満は表の外(``tabulated=False`` で返す)。
USP1174_REPOSE_TABLE = (
    (30.0, "excellent"),
    (35.0, "good"),
    (40.0, "fair"),            # 表の注: aid not needed
    (45.0, "passable"),        # 表の注: may hang up
    (55.0, "poor"),            # 表の注: must agitate, vibrate
    (65.0, "very poor"),
    (math.inf, "very, very poor"),
)
USP1174_LOWER_BOUND = 25.0

#: 公表値(読んだ数だけ)。Sunday ほか 2020(arXiv 2009.10448)§5.4: 1 mm ガラス球、容器幅 177 mm、
#: 側面像の上縁に左右別々に直線を当て、裾と頂を除く(本 op と同じ作法)。
GLASS_BEADS_REPOSE_PUBLISHED = {
    "material": "glass beads, d = 1.0 ± 0.2 mm, dry",
    "phi_deg": 25.2, "phi_sd_deg": 0.8, "trials": 6,
    "method": "side image, lines fitted to the upper edges, tails and centre removed",
    "dem_match": {"mu_slide_pp": 0.16, "mu_roll": 0.09, "phi_deg": 25.3, "phi_sd_deg": 0.1,
                  "restitution_pp": 0.97, "density_kg_m3": 2500},
    "source": "Sunday, Murdoch, Tardivel, Schwartz, Michel, MNRAS (2020), arXiv:2009.10448, Sec. 5.4-5.5, Table 2",
}


# ----------------------------------------------------------------------------------------------
# 引数の検査(fail-closed)
# ----------------------------------------------------------------------------------------------
def _pos(v, name):
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a finite number > 0, got %r" % (name, v))
    if isinstance(v, bool) or not math.isfinite(f) or f <= 0.0:
        raise ValueError("%s must be a finite number > 0, got %r" % (name, v))
    return f


def _nonneg(v, name):
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a finite number >= 0, got %r" % (name, v))
    if isinstance(v, bool) or not math.isfinite(f) or f < 0.0:
        raise ValueError("%s must be a finite number >= 0, got %r" % (name, v))
    return f


def _angle(v, name, lo=0.0, hi=90.0):
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be an angle in degrees, got %r" % (name, v))
    if isinstance(v, bool) or not math.isfinite(f) or not (lo < f < hi):
        raise ValueError("%s must satisfy %g < angle < %g degrees, got %r" % (name, lo, hi, v))
    return f


def _image(a, name):
    x = np.asarray(a, dtype=np.float64)
    if x.ndim != 2 or x.shape[0] < 3 or x.shape[1] < 3:
        raise ValueError("%s must be a 2-D array of at least 3x3, got shape %r" % (name, np.shape(a)))
    if not np.all(np.isfinite(x)):
        raise ValueError("%s contains nan/inf" % name)
    return x


def _choice(v, name, allowed):
    if v not in allowed:
        raise ValueError("%s must be one of %r, got %r" % (name, tuple(allowed), v))
    return v


# ----------------------------------------------------------------------------------------------
# 閉形式: 円錐・質量・Beverloo
# ----------------------------------------------------------------------------------------------
def heap_volume_cone(R: float | None = None, H: float | None = None, phi_deg: float | None = None) -> dict:
    """円錐の山の閉形式 —— ``R``・``H``・``phi_deg`` のうち **ちょうど 2 つ** を与えると残りと体積を返す。

    ``V = (π/3) R² H``、``H = R tan φ``。返り: ``R``, ``H``, ``phi_deg``, ``V`` [m³]、``A``(底面積 πR²)。
    **Raises** ``ValueError``: 与えた数が 2 つでない、または ≤ 0 / 非有限 / 角が (0, 90) の外。
    3 つ全部渡されたときも拒否する(矛盾した 3 つ組を黙って片方で上書きしない)。"""
    given = [v is not None for v in (R, H, phi_deg)]
    if sum(given) != 2:
        raise ValueError("heap_volume_cone: give exactly two of R, H, phi_deg (got %d)" % sum(given))
    if phi_deg is None:
        R, H = _pos(R, "R"), _pos(H, "H")
        phi_deg = math.degrees(math.atan2(H, R))
    elif H is None:
        R, phi_deg = _pos(R, "R"), _angle(phi_deg, "phi_deg")
        H = R * math.tan(math.radians(phi_deg))
    else:
        H, phi_deg = _pos(H, "H"), _angle(phi_deg, "phi_deg")
        R = H / math.tan(math.radians(phi_deg))
    return {"R": R, "H": H, "phi_deg": phi_deg, "V": math.pi / 3.0 * R * R * H, "A": math.pi * R * R}


def heap_mass(volume: float, bulk_density: float) -> float:
    """``m = ρ_b V`` [kg]。``bulk_density`` はかさ密度 [kg/m³] (粒子密度ではない —— ガラス球 2500 kg/m³ の
    山は充填率 ≈ 0.6 で ρ_b ≈ 1500 kg/m³)。**Raises** ``ValueError``: 体積が < 0、密度が ≤ 0。"""
    return _nonneg(volume, "volume") * _pos(bulk_density, "bulk_density")


def heap_volume_heightmap(hm, pitch: float, ground=None) -> float:
    """高さ図の山の体積 ``Σ (z − z_ground) pitch²`` [m³]。``ground`` は同形の地面高さ(None = 0)。
    負の高さ(地面より下)は 0 に切る —— 穴を山から引き算しない。**Raises** ``ValueError``: 形・pitch。"""
    z = _image(hm, "hm")
    p = _pos(pitch, "pitch")
    if ground is not None:
        g = _image(ground, "ground")
        if g.shape != z.shape:
            raise ValueError("ground shape %r != hm shape %r" % (g.shape, z.shape))
        z = z - g
    return float(np.clip(z, 0.0, None).sum() * p * p)


def beverloo_rate(D0: float, d: float, bulk_density: float, C: float = 0.58, k: float = 1.4, g: float = G_STD) -> float:
    """Beverloo の排出則 ``W = C ρ_b √g (D₀ − k d)^{5/2}`` [kg/s] (Beverloo ほか 1961; 係数 C ≈ 0.58、
    k ≈ 1.4 は Nedderman 1992 の整理)。``D0`` = 円孔の直径 [m]、``d`` = 粒径 [m]、``bulk_density`` = かさ密度。

    **Raises** ``ValueError``: ``D0 ≤ k d``(有効開口が無い。式は負の底を 5/2 乗できないし、現実には
    詰まる)/ いずれかが ≤ 0 / 非有限。``D0/d < 6`` 程度では間欠流・詰まりが起きる(式の適用外)が、
    それはここでは拒否せず、返りの検査は呼び手に委ねる(閾は材料依存)。"""
    D0, d, rb = _pos(D0, "D0"), _pos(d, "d"), _pos(bulk_density, "bulk_density")
    C, k, g = _pos(C, "C"), _nonneg(k, "k"), _pos(g, "g")
    eff = D0 - k * d
    if eff <= 0.0:
        raise ValueError("beverloo_rate: D0 - k d = %g <= 0 (no effective orifice)" % eff)
    return C * rb * math.sqrt(g) * eff ** 2.5


def beverloo_fit(D0, W, d: float, bulk_density: float, k: float = 1.4, g: float = G_STD) -> dict:
    """排出率の列 ``W_i(D0_i)`` に ``log W = log(C ρ_b √g) + n log(D₀ − k d)`` を最小二乗で当て、指数 ``n``
    と係数 ``C`` を返す(真値 n = 2.5、C ≈ 0.58)。返り: ``n``, ``C``, ``rms_log``(対数残差)。
    **Raises** ``ValueError``: 点が 3 未満 / ``D0 ≤ k d`` の点がある / W ≤ 0。"""
    x = np.asarray(D0, dtype=np.float64).ravel()
    y = np.asarray(W, dtype=np.float64).ravel()
    d, rb, k, g = _pos(d, "d"), _pos(bulk_density, "bulk_density"), _nonneg(k, "k"), _pos(g, "g")
    if x.size != y.size or x.size < 3:
        raise ValueError("beverloo_fit: need >= 3 matching points, got %d / %d" % (x.size, y.size))
    eff = x - k * d
    if np.any(eff <= 0.0) or np.any(y <= 0.0) or not np.all(np.isfinite(eff)) or not np.all(np.isfinite(y)):
        raise ValueError("beverloo_fit: all D0 must exceed k d and all W must be > 0")
    lx, ly = np.log(eff), np.log(y)
    A = np.column_stack([lx, np.ones_like(lx)])
    coef, *_ = np.linalg.lstsq(A, ly, rcond=None)
    n, b = float(coef[0]), float(coef[1])
    resid = ly - A @ coef
    return {"n": n, "C": math.exp(b) / (rb * math.sqrt(g)), "rms_log": float(np.sqrt(np.mean(resid ** 2))),
            "n_points": int(x.size)}


# ----------------------------------------------------------------------------------------------
# スプーンの傾け(規則、2 次元断面、準静的) —— 自分の導出
# ----------------------------------------------------------------------------------------------
def spoon_tilt_critical(phi_deg: float, L: float, h0: float) -> float:
    """スプーンから粉がこぼれ始める傾き θ_c [度] (2 次元断面、準静的、壁摩擦なし —— **自分の導出**)。

    模型: 床の長さ ``L``(唇から奥壁まで)、水平で深さ ``h0`` に平らに盛った粉。唇を下げて床を θ 傾ける。
    粉の自由表面は水平から φ(安息角)までしか立てないので、保持できる断面積は唇から奥へ
    ``A(θ) = ½ L² (tan φ − tan θ)``(床と表面の楔)。初めの面積 ``L h0`` を超えて保持できなくなる傾きが
    ``θ_c = atan(tan φ − 2 h0 / L)``。盛りが多いほど早くこぼれ、``h0 → 0`` で ``θ_c → φ``、θ = φ で全部出る。
    ``2 h0 / L ≥ tan φ`` なら水平でも既に保持できない(θ_c = 0 を返す)。
    **Raises** ``ValueError``: φ が (0, 90) の外、L / h0 が ≤ 0。"""
    phi = _angle(phi_deg, "phi_deg")
    L, h0 = _pos(L, "L"), _pos(h0, "h0")
    t = math.tan(math.radians(phi)) - 2.0 * h0 / L
    return math.degrees(math.atan(t)) if t > 0.0 else 0.0


def spoon_tilt_dispense(theta_deg: float, phi_deg: float, L: float, h0: float, h_wall: float | None = None) -> dict:
    """傾き θ で出た粉の割合(:func:`spoon_tilt_critical` と同じ 2 次元模型)。

    保持断面 ``A(θ) = ∫₀ᴸ min((tan φ − tan θ) x, h_wall) dx``(``h_wall`` = 奥壁の高さ、None = 無限)、
    出た割合 ``= 1 − min(A, L h0) / (L h0)``。θ ≤ θ_c で 0、θ ≥ φ で 1、間は単調。
    返り: ``fraction``, ``retained_area``, ``theta_c_deg``。**Raises** ``ValueError``: 引数の範囲。"""
    theta = _nonneg(theta_deg, "theta_deg")
    if theta >= 90.0:
        raise ValueError("theta_deg must be < 90, got %r" % theta_deg)
    phi = _angle(phi_deg, "phi_deg")
    L, h0 = _pos(L, "L"), _pos(h0, "h0")
    A0 = L * h0
    s = math.tan(math.radians(phi)) - math.tan(math.radians(theta))
    if s <= 0.0:
        A = 0.0
    elif h_wall is None:
        A = 0.5 * L * L * s
    else:
        hw = _pos(h_wall, "h_wall")
        xw = min(L, hw / s)                       # ここまで楔、先は壁の高さで頭打ち
        A = 0.5 * s * xw * xw + hw * (L - xw)
    return {"fraction": 1.0 - min(A, A0) / A0, "retained_area": min(A, A0),
            "theta_c_deg": spoon_tilt_critical(phi, L, h0)}


# ----------------------------------------------------------------------------------------------
# 流動性区分
# ----------------------------------------------------------------------------------------------
def powder_flowability_class(phi_deg: float) -> dict:
    """安息角 → 流動性区分(USP <1174> Table 1、原典 Carr 1965)。

    返り: ``cls``(excellent / good / fair / passable / poor / very poor / very, very poor)、``phi_int``(表を引いた
    整数の度 = 四捨五入)、``tabulated``(表の下限 25 度以上か)、``band_upper_deg``(その区分の上限; 上限の無い最後の区分は None ——
    返りに inf を入れない、JSON に載らないため)。表は整数の
    度なので 30.5 は 31(good)、30.4 は 30(excellent)。**Raises** ``ValueError``: 角が (0, 90) の外。"""
    phi = _angle(phi_deg, "phi_deg")
    k = int(math.floor(phi + 0.5))
    for hi, name in USP1174_REPOSE_TABLE:
        if k <= hi:
            return {"cls": name, "phi_int": k, "band_upper_deg": hi if math.isfinite(hi) else None, "tabulated": k >= USP1174_LOWER_BOUND,
                    "source": "USP <1174> Table 1 (Carr 1965)"}
    raise AssertionError("unreachable")


# ----------------------------------------------------------------------------------------------
# 合成世界: 円錐の山(側面像 + 高さ図、裾の丸み・頂の鈍り・地面の傾き)
# ----------------------------------------------------------------------------------------------
def cone_profile_px(u, H_px: float, phi_deg: float, toe_round_px: float = 0.0, apex_blunt_px: float = 0.0):
    """円錐の母線の断面 ``c(u)`` [px] (``u`` = 軸からの距離 [px])。

    基本は ``c = max(0, H − u tan φ)``。``apex_blunt_px`` = 頂に内接する円弧の半径(材料を削る、中心は
    ``(0, H − r/cos φ)``、接点 ``u = r sin φ``)。``toe_round_px`` = 裾の凹みを埋める円弧の半径(材料を
    足す、中心は空気側 ``(x_t, r)``、``x_t = R + r tan(φ/2)``、接点 ``u = x_t − r sin φ``)—— どちらも
    接線連続(導出: 接点で両側の高さが裾は ``r(1 − cos φ)``、頂は ``H − r sin²φ / cos φ`` で一致)。**Raises** ``ValueError``: 2 つの円弧が重なる(山が小さすぎる)。"""
    u = np.abs(np.asarray(u, dtype=np.float64))
    phi = math.radians(_angle(phi_deg, "phi_deg"))
    H = _pos(H_px, "H_px")
    ra, rt = _nonneg(apex_blunt_px, "apex_blunt_px"), _nonneg(toe_round_px, "toe_round_px")
    t, s, c = math.tan(phi), math.sin(phi), math.cos(phi)
    R = H / t
    xt = R + rt * math.tan(phi / 2.0)
    ua, ut = ra * s, xt - rt * s
    if ua >= ut:
        raise ValueError("cone_profile_px: apex arc (u <= %.2f) overlaps toe arc (u >= %.2f)" % (ua, ut))
    out = H - u * t
    if ra > 0.0:
        m = u <= ua
        out = np.where(m, (H - ra / c) + np.sqrt(np.clip(ra * ra - u * u, 0.0, None)), out)
    if rt > 0.0:
        m = (u >= ut) & (u <= xt)
        out = np.where(m, rt - np.sqrt(np.clip(rt * rt - (u - xt) ** 2, 0.0, None)), out)
    out = np.where(u > xt, 0.0, out)
    return np.clip(out, 0.0, None)


def heap_synth_cone(phi_deg: float, radius_px: float, pitch: float = 1e-3, *, toe_round_px: float = 0.0,
                    apex_blunt_px: float = 0.0, ground_tilt_deg: float = 0.0, margin_px: int = 12,
                    supersample: int = 8, noise: float = 0.0, seed: int | None = None) -> dict:
    """既知の安息角の円錐の山を合成する(側面像 = 反エイリアスの被覆率、高さ図 = セル中心の高さ)。

    - ``radius_px``: 裾までの半径 [px] (丸み無しのとき)。高さ ``H = R tan φ``。
    - ``ground_tilt_deg``: **基準面の傾き**(せん断型: ``z' = z + x tan β``)。高さ図の基準面(datum)
      が傾いているときの罠(平らでない地面で安息角が足し算される —— 既存 PoC `poc_stockpile_volume`
      と同じ門)。カメラのロール(回転型)とは 2 次でなく **1 次で違う**(β = 5 度・φ = 30 度で
      1.4 度、``atan(tan φ + tan β)`` 対 ``φ + β``)ので別物として扱う。
    - ``noise``: 被覆率に足す一様雑音の振幅(縁の揺らぎの代わり)。
    - 返り: ``side``(被覆率 ``(rows, cols)``)、``heightmap`` [m]、``ground``(基準面 [m]、同形)、
      ``truth``(phi_deg, R_px, H_px, toe_px, V(数値回転積分 [m³]), V_cone(閉形式)、ground_tilt_deg)、
      ``pitch``。側面像の列 ``x`` の粉の高さ(被覆率の列和)はちょうど ``c(x)`` [px] になる(副画素)。
    **Raises** ``ValueError``: 範囲外・円弧の重なり。"""
    phi = _angle(phi_deg, "phi_deg")
    R = _pos(radius_px, "radius_px")
    p = _pos(pitch, "pitch")
    beta = float(ground_tilt_deg)
    if not math.isfinite(beta) or not (-45.0 < beta < 45.0):
        raise ValueError("ground_tilt_deg must be within (-45, 45), got %r" % ground_tilt_deg)
    ss = int(supersample)
    if ss < 1:
        raise ValueError("supersample must be >= 1")
    H = R * math.tan(math.radians(phi))
    tb = math.tan(math.radians(beta))
    xt = R + _nonneg(toe_round_px, "toe_round_px") * math.tan(math.radians(phi) / 2.0)
    cols = int(math.ceil(2.0 * xt)) + 2 * int(margin_px)
    x0 = cols / 2.0
    rise = abs(tb) * x0
    rows = int(math.ceil(H + 2.0 * margin_px + 2.0 * rise))
    g0 = margin_px + rise                              # 中心での地面高さ [px] (画像下端から)

    # 側面像: 列ごとに ss 本の副列で被覆率を平均する
    xs = (np.arange(cols * ss) + 0.5) / ss                # 副列の中心 [px]
    c = cone_profile_px(xs - x0, H, phi, toe_round_px, apex_blunt_px)
    g = g0 + tb * (xs - x0)
    top = g + c
    hb = np.arange(rows, dtype=np.float64)[::-1][:, None]   # 各行の下端の高さ(行 0 が上)
    cov = np.clip(np.minimum(top[None, :], hb + 1.0) - np.maximum(g[None, :], hb), 0.0, 1.0)
    cov = np.where(c[None, :] > 0.0, cov, 0.0)
    side = cov.reshape(rows, cols, ss).mean(axis=2)
    if noise > 0.0:
        rng = np.random.default_rng(seed)
        side = np.clip(side + rng.uniform(-noise, noise, side.shape), 0.0, 1.0)

    # 高さ図: セル中心、回転対称
    n = cols
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64) + 0.5
    rr = np.hypot(xx - x0, yy - x0)
    cr = cone_profile_px(rr, H, phi, toe_round_px, apex_blunt_px)
    ground = tb * (xx - x0) * p
    hm = ground + cr * p

    # 真の体積: 回転積分 2π ∫ u c(u) du(細かい台形則)
    uu = np.linspace(0.0, xt, 20001)
    cu = cone_profile_px(uu, H, phi, toe_round_px, apex_blunt_px)
    V = 2.0 * math.pi * float(np.trapezoid(uu * cu, uu)) * p ** 3
    truth = {"phi_deg": phi, "R_px": R, "H_px": H, "toe_px": xt, "V": V,
             "V_cone": math.pi / 3.0 * (R * p) ** 2 * (H * p), "ground_tilt_deg": beta,
             "apex_col": x0, "ground_row_at_centre": rows - g0}
    return {"side": side, "heightmap": hm, "ground": ground, "truth": truth, "pitch": p}


# ----------------------------------------------------------------------------------------------
# 計測: 側面像 → 安息角(左右 2 直線)
# ----------------------------------------------------------------------------------------------
def _edge_crossings(sub, msub, threshold, rows):
    """列ごとの上縁・下縁(しきい値で縁の画素を選び、その被覆率を副画素の位置に読む)。返り: 上縁の高さ ``top``、
    地面の高さ ``g``(いずれも画像下端から [px])。"""
    first = np.argmax(msub, axis=0)
    last = rows - 1 - np.argmax(msub[::-1, :], axis=0)
    cols = np.arange(sub.shape[1])
    a1 = sub[first, cols]
    a0 = np.where(first > 0, sub[np.maximum(first - 1, 0), cols], 0.0)
    # 行 first の下端は高さ rows - 1 - first。縁の画素の被覆率 a1 がそのまま画素内の粉面の位置(反エイリアス
    # なら厳密)、その上の画素の被覆率 a0(< threshold)も足す。線形補間だと +0.5 px 偏る(実測 0.0025 の充填率)。
    top = (rows - 1 - first) + np.clip(a1, 0.0, 1.0) + np.clip(a0, 0.0, 1.0)
    b1 = sub[last, cols]
    b0 = np.where(last < rows - 1, sub[np.minimum(last + 1, rows - 1), cols], 0.0)
    g = (rows - 1 - last) + 1.0 - np.clip(b1, 0.0, 1.0) - np.clip(b0, 0.0, 1.0)
    return top, g


def repose_angle_silhouette(side, *, threshold: float = 0.5, toe_frac: float = 0.15, apex_frac: float = 0.15,
                            min_points: int = 8, correct_ground: bool = False, method: str = "edge") -> dict:
    """側面像(粉の被覆率)から安息角 φ を読む —— 左右の斜面に別々に直線を当て、裾と頂を除く。

    手順(Sunday ほか 2020 §5.3 の作法を規則化): ①列ごとの粉面の高さ = 被覆率が ``threshold`` を切る縁の画素の
    位置 + その被覆率(副画素; ``method="edge"``、既定)②地面 = 各列の最下の交差(同じ補間)→ ``measure.fit_line`` で
    地面の傾き β。``method="column_sum"`` は被覆率の列和(縁が反エイリアスなら厳密な副画素だが、粉の画素値が
    1 からずれると **その比で tan φ がずれる**: 一様雑音 ±0.1 を [0, 1] に切っただけで 0.62 度低く出た、実測)
    ③頂 = 高さの最大列 ④地面からの高さが ``toe_frac·H`` 以上・``(1 − apex_frac)·H`` 以下の点だけを
    左右別々に ``fit_line``(全最小二乗)⑤φ = 左右の平均。

    - ``correct_ground``: 基準面の傾き β を **tan の引き算**で外す(``tan φ' = tan θ ∓ tan β``; せん断型
      datum の傾きに対して厳密)。カメラのロールなら角の引き算が正しく、両者は β = 5 度で 1 度以上違う
      ので既定は外さない。左右の差 ``asymmetry_deg`` が大きいときだけ基準面を疑う。
    - 返り: ``phi_deg``, ``phi_left_deg``, ``phi_right_deg``, ``asymmetry_deg``, ``ground_deg``,
      ``height_px``, ``base_px``, ``apex_col``, ``left_cols`` / ``right_cols``(当てた列の範囲)、
      ``rms_left`` / ``rms_right``(直線からの残差 [px])、``n_left`` / ``n_right``。
    - **Raises** ``ValueError``: 画像でない / 被覆率が [0, 1] の外 / 粉が写っていない / 山が画像の
      上・左・右の縁に触れている(切れている)/ 当てる点が ``min_points`` 未満(山が小さすぎる)/
      ``toe_frac + apex_frac ≥ 1`` / ``method`` の綴り違い。
    分解能の目安(被覆率に一様雑音 ±0.1、4 角度 × 6 seed の実測): 山の幅 400 px で 0.007 度、50 px で 0.2 度、25 px で 0.6 度。"""
    a = _image(side, "side")
    if a.min() < -1e-9 or a.max() > 1.0 + 1e-9:
        raise ValueError("side must be a coverage image in [0, 1], got [%g, %g]" % (a.min(), a.max()))
    if not (0.0 <= toe_frac < 1.0 and 0.0 <= apex_frac < 1.0 and toe_frac + apex_frac < 1.0):
        raise ValueError("toe_frac + apex_frac must be < 1 (each in [0, 1))")
    rows, cols = a.shape
    mask = a >= float(threshold)
    if not mask.any():
        raise ValueError("no heap in view (no pixel >= threshold %g)" % threshold)
    if mask[0].any():
        raise ValueError("heap touches the top edge: truncated")
    colmask = mask.any(axis=0)
    if colmask[0] or colmask[-1]:
        raise ValueError("heap touches the left/right edge: truncated")
    xs = np.flatnonzero(colmask)
    _choice(method, "method", ("edge", "column_sum"))
    sub = a[:, xs]
    msub = mask[:, xs]
    top, g = _edge_crossings(sub, msub, float(threshold), rows)
    if method == "column_sum":
        first = np.argmax(msub, axis=0)
        last = rows - 1 - np.argmax(msub[::-1, :], axis=0)
        rr = np.arange(rows)[:, None]
        inside = (rr >= first[None, :] - 1) & (rr <= last[None, :])  # 背景の雑音を列和に溜めない
        h = np.where(inside, sub, 0.0).sum(axis=0)                  # 粉の高さ [px] (副画素)
        top = g + h
    gl = measure.fit_line(np.column_stack([rows - g, xs + 0.5]))
    ground_deg = -gl["angle_deg"]                               # 右が高いほど正
    i_apex = int(np.argmax(top))
    apex_col = float(xs[i_apex] + 0.5)
    c = top - g
    Hpx = float(c.max())
    base_px = float(xs[-1] - xs[0] + 1)
    lo, hi = toe_frac * Hpx, (1.0 - apex_frac) * Hpx
    sel = (c >= lo) & (c <= hi)
    left = sel & (xs < xs[i_apex])
    right = sel & (xs > xs[i_apex])
    nl, nr = int(left.sum()), int(right.sum())
    if nl < min_points or nr < min_points:
        raise ValueError("heap too small for the fit: %d left / %d right points (need %d each)" % (nl, nr, min_points))

    def _flank(m):
        f = measure.fit_line(np.column_stack([rows - top[m], xs[m] + 0.5]))
        return abs(f["angle_deg"]), f["rms"], (int(xs[m].min()), int(xs[m].max()))

    th_l, rms_l, span_l = _flank(left)
    th_r, rms_r, span_r = _flank(right)
    if correct_ground:
        tb = math.tan(math.radians(ground_deg))
        th_l = math.degrees(math.atan(math.tan(math.radians(th_l)) - tb))
        th_r = math.degrees(math.atan(math.tan(math.radians(th_r)) + tb))
    return {"phi_deg": 0.5 * (th_l + th_r), "phi_left_deg": th_l, "phi_right_deg": th_r,
            "asymmetry_deg": th_l - th_r, "ground_deg": ground_deg, "height_px": Hpx, "base_px": base_px,
            "apex_col": apex_col, "left_cols": span_l, "right_cols": span_r, "rms_left": rms_l, "rms_right": rms_r,
            "n_left": nl, "n_right": nr, "profile_top": top, "profile_ground": g, "profile_cols": xs}


# ----------------------------------------------------------------------------------------------
# 計測: 高さ図 → 安息角(勾配ヒストグラムの最頻)
# ----------------------------------------------------------------------------------------------
def _box_filter(z, k):
    """``k × k`` の移動平均(numpy の累積和、縁は端の値を複製)。``k`` は奇数。"""
    k = int(k)
    if k < 1 or k % 2 == 0:
        raise ValueError("smooth_cells must be a positive odd integer, got %r" % k)
    if k == 1:
        return z
    h = k // 2
    zp = np.pad(z, h, mode="edge")
    c = np.cumsum(np.cumsum(zp, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    n = z.shape[0]
    m = z.shape[1]
    return (c[k:k + n, k:k + m] - c[:n, k:k + m] - c[k:k + n, :m] + c[:n, :m]) / float(k * k)


def repose_angle_heightmap(hm, pitch: float, *, ground=None, min_rel_height: float = 0.1,
                           max_rel_height: float = 0.9, bin_deg: float = 0.25, method: str = "horn",
                           smooth_cells: int = 1) -> dict:
    """高さ図から安息角 φ —— ``demops.dem_slope`` の勾配のヒストグラムの最頻値。

    手順: ①``ground`` があれば引く(datum の補正; 無ければ外周 1 画素の中央値を地面とする)②``smooth_cells``
    (奇数)の移動平均 —— **粒が見える高さ図では必須**: 球の山(粒径 5.3 px)を平滑なしで測ると勾配の最頻は
    62 度(球面の縁)、2 粒径 = 11 セルで 24.5 度(MuJoCo の球の山の実測)。粒が見えない粉の山では 1 のまま
    ③高さが最大の ``min_rel_height``〜``max_rel_height`` の帯のセルだけ使う(裾の丸みと頂の鈍りを除く)
    ④``dem_slope(method)`` を ``bin_deg`` 刻みで数え、最頻ビンとその両隣に入る値の平均で φ(ビン中心の重心だと半ビン = 0.125 度の偏りが出た、実測)。
    返り: ``phi_deg``, ``phi_median_deg``, ``frac_within_1deg``(最頻 ±1 度に入るセルの割合 —— 円錐なら
    ≈ 1、起伏があれば下がる)、``n_cells``, ``hist_centers``, ``hist_counts``。
    **Raises** ``ValueError``: 形・pitch・選択肢(``method`` は ``"horn"`` / ``"central"`` のみ)/ 山が無い
    (地面より高いセルが無い)/ 帯に 20 セル未満。"""
    z = _image(hm, "hm")
    p = _pos(pitch, "pitch")
    _choice(method, "method", ("horn", "central"))
    if not (0.0 <= min_rel_height < max_rel_height <= 1.0):
        raise ValueError("need 0 <= min_rel_height < max_rel_height <= 1")
    if ground is not None:
        g = _image(ground, "ground")
        if g.shape != z.shape:
            raise ValueError("ground shape %r != hm shape %r" % (g.shape, z.shape))
        zz = z - g
    else:
        ring = np.concatenate([z[0], z[-1], z[:, 0], z[:, -1]])
        zz = z - float(np.median(ring))
    zz = _box_filter(zz, smooth_cells)
    Hm = float(zz.max())
    if Hm <= 0.0:
        raise ValueError("no heap in view (no cell above ground)")
    slope = demops.dem_slope(zz, p, method=method, units="degrees")
    band = (zz >= min_rel_height * Hm) & (zz <= max_rel_height * Hm)
    band[0, :] = band[-1, :] = band[:, 0] = band[:, -1] = False      # 縁の複製セルは除く
    s = slope[band]
    if s.size < 20:
        raise ValueError("heap too small: only %d cells in the height band" % s.size)
    edges = np.arange(0.0, 90.0 + bin_deg, bin_deg)
    cnt, _ = np.histogram(s, bins=edges)
    i = int(np.argmax(cnt))
    lo, hi = max(i - 1, 0), min(i + 1, cnt.size - 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    inwin = (s >= edges[lo]) & (s < edges[hi + 1])
    phi = float(s[inwin].mean())                  # ビン中心でなく中の値の平均(半ビンの偏り 0.125 度を消す、実測)
    return {"phi_deg": phi, "phi_median_deg": float(np.median(s)),
            "frac_within_1deg": float(np.mean(np.abs(s - phi) <= 1.0)), "n_cells": int(s.size),
            "hist_centers": centers, "hist_counts": cnt, "height_m": Hm}


# ----------------------------------------------------------------------------------------------
# 排出の合成と計測(山の体積の時間差分)
# ----------------------------------------------------------------------------------------------
def discharge_synth(D0: float, d: float, bulk_density: float, phi_deg: float, pitch: float, duration: float,
                    n_frames: int = 8, grid: int = 256, C: float = 0.58, k: float = 1.4, noise: float = 0.0,
                    seed: int | None = None) -> dict:
    """円孔 ``D0`` から Beverloo の率で落ちた粉が、下で安息角 φ の円錐に積もっていく高さ図の列を合成する。

    ``V(t) = W t / ρ_b``、``R(t) = (3 V / (π tan φ))^{1/3}``。返り: ``frames``(``n_frames`` 枚、``(grid, grid)``
    [m])、``times`` [s]、``W``(真の率 [kg/s])、``masses``(真の質量列)。``noise`` = 高さ図に足す
    ガウス雑音の σ [m] (距離センサの雑音の代わり; 地面も揺れるので体積は 0 で切られて偏る —— その偏りを
    門で測る)。山が格子からはみ出すと ``ValueError``(体積を黙って切らない)。"""
    W = beverloo_rate(D0, d, bulk_density, C=C, k=k)
    phi = _angle(phi_deg, "phi_deg")
    p = _pos(pitch, "pitch")
    rb = _pos(bulk_density, "bulk_density")
    n = int(grid)
    times = np.linspace(0.0, _pos(duration, "duration"), int(n_frames))
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64) + 0.5
    rr = np.hypot(xx - n / 2.0, yy - n / 2.0) * p
    t = math.tan(math.radians(phi))
    frames, masses = [], []
    rng = np.random.default_rng(seed)
    for tt in times:
        V = W * tt / rb
        R = (3.0 * V / (math.pi * t)) ** (1.0 / 3.0) if V > 0.0 else 0.0
        if 2.0 * R > (n - 4) * p:
            raise ValueError("discharge_synth: heap radius %.4f m exceeds the grid (%d px * %g m)" % (R, n, p))
        z = np.clip((R - rr) * t, 0.0, None)
        if noise > 0.0:
            z = z + rng.normal(0.0, noise, z.shape)
        frames.append(z)
        masses.append(V * rb)
    return {"frames": frames, "times": times, "W": W, "masses": np.asarray(masses), "D0": float(D0)}


def dispense_mass_from_video(frames, pitch: float, bulk_density: float, times, ground=None) -> dict:
    """高さ図の列から出た質量と排出率 —— 各コマの山の体積 × ρ_b、時間に対する直線当て(最小二乗)。

    返り: ``masses`` [kg]、``rate``(傾き [kg/s])、``total``(最後 − 最初)、``rms``(直線残差 [kg])。
    **Raises** ``ValueError``: コマが 2 未満 / 時刻の数が合わない / 時刻が単調でない。
    画像の体積分解能は ``pitch³ ρ_b`` の桁(1 mm・1500 kg/m³ で 1.5 mg/画素³ だが、縁の 1 画素の
    不確かさが面積 × pitch で乗るので実際は g 級)。mg 級は秤に譲る。"""
    fr = list(frames)
    tt = np.asarray(times, dtype=np.float64).ravel()
    if len(fr) < 2 or tt.size != len(fr):
        raise ValueError("need >= 2 frames with matching times, got %d frames / %d times" % (len(fr), tt.size))
    if np.any(np.diff(tt) <= 0.0):
        raise ValueError("times must be strictly increasing")
    rb = _pos(bulk_density, "bulk_density")
    m = np.array([heap_volume_heightmap(f, pitch, ground) * rb for f in fr])
    A = np.column_stack([tt, np.ones_like(tt)])
    coef, *_ = np.linalg.lstsq(A, m, rcond=None)
    resid = m - A @ coef
    return {"masses": m, "rate": float(coef[0]), "total": float(m[-1] - m[0]),
            "rms": float(np.sqrt(np.mean(resid ** 2)))}


# ----------------------------------------------------------------------------------------------
# 容器の充填率(側面像)
# ----------------------------------------------------------------------------------------------
def container_synth(fill_frac: float, surface_tilt_deg: float = 0.0, rows: int = 200, cols: int = 160,
                    supersample: int = 8) -> dict:
    """透明な容器の内側を横から見た粉の被覆率を合成する(表面は平面、傾き可)。真値 = ``fill_frac``。"""
    f = float(fill_frac)
    if not (0.0 < f < 1.0):
        raise ValueError("fill_frac must be in (0, 1), got %r" % fill_frac)
    tb = math.tan(math.radians(float(surface_tilt_deg)))
    ss = int(supersample)
    xs = (np.arange(cols * ss) + 0.5) / ss
    top = f * rows + tb * (xs - cols / 2.0)
    if top.min() <= 0.0 or top.max() >= rows:
        raise ValueError("surface leaves the container (tilt too large for this fill)")
    hb = np.arange(rows, dtype=np.float64)[::-1][:, None]
    cov = np.clip(np.minimum(top[None, :], hb + 1.0) - hb, 0.0, 1.0)
    return {"side": cov.reshape(rows, cols, ss).mean(axis=2), "truth": {"fill_frac": f, "tilt_deg": float(surface_tilt_deg)}}


def container_fill_level(side, *, threshold: float = 0.5) -> dict:
    """容器内側の側面像(粉の被覆率、容器の内寸 = 画像)から充填率と粉面の傾きを読む。

    充填率 = 列ごとの粉面(しきい値の交差、副画素)の平均 / 行数。粉面 → ``fit_line`` →
    ``surface_tilt_deg``(右が高いほど正)と ``surface_rms``(平面からのずれ [px])。
    **Raises** ``ValueError``: 空(しきい値以上の画素が無い)/ 満杯で粉面が見えない(最上行が粉)。"""
    a = _image(side, "side")
    if a.min() < -1e-9 or a.max() > 1.0 + 1e-9:
        raise ValueError("side must be a coverage image in [0, 1]")
    mask = a >= float(threshold)
    if not mask.any():
        raise ValueError("container is empty (no pixel >= threshold)")
    if mask[0].all():
        raise ValueError("container is full to the top edge: surface not visible")
    rows, cols = a.shape
    top, _ = _edge_crossings(a, mask, float(threshold), rows)
    f = measure.fit_line(np.column_stack([rows - top, np.arange(cols) + 0.5]))
    return {"fill_frac": float(top.mean() / rows), "surface_tilt_deg": -f["angle_deg"], "surface_rms": f["rms"],
            "mean_height_px": float(top.mean())}


# ----------------------------------------------------------------------------------------------
# 第 2 実装: 剛体球の山(MuJoCo、optional)
# ----------------------------------------------------------------------------------------------
def heap_spheres_select(pos, radius: float, floor_height: float, bin_radius: float, keep_min: float = 0.5) -> dict:
    """山に属する球だけを選ぶ: ビンの底板より下(``z < floor_height − r``)で、ビン半径の 3 倍の内側。
    ビンに残った球(平底の滞留層)と転がって逃げた球は山ではない。返り: ``pos``(選んだ中心)、``n_in_bin``、
    ``n_runaway``、``radius_95``(山の半径の目安)。**Raises** ``ValueError``: 残りが ``keep_min`` 未満(山になって
    いない —— 滑らかな台で 1,200 個中 600 個が逃げたときに黙って測らないため)。"""
    P = np.asarray(pos, dtype=np.float64)
    r = _pos(radius, "radius")
    rad = np.hypot(P[:, 0], P[:, 1])
    in_bin = P[:, 2] >= _pos(floor_height, "floor_height") - r
    runaway = (~in_bin) & (rad > 3.0 * _pos(bin_radius, "bin_radius"))
    keep = ~in_bin & ~runaway
    if keep.sum() < keep_min * P.shape[0]:
        raise ValueError("no heap: only %d of %d spheres remain after dropping %d in the bin and %d runaways"
                         % (int(keep.sum()), P.shape[0], int(in_bin.sum()), int(runaway.sum())))
    return {"pos": P[keep], "n_in_bin": int(in_bin.sum()), "n_runaway": int(runaway.sum()),
            "radius_95": float(np.percentile(rad[keep], 95))}


def spheres_to_heightmap(pos, radius: float, pitch: float, extent: float) -> np.ndarray:
    """球の中心列 ``pos (n, 3)`` [m] と半径から、上から見た高さ図(各セルで球面の最大高さ、無ければ 0)。
    格子は ``[-extent, extent]²`` を ``pitch`` で刻む。"""
    P = np.asarray(pos, dtype=np.float64)
    r = _pos(radius, "radius")
    p = _pos(pitch, "pitch")
    n = int(round(2.0 * extent / p))
    hm = np.zeros((n, n))
    k = int(math.ceil(r / p))
    for x, y, z in P:
        i0, j0 = int((y + extent) / p), int((x + extent) / p)
        if i0 + k < 0 or j0 + k < 0 or i0 - k >= n or j0 - k >= n:
            continue                                   # 格子の外の球(転がって逃げた)は描かない
        ii, jj = np.mgrid[max(i0 - k, 0):min(i0 + k + 1, n), max(j0 - k, 0):min(j0 + k + 1, n)]
        cy, cx = (ii + 0.5) * p - extent, (jj + 0.5) * p - extent
        d2 = (cx - x) ** 2 + (cy - y) ** 2
        top = z + np.sqrt(np.clip(r * r - d2, 0.0, None))
        top = np.where(d2 <= r * r, top, 0.0)
        hm[ii, jj] = np.maximum(hm[ii, jj], top)
    return hm


def spheres_to_silhouette(pos, radius: float, pitch: float, extent: float, height: float, supersample: int = 4) -> np.ndarray:
    """球の中心列から、横(y 方向)から見た正射影の被覆率画像(円板の和、反エイリアス)。行 0 が上。"""
    P = np.asarray(pos, dtype=np.float64)
    r = _pos(radius, "radius")
    ss = int(supersample)
    p = _pos(pitch, "pitch") / ss
    cols, rows = ss * int(round(2.0 * extent / pitch)), ss * int(round(height / pitch))
    img = np.zeros((rows, cols), dtype=bool)
    k = int(math.ceil(r / p))
    for x, _, z in P:
        j0, i0 = int((x + extent) / p), int((height - z) / p)
        if i0 + k < 0 or j0 + k < 0 or i0 - k >= rows or j0 - k >= cols:
            continue
        ii, jj = np.mgrid[max(i0 - k, 0):min(i0 + k + 1, rows), max(j0 - k, 0):min(j0 + k + 1, cols)]
        cx, cz = (jj + 0.5) * p - extent, height - (ii + 0.5) * p
        img[ii, jj] |= (cx - x) ** 2 + (cz - z) ** 2 <= r * r
    return img.reshape(rows // ss, ss, cols // ss, ss).mean(axis=(1, 3))


def spheres_render_shaded(pos, radius: float, pitch: float, extent: float, height: float, light=(-0.4, -0.6, 0.7)) -> np.ndarray:
    """横からの正射影を陰影つきで描く(numpy の z バッファ、Lambert)。GIF 用。返り ``(rows, cols, 3)`` [0, 1]。"""
    P = np.asarray(pos, dtype=np.float64)
    r = _pos(radius, "radius")
    p = _pos(pitch, "pitch")
    cols, rows = int(round(2.0 * extent / p)), int(round(height / p))
    img = np.full((rows, cols, 3), np.array([0.08, 0.09, 0.11]))
    zbuf = np.full((rows, cols), -np.inf)
    L = np.asarray(light, dtype=np.float64)
    L /= np.linalg.norm(L)
    k = int(math.ceil(r / p))
    order = np.argsort(P[:, 1])[::-1]                   # 奥(y 大)から手前へ
    base = np.array([0.85, 0.80, 0.62])
    for idx in order:
        x, y, z = P[idx]
        j0, i0 = int((x + extent) / p), int((height - z) / p)
        if i0 + k < 0 or j0 + k < 0 or i0 - k >= rows or j0 - k >= cols:
            continue
        ii, jj = np.mgrid[max(i0 - k, 0):min(i0 + k + 1, rows), max(j0 - k, 0):min(j0 + k + 1, cols)]
        cx, cz = (jj + 0.5) * p - extent, height - (ii + 0.5) * p
        dx, dz = (cx - x) / r, (cz - z) / r
        d2 = dx * dx + dz * dz
        inside = d2 <= 1.0
        dy = -np.sqrt(np.clip(1.0 - d2, 0.0, None))          # 手前向き
        depth = -y + dy * r
        upd = inside & (depth > zbuf[ii, jj])
        shade = np.clip(dx * L[0] + dy * L[1] + dz * L[2], 0.0, 1.0) * 0.8 + 0.2
        for cch in range(3):
            ch = img[..., cch]
            sub = ch[ii, jj]
            sub[upd] = (shade * base[cch])[upd]
            ch[ii, jj] = sub
        zb = zbuf[ii, jj]
        zb[upd] = depth[upd]
        zbuf[ii, jj] = zb
    return img


def heap_scene_mjcf(n_spheres: int = 1200, radius: float = 0.004, *, mu_slide: float = 0.16, mu_roll: float = 0.09,
                    density: float = 2500.0, orifice_d: float = 0.048, orifice_height: float = 0.06, bin_radius: float = 0.05,
                    timestep: float = 1.5e-3, base_roll: float = 0.01, base_slide: float = 1.0, solver_iterations: int = 50,
                    solver: str = "CG", cone: str = "elliptic", condim: int = 6, contact_tc: float = 0.006, seed: int = 0) -> dict:
    """平底ホッパ(正方形の孔、辺 ``orifice_d``)に剛体球を積んだ場面の MJCF 文字列(**mujoco 不要**、台帳に載る)。

    球は円筒ビン(半径 ``bin_radius``、底板は高さ ``orifice_height``)の中に層で積む。底板の孔から流れ落ちて平面に山を
    作る(山が孔に届くと止まる —— 実際のホッパ下の山と同じ)。孔は 4 枚の板で囲った正方形(Beverloo の式は円孔の
    D₀; 正方形は等価直径で比べる)。摩擦は ``(mu_slide, 0.005, mu_roll·R)``: MuJoCo の転がり摩擦係数は長さの単位
    (トルク / 法線力)なので、DEM の無次元 μ_r(Sunday ほか 2020 の 0.09)に半径を掛ける。底板は **粗い台**(平面の
    滑り摩擦 ``base_slide`` 既定 1.0、転がり ``base_roll`` [m] 既定 0.01; 安息角の実験で底に紙やすりを貼るのと同じ役)。
    滑らかな台(μ 0.16)だと最初に落ちた球が転がって逃げ、山ができなかった(実測: 1,200 個が半径 0.15 m の単層に
    広がった)。転がり抵抗は滑り摩擦の限界 μ_s g で飽和する(1 球の実測: 転がり係数 0.01 でも 0.1 でも 1 m/s から
    0.32 m 走る = 減速 1.6 m/s²)ので、底を止めるのは滑り摩擦のほう。``contact_tc`` = 軟接触の時定数 [s] (solref)。
    **2·timestep 以上に取る**: 0.004 s で timestep 2 ms(= 限界)、半径 3.5 mm・2,000 個が発散した(最大速度
    12.6 m/s、実測)。解法は既定 CG + 楕円錐(Newton は密な山で 700 球が 280 s 超 → 打ち切り、実測)。

    返り: ``xml``(文字列)、``positions``(初期中心 ``(n, 3)``)、``info``(n, radius, mu_slide, mu_roll, orifice_d, bin_radius,
    orifice_height, timestep, mass_each, mass_total, column_top, bulk_density_bin)。
    **Raises** ``ValueError``: ``contact_tc < 2 timestep`` / 孔がビンに収まらない / 球がビンに入らない / 解法・錐の綴り違い。"""
    if float(contact_tc) < 2.0 * float(timestep):
        raise ValueError("contact_tc (%g) must be >= 2 * timestep (%g) for a stable soft contact" % (contact_tc, timestep))
    rng = np.random.default_rng(seed)
    r = _pos(radius, "radius")
    n = int(n_spheres)
    if n < 1:
        raise ValueError("n_spheres must be >= 1, got %r" % n_spheres)
    Rb = _pos(bin_radius, "bin_radius")
    D0 = _pos(orifice_d, "orifice_d")
    z_floor = _pos(orifice_height, "orifice_height")
    ts = _pos(timestep, "timestep")
    if D0 >= 2.0 * Rb - 4.0 * r:
        raise ValueError("orifice_d must be well inside the bin (bin diameter %.3f)" % (2.0 * Rb))
    _choice(cone, "cone", ("elliptic", "pyramidal"))
    _choice(solver, "solver", ("CG", "Newton", "PGS"))
    # ビンの中に球を積む(半径 Rb − r の円内、層間隔 2r)
    pts = []
    layer = 0
    while len(pts) < n:
        z = z_floor + 0.002 + r + layer * 2.0 * r * 0.98
        off = (layer % 2) * r
        for gy in np.arange(-Rb, Rb, 2.0 * r * 0.99):
            for gx in np.arange(-Rb + off, Rb, 2.0 * r * 0.99):
                if math.hypot(gx, gy) <= Rb - r * 1.1 and len(pts) < n:
                    pts.append((gx + rng.uniform(-0.08, 0.08) * r, gy + rng.uniform(-0.08, 0.08) * r, z))
        layer += 1
        if layer > 400:
            raise ValueError("cannot place %d spheres in the bin" % n)
    pts = np.asarray(pts)
    top = float(pts[:, 2].max()) + 4.0 * r
    th = 0.002                                               # 板の厚み
    wall_fric = 'friction="0.45 0.005 %.6f" condim="%d"' % (mu_roll * r, int(condim))
    geoms = []
    nwall = 24
    for i in range(nwall):
        a = 2.0 * math.pi * i / nwall
        cx, cy = (Rb + th) * math.cos(a), (Rb + th) * math.sin(a)
        seg = 2.0 * math.pi * (Rb + th) / nwall
        geoms.append('<geom type="box" size="%.4f %.4f %.4f" pos="%.4f %.4f %.4f" euler="0 0 %.5f" rgba="0.3 0.5 0.8 0.15" %s/>'
                     % (th, seg * 0.55, 0.5 * (top - z_floor) + th, cx, cy, 0.5 * (top + z_floor), a, wall_fric))
    h2 = 0.5 * D0
    E = Rb + 2.0 * th
    zc = z_floor - th
    # 底板 = 正方形の孔を囲う 4 枚(北・南は全幅、東・西は孔の高さぶん)
    geoms.append('<geom type="box" size="%.4f %.4f %.4f" pos="0 %.4f %.4f" rgba="0.5 0.5 0.5 0.3" %s/>' % (E, 0.5 * (E - h2), th, 0.5 * (E + h2), zc, wall_fric))
    geoms.append('<geom type="box" size="%.4f %.4f %.4f" pos="0 %.4f %.4f" rgba="0.5 0.5 0.5 0.3" %s/>' % (E, 0.5 * (E - h2), th, -0.5 * (E + h2), zc, wall_fric))
    geoms.append('<geom type="box" size="%.4f %.4f %.4f" pos="%.4f 0 %.4f" rgba="0.5 0.5 0.5 0.3" %s/>' % (0.5 * (E - h2), h2, th, 0.5 * (E + h2), zc, wall_fric))
    geoms.append('<geom type="box" size="%.4f %.4f %.4f" pos="%.4f 0 %.4f" rgba="0.5 0.5 0.5 0.3" %s/>' % (0.5 * (E - h2), h2, th, -0.5 * (E + h2), zc, wall_fric))
    bodies = "\n".join('<body pos="%.5f %.5f %.5f"><freejoint/><geom type="sphere" size="%.5f" density="%.1f" '
                       'friction="%.4f 0.005 %.6f" condim="%d"/></body>' % (x, y, z, r, density, mu_slide, mu_roll * r, int(condim))
                       for x, y, z in pts)
    xml = """<mujoco><option timestep="%g" gravity="0 0 -9.80665" integrator="implicitfast" cone="%s" solver="%s" iterations="%d" noslip_iterations="0"/>
<default><geom solref="%.4f 1" solimp="0.95 0.99 0.001"/></default>
<worldbody>
<geom type="plane" size="2 2 0.1" friction="%.3f 0.005 %.6f" condim="%d"/>
%s
%s
</worldbody></mujoco>""" % (ts, cone, solver, int(solver_iterations), _pos(contact_tc, "contact_tc"), _pos(base_slide, "base_slide"),
                            _pos(base_roll, "base_roll"), int(condim), "\n".join(geoms), bodies)
    m_each = _pos(density, "density") * 4.0 / 3.0 * math.pi * r ** 3
    info = {"n": n, "radius": r, "mu_slide": float(mu_slide), "mu_roll": float(mu_roll), "orifice_d": D0, "bin_radius": Rb,
            "orifice_height": z_floor, "timestep": ts, "plate_thickness": th, "mass_each": m_each, "mass_total": n * m_each,
            "column_top": top, "bulk_density_bin": n * m_each / (math.pi * (Rb - r) ** 2 * (top - 4.0 * r - z_floor))}
    return {"xml": xml, "positions": pts, "info": info}


def heap_mujoco_pour(n_spheres: int = 1200, radius: float = 0.004, *, duration: float = 2.5, record_every: int = 25, **scene) -> dict:
    """:func:`heap_scene_mjcf` の場面を MuJoCo で ``duration`` [s] 走らせ、球が孔から流れて山になるまでを記録する
    (**facade、mujoco が要る**、台帳の外)。**第 2 実装**(閉形式と公表値に対する独立の被験者)。

    返り: ``pos``(最終中心 ``(n, 3)``)、``frames``(``record_every`` 歩ごとの中心列)、``times``、``radius``、
    ``mass_below``(各コマで底板より下にある質量 [kg])、``elapsed_s``、``model_info``(場面の info + steps, max_speed_end,
    n_outside, n_in_bin)。**正直に**: 剛体の軟接触で付着は無い → 乾いた大粒・低付着の領域だけ。転がり摩擦の模型が
    DEM と違う(MuJoCo は錐の制約、DEM は接触ごとのトルク)。球は単分散。
    **Raises** ``ValueError``: mujoco が無い、場面の引数(:func:`heap_scene_mjcf` と同じ)。"""
    try:
        import mujoco
    except ImportError as exc:
        raise ValueError("heap_mujoco_pour needs mujoco: %s" % exc)
    import time as _time
    sc = heap_scene_mjcf(n_spheres, radius, **scene)
    info = dict(sc["info"])
    n, r, z_floor, th, m_each, ts = info["n"], info["radius"], info["orifice_height"], info["plate_thickness"], info["mass_each"], info["timestep"]
    t0 = _time.perf_counter()
    model = mujoco.MjModel.from_xml_string(sc["xml"])
    data = mujoco.MjData(model)
    frames, times, below = [], [], []
    steps = int(round(_pos(duration, "duration") / ts))
    every = int(record_every)
    if every < 1:
        raise ValueError("record_every must be >= 1")
    for st in range(steps + 1):
        if st % every == 0:
            q = data.qpos.reshape(n, 7)[:, :3].copy()
            frames.append(q)
            times.append(st * ts)
            below.append(float(np.sum(q[:, 2] < z_floor - 2.0 * th - r)) * m_each)
        if st < steps:
            mujoco.mj_step(model, data)
    pos = data.qpos.reshape(n, 7)[:, :3].copy()
    vel = data.qvel.reshape(n, 6)[:, :3]
    rad = np.hypot(pos[:, 0], pos[:, 1])
    info.update({"steps": steps, "max_speed_end": float(np.linalg.norm(vel, axis=1).max()),
                 "n_outside": int(np.sum(rad > 3.0 * info["bin_radius"])), "n_in_bin": int(np.sum(pos[:, 2] > z_floor))})
    return {"pos": pos, "frames": frames, "times": np.asarray(times), "radius": r, "mass_below": np.asarray(below),
            "elapsed_s": _time.perf_counter() - t0, "model_info": info}


def hopper_discharge_rate(mass_below, times, mass_total: float, *, lo: float = 0.2, hi: float = 0.8) -> dict:
    """底板より下の質量の列 ``m(t)`` から排出率 [kg/s] —— 全質量の ``lo``〜``hi`` の帯だけを直線で当てる(立ち上がりと
    止まり際を除く; Beverloo の定常流の仮定)。返り: ``rate``, ``n_frames``(帯のコマ数), ``t_range``, ``rms`` [kg]。
    **Raises** ``ValueError``: 帯に 3 コマ未満(排出が速すぎてコマが無い —— 黙って 2 点の傾きを返さない)/ 時刻が単調でない。"""
    m = np.asarray(mass_below, dtype=np.float64).ravel()
    t = np.asarray(times, dtype=np.float64).ravel()
    M = _pos(mass_total, "mass_total")
    if m.size != t.size or m.size < 3:
        raise ValueError("need >= 3 matching samples, got %d / %d" % (m.size, t.size))
    if np.any(np.diff(t) <= 0.0):
        raise ValueError("times must be strictly increasing")
    if not (0.0 <= lo < hi <= 1.0):
        raise ValueError("need 0 <= lo < hi <= 1")
    sel = (m > lo * M) & (m < hi * M)
    if sel.sum() < 3:
        raise ValueError("only %d frames in the %g-%g band of the total mass: discharge too fast to fit" % (int(sel.sum()), lo, hi))
    A = np.column_stack([t[sel], np.ones(int(sel.sum()))])
    coef, *_ = np.linalg.lstsq(A, m[sel], rcond=None)
    resid = m[sel] - A @ coef
    return {"rate": float(coef[0]), "n_frames": int(sel.sum()), "t_range": (float(t[sel][0]), float(t[sel][-1])),
            "rms": float(np.sqrt(np.mean(resid ** 2)))}


def heap_mujoco_discharge(n_spheres: int = 1200, radius: float = 0.004, *, duration: float = 2.5, record_every: int = 25, **scene) -> dict:
    """:func:`heap_mujoco_pour` を走らせ、排出率を :func:`hopper_discharge_rate` で読み、Beverloo の式(正方孔は等価直径
    ``D_eq = √(4/π)·orifice_d``、粒径 2R、かさ密度はビンの実測)と比べる(**facade、mujoco が要る**)。
    返り: ``rate``, ``beverloo``, ``ratio``, ``D_eq``, ``run``(pour の返り)。比は桁の照合に留める(D₀/d が小さい・正方孔・
    コマ数が少ない —— 実測 0.99 だが別の構成では 1.02 / 1.14、一致が良すぎるので信用しない、と PoC に明記)。"""
    run = heap_mujoco_pour(n_spheres, radius, duration=duration, record_every=record_every, **scene)
    info = run["model_info"]
    dr = hopper_discharge_rate(run["mass_below"], run["times"], info["mass_total"])
    Deq = math.sqrt(4.0 / math.pi) * info["orifice_d"]
    Wb = beverloo_rate(Deq, 2.0 * run["radius"], info["bulk_density_bin"])
    return {"rate": dr["rate"], "beverloo": Wb, "ratio": dr["rate"] / Wb, "D_eq": Deq, "n_frames": dr["n_frames"], "run": run}


# ----------------------------------------------------------------------------------------------
# 基準面の傾きの警報(左右差)—— 既存 PoC の罠を op に
# ----------------------------------------------------------------------------------------------
def datum_tilt_check(result, warn_deg: float = 1.0) -> dict:
    """:func:`repose_angle_silhouette` の返り(左右の斜面角と地面の傾き)から **基準面が傾いていないか** を判定する。

    平らでない地面(datum)の傾き β は安息角に足し算される(既存の体積 PoC と同じ罠)。せん断型(``z' = z + x tan β``)
    なら左右の斜面は ``atan(tan φ ± tan β)``、カメラのロール(回転型)なら ``φ ± β`` —— **どちらも左右差 ≈ 2β** なので、
    左右差が ``warn_deg`` を超えたら警報。2 つの模型は 1 次で違う(β = 5 度・φ = 30 度で左の斜面が 33.62 対 35.00 度、
    実測)ので、両方の補正値を返し、どちらを使うかは地面の由来(高さ図の datum か、カメラの傾きか)で決める:
    ``phi_shear_deg``(tan の引き算、``ground_deg`` を使う)、``phi_roll_deg``(角の引き算 = 左右の平均そのもの)、
    ``beta_shear_deg``(左右の tan 差から読んだ β = atan((tan L − tan R)/2))、``beta_roll_deg``(= 左右差 / 2)。
    **Raises** ``ValueError``: 欄が無い / 角が範囲外 / ``warn_deg ≤ 0``。"""
    if not isinstance(result, dict) or not all(k in result for k in ("phi_left_deg", "phi_right_deg", "ground_deg")):
        raise ValueError("datum_tilt_check: need a repose_angle_silhouette result with phi_left_deg / phi_right_deg / ground_deg")
    w = _pos(warn_deg, "warn_deg")
    L = _angle(result["phi_left_deg"], "phi_left_deg")
    R = _angle(result["phi_right_deg"], "phi_right_deg")
    g = float(result["ground_deg"])
    if not math.isfinite(g) or abs(g) >= 45.0:
        raise ValueError("ground_deg must be finite and within (-45, 45), got %r" % result["ground_deg"])
    tl, tr, tg = math.tan(math.radians(L)), math.tan(math.radians(R)), math.tan(math.radians(g))
    asym = L - R
    phi_shear = 0.5 * (math.degrees(math.atan(tl - tg)) + math.degrees(math.atan(tr + tg)))
    return {"asymmetry_deg": asym, "ground_deg": g, "alarm": abs(asym) > w, "warn_deg": w,
            "phi_shear_deg": phi_shear, "phi_roll_deg": 0.5 * (L + R),
            "beta_shear_deg": math.degrees(math.atan(0.5 * (tl - tr))), "beta_roll_deg": 0.5 * asym}
