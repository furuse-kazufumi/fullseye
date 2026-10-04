# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pegsim — 柔らかい手首のペグ挿入(peg-in-hole)を、Whitney の準静的幾何と手首カメラの計測で門にする(2026-10-04)。

物理シミュ × Fullseye 系列の第 1 弾。真値は 2 つの外から来る:
  * **定理**: D. E. Whitney, "Quasi-Static Assembly of Compliantly Supported Rigid Parts", ASME J. Dyn. Sys. Meas. Control
    104(1), 65-77, 1982, DOI 10.1115/1.3149634。**原著は有料で未読**。式は著者本人の講義スライド(MIT OCW 2.875 Fall 2004,
    Class 3 "Rigid Part Mating", https://ocw.mit.edu/courses/2-875-mechanical-assembly-and-its-role-in-product-development-fall-2004/
    6abbc6934125042e12e9d153f87f9278_cls3_rgd_prt_mn4.pdf)の本文テキストから取った(図は著作権で抜かれているが式と記号は残る):
    p.9 二点接触の深さ l/d = c/θ と θ_m = √(2c)、p.11 clearance ratio c = (D − d)/D、p.28 くさび(wedging)の条件 θ > c/μ、
    p.34 かじり(jamming)の平行四辺形(頂点 (−1/μ, 2λ+1), (1/μ, −1), (1/μ, −(2λ+1)), (−1/μ, 1)、縦軸切片 ±λ、λ = l/(2rμ))。
    接触状態の遷移(無接触 → 面取り → 一点 → 二点)は Xu, Hou, Liu, Qiao, arXiv:1904.05240 §III.A の引用とも一致する。
  * **物理エンジン**: MuJoCo(≥ 3.x)の接触と mj_geomDistance。mujoco が要る関数は facade(fullseye.<名前>)だけに出し、台帳には
    numpy だけで動く op を載せる(:func:`humanoid_walk_clip` と同じ扱い)。

numpy 層(台帳 ``pegsim``、opsdrive):
  :func:`peg_params` 寸法 / :func:`whitney_clearance` c・θ_m・面取り許容・くさびの境目 / :func:`two_point_depth` 二点接触の深さ
  (厳密・小角・2-D 近似の 3 模型)/ :func:`wedging_check` / :func:`jamming_diagram` / :func:`chamfer_capture` /
  :func:`contact_state_predict` 真の姿勢から接触点数を幾何だけで予測(第 2 実装)/ :func:`circle_fit_known_radius` /
  :func:`cylinder_fit_known_radius` / :func:`coverage_edge_points` 反エイリアスの被覆率から副画素の縁 / :func:`hole_centre_from_rgbd` /
  :func:`peg_tip_from_rgbd` / :func:`peg_offset_from_rgbd` / :func:`peg_measure_overlay` / :func:`camera_world_to_cv` /
  :func:`peg_synthetic_rgbd` 真値つきの合成 RGB-D(解析的レイキャスト、mujoco 不要)/ :func:`insertion_grid_summary` /
  :func:`peg_scene_mjcf`(MJCF 文字列。mujoco 不要)。
mujoco 層(facade のみ): :func:`peg_scene_build` / :func:`peg_set_pose` / :func:`peg_wrist_render` / :func:`peg_contact_state` /
  :func:`peg_two_point_depth_sim` / :func:`peg_depth_sample_offset` / :func:`peg_insertion_run` / :func:`peg_insertion_grid`。

二点接触の深さは 3 次元の円柱で厳密に導いた(**導出**、原文の式ではない): 傾き θ・先端中心の深さ l(最狭部 = 面取りの底から)の
ペグが「先端の縁で遠い側の壁」+「反対側の最狭部の縁で胴」に同時に触れる条件は
    l · tan θ = 2R − r (cos θ + sec θ)                       … (1′)
cos θ + sec θ = 2 + O(θ⁴) なので l · sin θ ≈ l · tan θ ≈ 2 c_r(半径 clearance)が 4 次まで正確。試作の実測(mj_geomDistance の二分法)は
(1′) と 0.07 mm 以内で一致し、l₂·sin θ = 0.396〜0.398 mm(2c_r = 0.400 mm)。最初に書いた 2-D の長方形近似 D = d/cos θ + l tan θ は
縁の点の高さ r sin θ を無視するため θ = 6° で 0.5 mm ずれる —— :func:`two_point_depth` に ``model="rectangle"`` として残し、門で
「間違う量」を測る。

踏んだ罠(両方とも計測の規約を壊す):
  * **MSAA と深度**: MuJoCo の offsamples=4(既定)で描いた depth は、画素中心でなく **サンプル 0 の位置 (u − 0.125, v + 0.375) px の
    深度**になる(傾けた平面で実測、offsamples=0 なら画素中心)。Fullseye の camera.py も実物の RGB-D も画素中心を仮定するので、
    depth は ``offsamples=0`` で別にコンパイルした同じ場面から取る(:func:`peg_wrist_render`)。RGB は MSAA のまま(縁の反エイリアスが
    副画素情報を運ぶ)。
  * **円柱の既定スライス数**: MuJoCo の円柱は既定 numslices=28 の多角形で描かれ、半径が最大 r(1 − cos(π/28)) ≈ 0.6 % = 0.03〜0.04 mm
    内側に入る。depth から当てた半径が系統的に小さく出るので ``<quality numslices="128">`` にする(0.0015 %)。

計測(:func:`peg_offset_from_rgbd`)は 640×480 の手首 RGB-D 1 枚から、穴中心(反エイリアスの縁 → 平面に持ち上げ → 既知半径でなく
自由な円当てはめ)、ペグ先端(depth の点群 → 既知半径の円柱 → 影の端を投影した縁の円で合わせる模型)、相対ずれ (dx, dy)。
試作の実測(16 姿勢): 穴中心 ≤ 0.04 px、相対ずれ max 0.010 mm、先端の軸方向 0.83 px(目標 0.3 px は**未達**で、影の端 1 画素の
被覆率だけから軸方向を読む限界)。

規約: 長さは m、角は rad(引数名に _deg / _mm が付くものだけ度・mm)。穴の口の面が z = 0、穴の軸が世界 z 軸、面取りは
z ∈ [−W, 0]、最狭部(半径 R)は z = −W より下。Whitney の挿入深さ l は**最狭部から**先端中心まで(:func:`two_point_depth`)、
``depth`` は口の面から(:func:`contact_state_predict`)。画素座標は Fullseye の規約(画素中心が整数、主点 ((W−1)/2, (H−1)/2))。
"""
from __future__ import annotations

import math

import numpy as np

import camera
import imagedraw
import measure as _fsmeasure
import render3d

__all__ = [
    "peg_params", "whitney_clearance", "two_point_depth", "wedging_check", "jamming_diagram", "chamfer_capture",
    "contact_state_predict", "circle_fit_known_radius", "cylinder_fit_known_radius", "coverage_edge_points",
    "hole_centre_from_rgbd", "peg_tip_from_rgbd", "peg_offset_from_rgbd", "peg_measure_overlay", "camera_world_to_cv",
    "peg_synthetic_rgbd", "insertion_grid_summary", "peg_scene_mjcf",
    # mujoco が要る(facade のみ、台帳の外)
    "peg_scene_build", "peg_set_pose", "peg_wrist_render", "peg_contact_state", "peg_two_point_depth_sim",
    "peg_depth_sample_offset", "peg_insertion_run", "peg_insertion_grid", "peg_scene_close",
    "CONTACT_STATES",
]

#: 接触状態の語彙(Whitney の分類 + シミュレーション側の 2 語)
CONTACT_STATES = ("air", "chamfer", "one_point", "two_point", "inserting", "bottomed")

_FLIP = np.diag([1.0, -1.0, -1.0])      # MuJoCo カメラ(−Z を見る、+Y 上)→ OpenCV(+Z 前、+Y 下)


# ----------------------------------------------------------------------------------------------------------------------
# 寸法
def peg_params(r: float = 5.0e-3, R: float = 5.2e-3, hole_depth: float = 20.0e-3, chamfer: float = 1.0e-3,
               chamfer_deg: float = 45.0, peg_length: float = 40.0e-3, mu: float = 0.3, n_seg: int = 36,
               k_trans: float = 600.0, k_rot: float = 1.5, image_size=(640, 480), fovy_deg: float = 40.0) -> dict:
    """ペグと穴の寸法の表(m・rad): ペグ半径 r、穴半径 R、穴の深さ、面取りの幅と角、ペグ長、摩擦係数、手首剛性、手首カメラ。

    既定は試作の寸法: r = 5.0 mm、R = 5.2 mm(半径 clearance 0.2 mm、c = 0.0385)、深さ 20 mm、45° の面取り 1 mm、ペグ 40 mm、
    μ = 0.3(MuJoCo の滑り摩擦)。``n_seg`` は穴の壁を近似する箱の数(MJCF)、``k_trans`` [N/m]・``k_rot`` [N m/rad] は
    手首(コンプライアント支持)の並進・回転剛性、``image_size`` と ``fovy_deg`` は手首カメラ。
    **Raises** ``ValueError``: r ≤ 0、R ≤ r、面取りが穴より深い、μ < 0、面取り角が (0°, 90°) の外。"""
    r, R, hole_depth, chamfer, mu = float(r), float(R), float(hole_depth), float(chamfer), float(mu)
    if not (r > 0.0 and R > r):
        raise ValueError("peg_params: need 0 < r < R, got r=%r R=%r" % (r, R))
    if not (0.0 <= chamfer < hole_depth):
        raise ValueError("peg_params: chamfer must be in [0, hole_depth), got %r / %r" % (chamfer, hole_depth))
    if mu < 0.0:
        raise ValueError("peg_params: mu must be >= 0, got %r" % mu)
    if not (0.0 < float(chamfer_deg) < 90.0):
        raise ValueError("peg_params: chamfer_deg must be in (0, 90), got %r" % chamfer_deg)
    if int(n_seg) < 8:
        raise ValueError("peg_params: n_seg must be >= 8, got %r" % n_seg)
    w, h = int(image_size[0]), int(image_size[1])
    if w < 16 or h < 16:
        raise ValueError("peg_params: image_size too small %r" % (image_size,))
    return {"r": r, "R": R, "d": 2.0 * r, "D": 2.0 * R, "hole_depth": hole_depth, "chamfer": chamfer,
            "chamfer_deg": float(chamfer_deg), "peg_length": float(peg_length), "mu": mu, "n_seg": int(n_seg),
            "k_trans": float(k_trans), "k_rot": float(k_rot), "image_size": (w, h), "fovy_deg": float(fovy_deg)}


def _kp(kp) -> dict:
    """kp が None なら既定、dict なら必須の鍵を確認して返す(fail-closed)。"""
    if kp is None:
        return peg_params()
    if not isinstance(kp, dict):
        raise ValueError("pegsim: kp must be the dict from peg_params(), got %s" % type(kp).__name__)
    for k in ("r", "R", "hole_depth", "chamfer", "mu"):
        if k not in kp:
            raise ValueError("pegsim: kp lacks %r (use peg_params())" % k)
    return kp


# ----------------------------------------------------------------------------------------------------------------------
# Whitney の量
def whitney_clearance(kp=None) -> dict:
    """Whitney の無次元 clearance と、そこから決まる境目: c = (D − d)/D、c_r = R − r、θ_m = √(2c)、面取りの許容ずれ、くさびの角。

    返り: ``c``(clearance ratio、OCW p.11)、``c_r``(半径 clearance)、``theta_m``(小角の θ_m = √(2c)、p.9)、``theta_m_exact``
    (arccos(d/D): 水平断面の楕円の長半径 r/cos θ が R に達する角 —— √(2c) はその 2 次の近似)、``eps_chamfer_max``
    (W + c_r: 面取りが補正なしで救える初期横ずれ、導出)、``theta_wedge``(c/μ: 二点接触の始まりでこれより傾いていると
    くさびが起こりうる、p.28。μ = 0 なら inf)。"""
    kp = _kp(kp)
    r, R, mu = kp["r"], kp["R"], kp["mu"]
    c = (R - r) / R
    return {"c": c, "c_r": R - r, "theta_m": math.sqrt(2.0 * c), "theta_m_exact": math.acos(r / R),
            "eps_chamfer_max": kp["chamfer"] + (R - r), "theta_wedge": (c / mu) if mu > 0 else math.inf, "mu": mu}


def two_point_depth(kp, theta: float, model: str = "exact") -> float:
    """傾き θ [rad] で二点接触が始まる挿入深さ l₂ [m](最狭部から先端中心まで)。3 つの模型を名前で選ぶ。

    ``"exact"``: 3-D の円柱で厳密 l₂ = (2R − r(cos θ + sec θ)) / tan θ(導出 (1′))。``"small_angle"``: l₂ = 2c_r / sin θ
    (OCW p.9 の l/d = c/θ を半径 clearance で書いたもの)。``"rectangle"``: 2-D の長方形近似 (D − d/cos θ)/tan θ(縁の点の
    高さ r sin θ を無視するので θ = 6° で 0.5 mm 浅く出る —— 間違いの量を測るために残す)。
    **Raises** ``ValueError``: θ ≤ 0、θ ≥ θ_m_exact(入口にすら入らない)、未知の model。"""
    kp = _kp(kp)
    th = float(theta)
    r, R = kp["r"], kp["R"]
    if not (th > 0.0):
        raise ValueError("two_point_depth: theta must be > 0 rad (a straight peg never reaches two-point contact)")
    if th >= math.acos(r / R):
        raise ValueError("two_point_depth: theta=%.4f rad >= theta_m_exact=%.4f rad; the peg does not enter" % (th, math.acos(r / R)))
    if model == "exact":
        return (2.0 * R - r * (math.cos(th) + 1.0 / math.cos(th))) / math.tan(th)
    if model == "small_angle":
        return 2.0 * (R - r) / math.sin(th)
    if model == "rectangle":
        return (2.0 * R - 2.0 * r / math.cos(th)) / math.tan(th)
    raise ValueError("two_point_depth: model must be 'exact' | 'small_angle' | 'rectangle', got %r" % (model,))


def wedging_check(kp, theta: float) -> dict:
    """二点接触が始まる時点の傾き θ [rad] で、くさび(wedging)が起こりうるか(OCW p.28: θ > c/μ)。

    返り: ``possible``(θ > c/μ)、``theta_limit`` = c/μ、``l2``(その θ での二点接触の深さ、exact。θ ≥ θ_m_exact なら 0)、
    ``l2_over_d``、``lambda`` = l₂/(2rμ)、``possible_small_angle``(l₂/d < μ ⇔ λ < 1。小角では ``possible`` と同じ判定)。
    μ = 0 なら摩擦円錐が無いので常に False。"""
    kp = _kp(kp)
    th = float(theta)
    if th < 0.0:
        raise ValueError("wedging_check: theta must be >= 0")
    wc = whitney_clearance(kp)
    d, mu = 2.0 * kp["r"], kp["mu"]
    l2 = two_point_depth(kp, th, "exact") if 0.0 < th < wc["theta_m_exact"] else (0.0 if th > 0 else math.inf)
    lam = (l2 / (d * mu)) if mu > 0 else math.inf
    return {"possible": bool(mu > 0 and th > wc["theta_wedge"]), "theta": th, "theta_limit": wc["theta_wedge"], "l2": l2,
            "l2_over_d": l2 / d, "lambda": lam, "possible_small_angle": bool(mu > 0 and l2 / d < mu)}


def jamming_diagram(kp, depth: float, fx_over_fz: float | None = None, m_over_rfz: float | None = None) -> dict:
    """かじり(jamming)の図(OCW p.34): 二点接触の深さ l [m] で、加える力の比 (F_x/F_z, M/(rF_z)) が進める領域の平行四辺形。

    λ = l/(2rμ)。頂点は (−1/μ, 2λ+1), (1/μ, −1), (1/μ, −(2λ+1)), (−1/μ, 1)、縦軸の切片 ±λ、縦辺は F_x/F_z = ±1/μ。深さが増える
    (λ が増える)と縦に広がり、かじりにくくなる。``fx_over_fz`` と ``m_over_rfz`` を与えると ``inside``(内側なら進む)と
    ``margin``(4 辺の不等式の最小の余裕、負なら外)も返す。
    **Raises** ``ValueError``: l < 0、μ ≤ 0(摩擦なしは平行四辺形が無限に広い)。"""
    kp = _kp(kp)
    ell, mu, r = float(depth), kp["mu"], kp["r"]
    if ell < 0.0:
        raise ValueError("jamming_diagram: depth must be >= 0")
    if mu <= 0.0:
        raise ValueError("jamming_diagram: mu must be > 0 (no friction -> no jamming)")
    lam = ell / (2.0 * r * mu)
    verts = np.array([[-1.0 / mu, 2.0 * lam + 1.0], [1.0 / mu, -1.0], [1.0 / mu, -(2.0 * lam + 1.0)], [-1.0 / mu, 1.0]])
    out = {"lambda": lam, "vertices": verts, "fx_limit": 1.0 / mu, "intercept": lam, "slope": -(lam + 1.0) * mu}
    if fx_over_fz is not None and m_over_rfz is not None:
        x, y = float(fx_over_fz), float(m_over_rfz)
        s = -(lam + 1.0) * mu
        margins = (1.0 / mu - x, x + 1.0 / mu, (lam + s * x) - y, y - (-lam + s * x))
        out["margin"] = float(min(margins))
        out["inside"] = bool(out["margin"] >= 0.0)
    return out


def chamfer_capture(kp, eps0: float) -> dict:
    """初期の横ずれ ε₀ [m] を面取りが補正なしで吸収できるか: |ε₀| ≤ W + c_r(先端の縁が面取り面の上に着地する条件、導出)。

    返り: ``captured``、``eps_max`` = W + c_r、``margin`` = eps_max − |ε₀|。既定の寸法では 1.2 mm。
    傾き θ₀ があると先端の縁の投影が動くが、θ₀ ≤ 3° では無視できる(試作の格子で ε₀ = 2, 3 mm が補正なしで失敗した根拠)。"""
    kp = _kp(kp)
    emax = kp["chamfer"] + (kp["R"] - kp["r"])
    e = abs(float(eps0))
    return {"captured": bool(e <= emax + 1e-12), "eps_max": emax, "margin": emax - e, "eps0": e}


def _ellipse_reach(centre_xy, e1, e2, a1, a2, n=3600) -> float:
    """原点から、中心 centre・半軸 a1 e1 / a2 e2 の楕円の最遠点までの距離(標本化、誤差 ≈ a(π/n)²/2)。"""
    phis = np.linspace(0.0, 2.0 * math.pi, int(n), endpoint=False)
    pts = centre_xy[None, :] + a1 * np.cos(phis)[:, None] * e1[None, :] + a2 * np.sin(phis)[:, None] * e2[None, :]
    return float(np.max(np.linalg.norm(pts, axis=1)))


def contact_state_predict(kp, tip_xyz, axis, tol: float = 0.06e-3) -> dict:
    """真のペグ姿勢(先端中心と軸の向き)から、接触点の数と場所を**幾何だけで**予測する(接触計算と独立な第 2 実装)。

    先端の縁の円(半径 r、水平投影は e₁ 方向 r・傾き方向 r cos θ の楕円)が穴の最狭部の円 R(面取り帯では高さに応じた円錐の半径)に
    届けば「tip」、胴の最狭部(z = −W)での水平断面(半径 r と r/cos θ の楕円)が R に届けば「mouth」。胴が面取りの円錐に触れる
    場所は tan θ < 1 なら必ず最狭部の縁になる(円錐の半径は高さに 1 で増え、断面の中心は tan θ でしか動かない)。
    返り: ``n``(0/1/2)、``where``("none" / "chamfer" / "tip" / "mouth" / "tip+mouth")、``depth``(口の面からの先端深さ、
    負なら空中)、``depth_below_chamfer``、``tilt`` [rad]。``tol`` は「届いた」とみなす半径方向の余裕。
    **Raises** ``ValueError``: axis がゼロ、tip_xyz の形が (3,) でない。"""
    kp = _kp(kp)
    tip = np.asarray(tip_xyz, np.float64).reshape(-1)
    a = np.asarray(axis, np.float64).reshape(-1)
    if tip.shape != (3,) or a.shape != (3,):
        raise ValueError("contact_state_predict: tip_xyz and axis must be 3-vectors")
    na = float(np.linalg.norm(a))
    if na < 1e-12:
        raise ValueError("contact_state_predict: axis is zero")
    a = a / na
    if a[2] < 0:
        a = -a                                               # 軸は先端から上へ
    r, R, W = kp["r"], kp["R"], kp["chamfer"]
    th = math.atan2(math.hypot(float(a[0]), float(a[1])), abs(float(a[2])))   # acos(|a_z|) は 0 近傍で √ε の床(1e-8 rad)を持つ
    ax = a[:2]
    nxy = float(np.linalg.norm(ax))
    u = ax / nxy if nxy > 1e-12 else np.array([1.0, 0.0])
    e1 = np.array([-u[1], u[0]])
    depth = -float(tip[2])
    out = {"depth": depth, "depth_below_chamfer": depth - W, "tilt": th}
    if depth <= 0.0:
        out.update(n=0, where="none")
        return out
    rim_reach = _ellipse_reach(tip[:2], e1, u, r, r * math.cos(th))
    if depth < W:                                            # 先端は面取りの帯の中
        cone_r = R + (W - depth)
        hit = rim_reach >= cone_r - tol
        out.update(n=int(hit), where="chamfer" if hit else "none")
        return out
    where = []
    if rim_reach >= R - tol:
        where.append("tip")
    if abs(a[2]) > 1e-9:
        c0 = tip[:2] + a[:2] * ((depth - W) / a[2])          # 軸が最狭部 z = −W を貫く点
        if _ellipse_reach(c0, e1, u, r, r / math.cos(th)) >= R - tol:
            where.append("mouth")
    out.update(n=len(where), where="+".join(where) if where else "none")
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 既知半径の当てはめ
def circle_fit_known_radius(points, r: float, iters: int = 30) -> dict:
    """半径 r が既知の円を 2-D 点列 (row, col) に当てる(中心だけを Gauss-Newton で解く。部分弧でも安定)。

    :func:`measure.fit_circle`(代数的、半径も未知)と同じ入出力の規約(``cy``・``cx``・``rms``)。ペグの断面のように半径が
    図面で分かっている対象は、半径を固定したほうが短い弧でも中心が決まる(自由な当てはめは弧が短いと半径と中心が相殺する)。
    **Raises** ``ValueError``: 点が 2 つ未満、非有限、r ≤ 0。"""
    p = np.asarray(points, np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 2:
        raise ValueError("circle_fit_known_radius: points must be (N >= 2, 2) of (row, col)")
    if not np.all(np.isfinite(p)):
        raise ValueError("circle_fit_known_radius: points contain non-finite values")
    r = float(r)
    if not (r > 0.0):
        raise ValueError("circle_fit_known_radius: r must be > 0")
    q = p[:, ::-1]                                           # (x, y)
    c = q.mean(axis=0)
    d = q - c
    nrm = np.linalg.norm(d, axis=1)
    if nrm.sum() > 0:                                        # 弧の反対側へ中心を押して始める
        c = c - r * 0.6 * (d.sum(axis=0) / nrm.sum())
    for _ in range(int(iters)):
        d = q - c
        dist = np.linalg.norm(d, axis=1)
        res = dist - r
        J = -d / np.maximum(dist[:, None], 1e-12)
        step = np.linalg.lstsq(J, -res, rcond=None)[0]
        c = c + step
        if np.linalg.norm(step) < 1e-12:
            break
    res = np.linalg.norm(q - c, axis=1) - r
    return {"cy": float(c[1]), "cx": float(c[0]), "r": r, "rms": float(np.sqrt(np.mean(res ** 2))), "n": int(len(q))}


def cylinder_fit_known_radius(points, r: float, axis_point, axis, iters: int = 25) -> dict:
    """半径 r が既知の円柱を 3-D 点群 (N, 3) に当てる: 軸上の点(軸に垂直な 2 自由度)と軸の向き(2 自由度)を Gauss-Newton で。

    初期値 ``axis_point``・``axis`` から出発し、残差 = 軸からの距離 − r。返り: ``axis_point``(3,)、``axis``(単位、入力の向きを保つ)、
    ``rms``、``n``。**Raises** ``ValueError``: 点が 5 未満、r ≤ 0、axis がゼロ。"""
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3 or len(P) < 5:
        raise ValueError("cylinder_fit_known_radius: points must be (N >= 5, 3)")
    r = float(r)
    if not (r > 0.0):
        raise ValueError("cylinder_fit_known_radius: r must be > 0")
    a = np.asarray(axis, np.float64).reshape(3)
    if np.linalg.norm(a) < 1e-12:
        raise ValueError("cylinder_fit_known_radius: axis is zero")
    a = a / np.linalg.norm(a)
    a_in = a.copy()
    c = np.asarray(axis_point, np.float64).reshape(3)

    def basis(ax):
        b1 = np.cross(ax, [0.0, 1.0, 0.0]) if abs(ax[1]) < 0.9 else np.cross(ax, [1.0, 0.0, 0.0])
        b1 /= np.linalg.norm(b1)
        return b1, np.cross(ax, b1)

    def resid(cc, ax):
        dd = P - cc
        perp = dd - np.outer(dd @ ax, ax)
        return np.linalg.norm(perp, axis=1) - r

    def apply(x, cc, ax):
        b1, b2 = basis(ax)
        c2 = cc + x[0] * b1 + x[1] * b2
        a2 = ax + x[2] * b1 + x[3] * b2
        return c2, a2 / np.linalg.norm(a2)

    r0 = resid(c, a)
    eps = 1e-7
    for _ in range(int(iters)):
        J = np.empty((len(P), 4))
        for j in range(4):
            x = np.zeros(4)
            x[j] = eps
            c2, a2 = apply(x, c, a)
            J[:, j] = (resid(c2, a2) - r0) / eps
        step = np.linalg.lstsq(J, -r0, rcond=None)[0]
        c, a = apply(step, c, a)
        r0 = resid(c, a)
        if np.linalg.norm(step) < 1e-10:
            break
    if a @ a_in < 0:
        a = -a
    return {"axis_point": c, "axis": a, "rms": float(np.sqrt(np.mean(r0 ** 2))), "n": int(len(P))}


# ----------------------------------------------------------------------------------------------------------------------
# 画像計測
def _shift(m, dy, dx):
    out = np.zeros_like(m)
    H, W = m.shape
    ys, ye = max(0, dy), min(H, H + dy)
    xs, xe = max(0, dx), min(W, W + dx)
    out[ys:ye, xs:xe] = m[ys - dy:ye - dy, xs - dx:xe - dx]
    return out


def _dilate(m, n=1):
    for _ in range(int(n)):
        m = m | _shift(m, 1, 0) | _shift(m, -1, 0) | _shift(m, 0, 1) | _shift(m, 0, -1)
    return m


def _erode(m, n=1):
    for _ in range(int(n)):
        m = m & _shift(m, 1, 0) & _shift(m, -1, 0) & _shift(m, 0, 1) & _shift(m, 0, -1)
    return m


def _largest_component(mask):
    """最大の 4 連結成分(膨張の反復による flood fill、numpy だけ)。"""
    remaining = mask.copy()
    comps = []
    while remaining.any() and len(comps) <= 12:
        ys, xs = np.nonzero(remaining)
        seed = np.zeros_like(mask)
        seed[ys[0], xs[0]] = True
        prev = 0
        while True:
            seed = _dilate(seed) & remaining
            n = int(seed.sum())
            if n == prev:
                break
            prev = n
        comps.append(seed)
        remaining &= ~seed
    if not comps:
        return mask
    return max(comps, key=lambda c: int(c.sum()))


def _fit_plane(P):
    c0 = P.mean(axis=0)
    _, _, vt = np.linalg.svd(P - c0, full_matrices=False)
    n = vt[2]
    if n[2] > 0:
        n = -n                                               # 法線はカメラ側(−Z)へ
    return c0, n


def _classify(rgb):
    """色だけの粗い分類: (plate, dark, peg) の bool マスク。試作の場面の色(ペグ 橙、板 灰、穴 黒)に合わせた閾値。"""
    a = np.asarray(rgb).astype(np.float64)
    if a.ndim != 3 or a.shape[2] != 3:
        raise ValueError("pegsim: rgb must be (H, W, 3)")
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    gray = a.mean(axis=-1)
    peg = (r > 80) & (r - b > 50) & (r > g + 20)
    plate = (gray > 120) & ~peg & ((a.max(-1) - a.min(-1)) < 30)
    dark = (gray < 110) & ~peg
    return plate, dark, peg


def coverage_edge_points(gray, inside, outside, min_contrast: float = 25.0, exclude=None) -> np.ndarray:
    """反エイリアスされた境界の明るさ(被覆率)から副画素の縁の点 (u, v) を返す: inside 側の画素 p と 2 画素先が outside の対で、
    縁の位置 = p から (−0.5 + f_p + f_q) 画素(f = その画素の inside 側の被覆率 = (I − I_out) / (I_in − I_out))。

    4 軸方向(上下左右)の対を全部使う。``inside`` / ``outside`` は bool マスク(同じ形)、``gray`` は明るさ(float)。
    ``min_contrast`` 未満の対は捨て、``exclude`` のマスクに掛かる対も捨てる。返りは (N, 2) の (u, v)(列・行)。
    **Raises** ``ValueError``: 形が違う、対が 1 つも無い。"""
    g = np.asarray(gray, np.float64)
    ins = np.asarray(inside, bool)
    outs = np.asarray(outside, bool)
    if g.ndim != 2 or ins.shape != g.shape or outs.shape != g.shape:
        raise ValueError("coverage_edge_points: gray / inside / outside must share one (H, W) shape")
    ex = np.zeros_like(ins) if exclude is None else np.asarray(exclude, bool)
    if ex.shape != g.shape:
        raise ValueError("coverage_edge_points: exclude must be (H, W)")
    I_in = float(np.median(g[ins])) if ins.any() else 0.0
    pts = []
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        q_out = _shift(outs, -dy, -dx)                       # q = p + (dy, dx) が outside
        q2_out = _shift(outs, -2 * dy, -2 * dx)
        pair = ins & q_out & q2_out & ~ex
        ys, xs = np.nonzero(pair)
        if len(ys) == 0:
            continue
        I_p = g[ys, xs]
        I_q = g[ys + dy, xs + dx]
        I_q2 = g[ys + 2 * dy, xs + 2 * dx]
        contrast = I_in - I_q2
        ok = contrast > float(min_contrast)
        f_p = np.clip((I_p - I_q2) / np.maximum(contrast, 1e-9), 0, 1)
        f_q = np.clip((I_q - I_q2) / np.maximum(contrast, 1e-9), 0, 1)
        off = -0.5 + f_p + f_q
        pts.append(np.column_stack([xs + off * dx, ys + off * dy])[ok])
    if not pts or sum(len(p) for p in pts) == 0:
        raise ValueError("coverage_edge_points: no inside/outside pixel pair with enough contrast")
    return np.vstack(pts)


def hole_centre_from_rgbd(rgb, depth, K, peg_mask=None, radius: float | None = None) -> dict:
    """手首 RGB-D 1 枚から穴(暗い円盤)の中心を 3-D(カメラ座標)で: 板の平面を depth で当て、反エイリアスの縁を平面に持ち上げ、
    平面内で円を当てる(:func:`measure.fit_circle`)。

    画像面の楕円当てはめ(:func:`measure.fit_ellipse`)も参考に返すが、透視では楕円の中心 ≠ 円の中心の投影(試作で最大 1.9 px の
    偏り)なので 3-D で当てる。``radius`` に治具の図面の値(面取りの外径 R + W)を渡すと :func:`circle_fit_known_radius` で中心だけを
    解く —— ペグが低く構えて縁の半分近くを隠す姿勢(ε = −3 mm、高さ 4 mm)では自由な当てはめの 0.18 px が既知半径で 0.05 px になる。
    返り: ``centre_cam``(3,)、``radius``、``rms_circle``、``n_edge``、``edge_uv``、``plane_n``・``plane_c``、
    ``ellipse``、``uv``(中心の投影)、``peg``(ペグのマスク)。``depth`` は画素中心の +Z 距離 [m](MSAA の深度は使わない)。
    **Raises** ``RuntimeError``: 縁が見つからない。"""
    rgb = np.asarray(rgb)
    depth = np.asarray(depth, np.float64)
    plate, dark, peg = _classify(rgb)
    if depth.shape != plate.shape:
        raise ValueError("hole_centre_from_rgbd: depth must be (H, W) matching rgb")
    if peg_mask is None:
        peg_mask = peg
    dark = _largest_component(dark & ~_dilate(peg_mask, 2))
    near_peg = _dilate(peg_mask, 4)
    gray = rgb.astype(np.float64).mean(axis=-1)
    roi = _dilate(dark, 24)
    band = roi & plate & ~near_peg & ~dark
    ys, xs = np.nonzero(band)
    if len(ys) < 20:
        raise RuntimeError("hole_centre_from_rgbd: not enough plate pixels around the hole")
    P = camera.backproject(np.column_stack([xs, ys]), depth[ys, xs], K)
    c0, n = _fit_plane(P)
    for _ in range(2):                                       # 平面から外れた画素を捨てて当て直す
        dz = (P - c0) @ n
        keep = np.abs(dz) < 0.15e-3
        if keep.sum() >= 10:
            c0, n = _fit_plane(P[keep])
    yy, xx = np.nonzero(roi)
    Pr = camera.backproject(np.column_stack([xx, yy]), depth[yy, xx], K)
    dzr = np.abs((Pr - c0) @ n)
    on_plane = np.zeros_like(plate)
    on_plane[yy, xx] = dzr < 0.06e-3
    off_plane = np.zeros_like(plate)
    off_plane[yy, xx] = dzr > 0.10e-3
    plate_d = on_plane & ~peg_mask
    dark_d = off_plane & ~peg_mask
    try:
        uv = coverage_edge_points(gray, plate_d, dark_d, exclude=near_peg)
    except ValueError as exc:
        raise RuntimeError("hole_centre_from_rgbd: no hole edge found (%s)" % exc)
    rays = camera.backproject(uv, 1.0, K)
    tpar = (c0 @ n) / (rays @ n)
    E = rays * tpar[:, None]
    e1 = np.cross(n, [0.0, 0.0, 1.0])
    e1 = e1 / np.linalg.norm(e1) if np.linalg.norm(e1) > 1e-9 else np.array([1.0, 0.0, 0.0])
    e2 = np.cross(n, e1)
    xy = np.column_stack([(E - c0) @ e1, (E - c0) @ e2])
    def _fit(pts_rc):
        if radius is None:
            return _fsmeasure.fit_circle(pts_rc)
        return circle_fit_known_radius(pts_rc, float(radius))

    circ = _fit(np.column_stack([xy[:, 1], xy[:, 0]]))
    resid = np.hypot(xy[:, 0] - circ["cx"], xy[:, 1] - circ["cy"]) - circ["r"]
    keep = np.abs(resid) < max(3.0 * float(np.std(resid)), 1e-6)
    if keep.sum() >= 8:
        circ = _fit(np.column_stack([xy[keep, 1], xy[keep, 0]]))
    centre = c0 + circ["cx"] * e1 + circ["cy"] * e2
    ell = _fsmeasure.fit_ellipse(np.column_stack([uv[:, 1], uv[:, 0]])) if len(uv) >= 5 else None
    uv_c, _ = camera.project_points(centre[None, :], K)
    return {"centre_cam": centre, "radius": circ["r"], "rms_circle": circ["rms"], "n_edge": int(len(uv)), "edge_uv": uv,
            "plane_n": n, "plane_c": c0, "ellipse": ell, "uv": uv_c[0], "peg": peg}


def peg_tip_from_rgbd(rgb, depth, K, r_peg: float = 5.0e-3, peg_mask=None) -> dict:
    """手首 RGB-D 1 枚からペグ先端の中心を 3-D(カメラ座標)で: ペグの画素 → depth の点群 → PCA の軸 → 既知半径の円柱当てはめ、
    先端の軸方向は影の端(副画素、被覆率)を、投影した縁の円の端と一致させる模型で決める。

    返り: ``tip_cam``(3,)、``axis``(先端 → 上、単位)、``rms_cyl``、``n_pts``、``uv``(先端の投影)、``delta_axial``。
    正直に: 試作の 16 姿勢で軸方向の誤差 max 0.83 px(横方向 0.004 px)—— 影の端 1 画素の被覆率だけから軸方向を読む限界で、
    目標 0.3 px は未達。**Raises** ``RuntimeError``: ペグが見えない(芯の画素 < 50)。"""
    rgb = np.asarray(rgb)
    depth = np.asarray(depth, np.float64)
    if peg_mask is None:
        _, _, peg_mask = _classify(rgb)
    core = _erode(peg_mask, 2)
    ys, xs = np.nonzero(core)
    if len(ys) < 50:
        raise RuntimeError("peg_tip_from_rgbd: peg not visible (%d core pixels)" % len(ys))
    P = camera.backproject(np.column_stack([xs, ys]), depth[ys, xs], K)
    c0 = P.mean(axis=0)
    _, _, vt = np.linalg.svd(P - c0, full_matrices=False)
    a = vt[0]
    uv0, _ = camera.project_points(c0[None, :], K)
    uv1, _ = camera.project_points((c0 + 1e-3 * a)[None, :], K)
    if (uv1 - uv0)[0, 1] > 0:                                # +a が画像の下へ向くなら反転(先端は下)
        a = -a
    e1 = np.cross(a, [0.0, 1.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    q = np.column_stack([(P - c0) @ e2, (P - c0) @ e1])      # (row, col) 規約
    cq = circle_fit_known_radius(q, float(r_peg))
    axis_pt = c0 + cq["cx"] * e1 + cq["cy"] * e2
    fit = cylinder_fit_known_radius(P, float(r_peg), axis_pt, a)
    axis_pt, a = fit["axis_point"], fit["axis"]
    t_min = float(((P - axis_pt) @ a).min())
    gray = rgb.astype(np.float64).mean(axis=-1)
    uvA, _ = camera.project_points(np.vstack([axis_pt, axis_pt - 1e-3 * a]), K)
    v_img = uvA[1] - uvA[0]
    v_img /= np.linalg.norm(v_img)
    ys_f, xs_f = np.nonzero(peg_mask)
    s = xs_f * v_img[0] + ys_f * v_img[1]
    k = int(np.argmax(s))
    py, px = ys_f[k], xs_f[k]
    H, W = gray.shape
    by = min(max(int(round(py + 2 * v_img[1])), 0), H - 1)
    bx = min(max(int(round(px + 2 * v_img[0])), 0), W - 1)
    rgbf = rgb.astype(np.float64)
    c_in = np.median(rgbf[core], axis=0)
    c_out = rgbf[by, bx]
    denom = c_in - c_out
    f = float(np.clip(((rgbf[py, px] - c_out) @ denom) / max(float(denom @ denom), 1e-9), 0, 1))
    s_obs = float(s[k]) - 0.5 + f
    e1 = np.cross(a, [0.0, 1.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    phis = np.linspace(0.0, 2.0 * np.pi, 720, endpoint=False)
    ring = float(r_peg) * (np.cos(phis)[:, None] * e1 + np.sin(phis)[:, None] * e2)

    def s_pred(delta):
        T = axis_pt + a * (t_min + delta)
        uv, _ = camera.project_points(T + ring, K)
        return float(np.max(uv @ v_img))

    d0, d1 = 0.0, -1e-3
    s0, s1 = s_pred(d0), s_pred(d1)
    for _ in range(8):                                       # 割線法
        if abs(s1 - s0) < 1e-12:
            break
        d2 = d1 - (s1 - s_obs) * (d1 - d0) / (s1 - s0)
        d0, s0 = d1, s1
        d1, s1 = d2, s_pred(d2)
        if abs(s1 - s_obs) < 1e-4:
            break
    tip = axis_pt + a * (t_min + d1)
    uv_tip, _ = camera.project_points(tip[None, :], K)
    return {"tip_cam": tip, "axis": a, "rms_cyl": fit["rms"], "n_pts": int(len(P)), "uv": uv_tip[0],
            "delta_axial": float(d1), "t_min": t_min, "silhouette_s": s_obs}


def peg_offset_from_rgbd(rgb, depth, K, R_cam_to_world, r_peg: float = 5.0e-3, hole_radius: float | None = None) -> dict:
    """手首 RGB-D 1 枚から、穴中心に対するペグ先端の相対ずれ (dx, dy) [m] を世界(搬送台)座標で —— 視覚サーボの観測量。

    ``R_cam_to_world`` はカメラ座標のベクトルを世界へ回す 3×3(hand-eye)。ずれは板の平面内の成分、``height`` は先端の板からの高さ。
    ``hole_radius`` を与えると穴の円を既知半径で当てる(:func:`hole_centre_from_rgbd`)。
    返り: ``hole``・``tip``(各計測の dict)、``dx``・``dy``・``height``。試作(16 姿勢): |dx|, |dy| の最大 0.010 mm。"""
    Rcw = np.asarray(R_cam_to_world, np.float64)
    if Rcw.shape != (3, 3):
        raise ValueError("peg_offset_from_rgbd: R_cam_to_world must be 3x3")
    _, _, peg = _classify(rgb)
    hole = hole_centre_from_rgbd(rgb, depth, K, peg_mask=peg, radius=hole_radius)
    tip = peg_tip_from_rgbd(rgb, depth, K, r_peg=r_peg, peg_mask=peg)
    n = hole["plane_n"]
    delta = tip["tip_cam"] - hole["centre_cam"]
    dw = Rcw @ (delta - (delta @ n) * n)
    return {"hole": hole, "tip": tip, "dx": float(dw[0]), "dy": float(dw[1]), "height": float(delta @ n)}


def peg_synthetic_rgbd(kp=None, tip_xyz=(0.002, 0.001, 0.010), axis=(0.0, 0.0, 1.0), width: int = 320, height: int = 240,
                       supersample: int = 4, cam_pos=(-0.06, 0.0, 0.07), fovy_deg: float = 40.0) -> dict:
    """真値つきの合成 RGB-D(numpy だけ、mujoco 不要): 板 z = 0(灰)、穴の円盤(半径 R + W、黒、4 mm 下の面)、ペグ(半径 r の円柱 +
    先端の円盤、橙)を手首カメラ(45° 下向き、MJCF と同じ向き)から解析的にレイキャストする。

    深度は**画素中心**の +Z 距離(実物の RGB-D と Fullseye の規約)、色は ``supersample``² 倍の超標本の平均(反エイリアス = 被覆率)。
    計測(:func:`peg_offset_from_rgbd`)の門を mujoco 無しで立てるための入力で、MuJoCo の描画の代わりではない(影・照明・面取りの
    斜面は描かない)。返り: ``rgb``(H, W, 3) uint8、``depth``(H, W)、``K``、``R``・``t``(世界 → カメラ)、``R_cam_to_world``、
    ``tip``・``axis``(真値)、``uv_tip``・``uv_hole``(真値の投影)。**Raises** ``ValueError``: axis がゼロ、大きさが小さすぎる。"""
    kp = _kp(kp)
    W, H = int(width), int(height)
    if W < 32 or H < 32:
        raise ValueError("peg_synthetic_rgbd: width/height must be >= 32")
    a = np.asarray(axis, np.float64).reshape(3)
    if np.linalg.norm(a) < 1e-12:
        raise ValueError("peg_synthetic_rgbd: axis is zero")
    a = a / np.linalg.norm(a)
    tip = np.asarray(tip_xyz, np.float64).reshape(3)
    r, hole_r = kp["r"], kp["R"] + kp["chamfer"]
    K = render3d.intrinsics_from_fov(float(fovy_deg), W, H)
    s2 = 1 / math.sqrt(2)
    xw = np.array([0.0, -1.0, 0.0])
    yw = np.array([s2, 0.0, s2])
    ext = camera_world_to_cv(np.column_stack([xw, yw, np.cross(xw, yw)]), np.asarray(cam_pos, np.float64))
    R, t = ext["R"], ext["t"]
    cam_w = -R.T @ t
    col_plate, col_hole, col_peg = np.array([140, 140, 135.0]), np.array([12, 12, 15.0]), np.array([184, 84, 18.0])

    def trace(u, v):
        d = camera.backproject(np.column_stack([u, v]), 1.0, K) @ R
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        n = len(d)
        depth = np.full(n, np.inf)
        col = np.zeros((n, 3))
        tz = -cam_w[2] / d[:, 2]
        hit = tz > 0
        X = cam_w[None, :] + tz[:, None] * d
        in_hole = hit & (np.hypot(X[:, 0], X[:, 1]) < hole_r)
        tsel = np.where(in_hole, (-0.004 - cam_w[2]) / d[:, 2], tz)
        depth[hit] = tsel[hit]
        col[hit] = np.where(in_hole[hit, None], col_hole, col_plate)
        oc = cam_w - tip
        dd = d - np.outer(d @ a, a)
        oo = oc - (oc @ a) * a
        A = np.einsum("ij,ij->i", dd, dd)
        B = 2 * dd @ oo
        C = oo @ oo - r * r
        disc = B * B - 4 * A * C
        ok = (disc > 0) & (A > 1e-18)
        tcyl = np.where(ok, (-B - np.sqrt(np.where(ok, disc, 0))) / np.where(ok, 2 * A, 1), np.inf)
        Pc = cam_w[None, :] + np.where(np.isfinite(tcyl), tcyl, 0.0)[:, None] * d
        tax = (Pc - tip) @ a
        ok &= (tax >= 0) & (tax <= kp["peg_length"]) & (tcyl > 0)
        denom = d @ a
        safe = np.abs(denom) > 1e-12
        tdisc = np.where(safe, -(oc @ a) / np.where(safe, denom, 1), np.inf)
        Pd = cam_w[None, :] + np.where(np.isfinite(tdisc), tdisc, 0.0)[:, None] * d
        okd = (tdisc > 0) & (np.linalg.norm(Pd - tip - ((Pd - tip) @ a)[:, None] * a, axis=1) <= r)
        tpeg = np.minimum(np.where(ok, tcyl, np.inf), np.where(okd, tdisc, np.inf))
        peg_hit = tpeg < depth
        depth[peg_hit] = tpeg[peg_hit]
        col[peg_hit] = col_peg
        return depth * (d @ R.T[:, 2]), col

    v, u = np.mgrid[0:H, 0:W].astype(np.float64)
    depth = trace(u.ravel(), v.ravel())[0].reshape(H, W)
    ss = max(1, int(supersample))
    acc = np.zeros((H * W, 3))
    offs = (np.arange(ss) + 0.5) / ss - 0.5
    for du in offs:
        for dv in offs:
            acc += trace(u.ravel() + du, v.ravel() + dv)[1]
    rgb = np.clip(acc / (ss * ss), 0, 255).reshape(H, W, 3).astype(np.uint8)
    uv, _ = camera.project_points(np.vstack([tip, [0.0, 0.0, 0.0]]), K, R, t)
    return {"rgb": rgb, "depth": depth, "K": K, "R": R, "t": t, "R_cam_to_world": R.T, "tip": tip, "axis": a,
            "uv_tip": uv[0], "uv_hole": uv[1]}


def camera_world_to_cv(cam_xmat, cam_xpos) -> dict:
    """MuJoCo のカメラ姿勢(``d.cam_xmat`` 3×3 = 世界でのカメラ軸、``d.cam_xpos``)を OpenCV / Fullseye の外部パラメータに:
    X_cv = R X_w + t、R = diag(1, −1, −1) Rwcᵀ、t = −R p(MuJoCo は −Z を見て +Y が上、OpenCV は +Z 前で +Y 下)。

    返り: ``R``(3×3)、``t``(3,)、``R_cam_to_world`` = Rᵀ。numpy だけ(mujoco 不要)。**Raises** ``ValueError``: 形が違う、R が回転でない。"""
    Rwc = np.asarray(cam_xmat, np.float64).reshape(3, 3)
    p = np.asarray(cam_xpos, np.float64).reshape(3)
    if not np.allclose(Rwc @ Rwc.T, np.eye(3), atol=1e-6) or abs(np.linalg.det(Rwc) - 1.0) > 1e-6:
        raise ValueError("camera_world_to_cv: cam_xmat is not a rotation")
    R = _FLIP @ Rwc.T
    return {"R": R, "t": -R @ p, "R_cam_to_world": R.T}


def insertion_grid_summary(rows) -> dict:
    """成功率の格子を集計する: 行 = {eps_mm, tilt_deg, correct, success} の列から、補正あり/なし × ε₀ × θ₀ の成功率の表と、
    「補正なしで全部成功する最大の ε₀」「補正ありの成功数 / 総数」。

    返り: ``eps_mm``・``tilt_deg``(軸)、``rate``: {False: (n_eps, n_tilt) の配列, True: 同}、``n_runs``、``max_eps_all_ok``:
    {correct: その補正で全 θ₀ が成功する最大の ε₀(無ければ None)}、``success_count``: {correct: (成功数, 総数)}。
    **Raises** ``ValueError``: 行が空、鍵が欠ける。"""
    rows = list(rows)
    if not rows:
        raise ValueError("insertion_grid_summary: no rows")
    for k in ("eps_mm", "tilt_deg", "correct", "success"):
        if any(k not in rw for rw in rows):
            raise ValueError("insertion_grid_summary: every row needs %r" % k)
    eps = sorted({float(rw["eps_mm"]) for rw in rows})
    tilts = sorted({float(rw["tilt_deg"]) for rw in rows})
    out = {"eps_mm": eps, "tilt_deg": tilts, "rate": {}, "n_runs": {}, "max_eps_all_ok": {}, "success_count": {}}
    for corr in (False, True):
        rate = np.full((len(eps), len(tilts)), np.nan)
        cnt = np.zeros((len(eps), len(tilts)), int)
        ok_total = tot = 0
        for rw in rows:
            if bool(rw["correct"]) != corr:
                continue
            i, j = eps.index(float(rw["eps_mm"])), tilts.index(float(rw["tilt_deg"]))
            s = 1.0 if rw["success"] else 0.0
            rate[i, j] = s if cnt[i, j] == 0 else (rate[i, j] * cnt[i, j] + s) / (cnt[i, j] + 1)
            cnt[i, j] += 1
            ok_total += int(s)
            tot += 1
        out["rate"][corr] = rate
        out["n_runs"][corr] = cnt
        out["success_count"][corr] = (ok_total, tot)
        best = None
        for i, e in enumerate(eps):
            row = rate[i]
            if np.all(np.isfinite(row)) and np.all(row >= 1.0 - 1e-12):
                best = e
        out["max_eps_all_ok"][corr] = best
    return out


# ----------------------------------------------------------------------------------------------------------------------
# MJCF(mujoco 不要)
def _quat_axis(axis, ang):
    ax = np.asarray(axis, np.float64)
    ax = ax / np.linalg.norm(ax)
    return np.array([math.cos(ang / 2), *(math.sin(ang / 2) * ax)])


def _quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def peg_scene_mjcf(kp=None, lg: float | None = None, offsamples: int = 4, timestep: float = 5e-4) -> str:
    """場面の MJCF 文字列(mujoco 不要): 穴 = 内接面が半径 R の箱 n_seg 個の環 + 45° の面取りの環 + 口の面の襟 + 四角い枠、
    位置制御の搬送台(x, y, z のスライド)に 6 つのばね関節の柔らかい手首、その先にペグ(円柱)。手首カメラは搬送台の 60 mm 後ろ・
    20 mm 上から 45° 下向き、側面カメラは固定。

    ``lg`` = 先端から回転のコンプライアンス中心までの距離(None → 手首原点 = ペグ長、0 → 先端に中心 = RCC)。``offsamples`` は
    MSAA(RGB 用 4、depth 用 0 で別にコンパイルする —— 深度はサンプル 0 の位置になる罠)。``<quality numslices="128">`` で円柱の
    多角形近似を 0.0015 % に(既定 28 では半径が 0.04 mm 内側)。単位 m、口の面 z = 0。"""
    kp = _kp(kp)
    r, R, H, W = kp["r"], kp["R"], kp["hole_depth"], kp["chamfer"]
    L = kp["peg_length"]
    mu, n_seg = kp["mu"], kp["n_seg"]
    wall_t = 6.0e-3
    lg = L if lg is None else float(lg)
    hinge_z = -(L - lg)
    img_w, img_h = kp["image_size"]
    seg = []
    dphi = 2.0 * math.pi / n_seg
    tan_half = math.tan(dphi / 2.0)
    for i in range(n_seg):
        phi = i * dphi
        c, s = math.cos(phi), math.sin(phi)
        qz = "%.9f 0 0 %.9f" % (math.cos(phi / 2), math.sin(phi / 2))
        rc = R + wall_t / 2
        hy = (R + wall_t) * tan_half * 1.02
        hz = (H - W) / 2
        zc = -(W + hz)
        seg.append('<geom name="wall%d" type="box" size="%.6f %.6f %.6f" pos="%.7f %.7f %.7f" quat="%s" '
                   'rgba="0.05 0.05 0.06 1" class="hole"/>' % (i, wall_t / 2, hy, hz, rc * c, rc * s, zc, qz))
        ht = 1.0e-3
        hl = (W * math.sqrt(2.0)) / 2
        fx, fz = R + W / 2, -W / 2
        nr, nz = -1 / math.sqrt(2), 1 / math.sqrt(2)
        bx, bz = fx - nr * ht, fz - nz * ht
        hy_c = (R + W + ht) * tan_half * 1.05
        q = _quat_mul(_quat_axis((0, 0, 1), phi), _quat_axis((0, 1, 0), math.radians(-45.0)))
        seg.append('<geom name="chamf%d" type="box" size="%.6f %.6f %.6f" pos="%.7f %.7f %.7f" quat="%.9f %.9f %.9f %.9f" '
                   'rgba="0.16 0.16 0.18 1" class="hole"/>' % (i, hl, hy_c, ht, bx * c, bx * s, bz, q[0], q[1], q[2], q[3]))
        col_t = 2.4 * wall_t
        rcol = R + W + col_t / 2
        hy_k = (R + W + col_t) * tan_half * 1.02
        seg.append('<geom name="collar%d" type="box" size="%.6f %.6f 0.0005" pos="%.7f %.7f -0.0005" quat="%s" '
                   'rgba="0.55 0.55 0.53 1" class="hole"/>' % (i, col_t / 2, hy_k, rcol * c, rcol * s, qz))
    fh, inner = 0.06, R + W + wall_t * 0.6
    frame = []
    for (px, py, sx, sy) in [(0, (fh + inner) / 2, fh, (fh - inner) / 2), (0, -(fh + inner) / 2, fh, (fh - inner) / 2),
                             ((fh + inner) / 2, 0, (fh - inner) / 2, inner), (-(fh + inner) / 2, 0, (fh - inner) / 2, inner)]:
        frame.append('<geom type="box" size="%.5f %.5f 0.0125" pos="%.5f %.5f -0.0125" rgba="0.55 0.55 0.53 1" class="hole"/>'
                     % (sx, sy, px, py))
    s2 = 1 / math.sqrt(2)
    hover_z = L + 10e-3
    return """
<mujoco model="peghole">
  <compiler angle="radian"/>
  <option timestep="%(ts)g" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic" impratio="5"/>
  <statistic extent="0.3" center="0 0 0.02"/>
  <visual>
    <global offwidth="%(w)d" offheight="%(h)d"/>
    <map znear="0.01" zfar="60"/>
    <headlight ambient="0.45 0.45 0.45" diffuse="0.5 0.5 0.5" specular="0.05 0.05 0.05"/>
    <quality shadowsize="2048" numslices="128" numstacks="32" numquads="8" offsamples="%(offs)d"/>
  </visual>
  <default>
    <default class="hole">
      <geom contype="1" conaffinity="1" condim="3" friction="%(mu)g 0.005 0.0001" solref="0.002 1" solimp="0.95 0.99 0.0002"/>
    </default>
    <default class="peg">
      <geom contype="1" conaffinity="1" condim="3" friction="%(mu)g 0.005 0.0001" solref="0.002 1" solimp="0.95 0.99 0.0002"/>
    </default>
  </default>
  <worldbody>
    <light pos="0.1 -0.1 0.4" dir="-0.2 0.2 -1" diffuse="0.6 0.6 0.6" specular="0.1 0.1 0.1" castshadow="false"/>
    <light pos="-0.2 0.1 0.3" dir="0.5 -0.2 -1" diffuse="0.3 0.3 0.3" castshadow="false"/>
    <geom name="floor" type="plane" size="0.5 0.5 0.01" pos="0 0 -0.03" rgba="0.6 0.62 0.65 1" contype="0" conaffinity="0"/>
    <body name="plate" pos="0 0 0">
      <site name="hole_center" pos="0 0 0" size="0.0003" rgba="0 1 0 0"/>
      <site name="hole_bottom" pos="0 0 %(mH)g" size="0.0003" rgba="0 1 0 0"/>
      <geom name="hole_floor" type="box" size="%(fl)0.5f %(fl)0.5f 0.0025" pos="0 0 %(flz)0.5f" rgba="0.04 0.04 0.05 1" class="hole"/>
      %(segs)s
      %(frame)s
    </body>
    <camera name="side" pos="0.0 -0.050 0.022" xyaxes="1 0 0 0 0.38 0.925" fovy="30"/>
    <body name="carriage" pos="0 0 %(hover)g">
      <joint name="cx" type="slide" axis="1 0 0" damping="5"/>
      <joint name="cy" type="slide" axis="0 1 0" damping="5"/>
      <joint name="cz" type="slide" axis="0 0 1" damping="5"/>
      <geom type="box" size="0.012 0.012 0.004" pos="0 0 0.004" rgba="0.35 0.38 0.45 1" mass="0.5" contype="0" conaffinity="0"/>
      <camera name="wrist" pos="-0.06 0 0.02" xyaxes="0 -1 0 %(s2).9f 0 %(s2).9f" fovy="%(fovy)g"/>
      <site name="wrist_origin" pos="0 0 0" size="0.0003" rgba="0 0 1 0"/>
      <body name="wrist" pos="0 0 0">
        <joint name="wx" type="slide" axis="1 0 0" stiffness="%(kt)g" damping="2"/>
        <joint name="wy" type="slide" axis="0 1 0" stiffness="%(kt)g" damping="2"/>
        <joint name="wz" type="slide" axis="0 0 1" stiffness="%(kt)g" damping="2"/>
        <joint name="wrx" type="hinge" axis="1 0 0" pos="0 0 %(hz).6f" stiffness="%(kr)g" damping="0.01"/>
        <joint name="wry" type="hinge" axis="0 1 0" pos="0 0 %(hz).6f" stiffness="%(kr)g" damping="0.01"/>
        <joint name="wrz" type="hinge" axis="0 0 1" pos="0 0 %(hz).6f" stiffness="%(kr)g" damping="0.01"/>
        <geom name="peg" type="cylinder" size="%(r)g %(Lh)g" pos="0 0 %(mLh)g" rgba="0.72 0.33 0.07 1" mass="0.03" class="peg"/>
        <geom name="peg_cap" type="cylinder" size="0.007 0.003" pos="0 0 0.003" rgba="0.5 0.5 0.55 1" mass="0.01" contype="0" conaffinity="0"/>
        <site name="tip" pos="0 0 %(mL)g" size="0.0003" rgba="1 0 0 0"/>
        <site name="peg_top" pos="0 0 0" size="0.0003" rgba="1 0 0 0"/>
      </body>
    </body>
  </worldbody>
  <actuator>
    <position name="ax" joint="cx" kp="4000" kv="60"/>
    <position name="ay" joint="cy" kp="4000" kv="60"/>
    <position name="az" joint="cz" kp="4000" kv="60"/>
  </actuator>
</mujoco>
""" % {"ts": timestep, "w": img_w, "h": img_h, "offs": int(offsamples), "mu": mu, "mH": -H, "fl": R + wall_t,
       "flz": -H - 0.0025, "segs": "\n      ".join(seg), "frame": "\n      ".join(frame), "hover": hover_z,
       "s2": s2, "fovy": kp["fovy_deg"], "kt": kp["k_trans"], "kr": kp["k_rot"], "hz": hinge_z, "r": r, "Lh": L / 2,
       "mLh": -L / 2, "mL": -L}


# ----------------------------------------------------------------------------------------------------------------------
# mujoco 層(facade のみ)
def _mujoco():
    try:
        import mujoco
    except ImportError as exc:
        raise ImportError("pegsim: this function needs the optional dependency mujoco (pip install mujoco)") from exc
    return mujoco


def peg_scene_build(kp=None, lg: float | None = None) -> dict:
    """MuJoCo の場面を組む(mujoco が要る): :func:`peg_scene_mjcf` をコンパイルし、名前 → id の表と一緒に dict で返す。

    返り: ``model``・``data``・``kp``・``lg``、``ids``(peg / tip / top / hole_center / cam_wrist / cam_side / wall・chamf の集合 /
    floor / 関節の qpos 添字 ``qadr`` / アクチュエータ)。描画器は :func:`peg_wrist_render` が初回に作って場面に持たせる。
    **Raises** ``ImportError``: mujoco が無い。"""
    mujoco = _mujoco()
    kp = _kp(kp)
    m = mujoco.MjModel.from_xml_string(peg_scene_mjcf(kp, lg=lg, offsamples=4))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    g = mujoco.mj_name2id
    O = mujoco.mjtObj
    n_seg = kp["n_seg"]
    ids = {"peg": g(m, O.mjOBJ_GEOM, "peg"), "tip": g(m, O.mjOBJ_SITE, "tip"), "top": g(m, O.mjOBJ_SITE, "peg_top"),
           "hole_center": g(m, O.mjOBJ_SITE, "hole_center"), "cam_wrist": g(m, O.mjOBJ_CAMERA, "wrist"),
           "cam_side": g(m, O.mjOBJ_CAMERA, "side"), "floor": g(m, O.mjOBJ_GEOM, "hole_floor"),
           "wall": [g(m, O.mjOBJ_GEOM, "wall%d" % i) for i in range(n_seg)],
           "chamf": [g(m, O.mjOBJ_GEOM, "chamf%d" % i) for i in range(n_seg)]}
    ids["wall_set"], ids["chamf_set"] = set(ids["wall"]), set(ids["chamf"])
    jn = ["cx", "cy", "cz", "wx", "wy", "wz", "wrx", "wry", "wrz"]
    ids["qadr"] = {n: int(m.jnt_qposadr[g(m, O.mjOBJ_JOINT, n)]) for n in jn}
    ids["act"] = {n: g(m, O.mjOBJ_ACTUATOR, n) for n in ("ax", "ay", "az")}
    return {"model": m, "data": d, "ids": ids, "kp": kp, "lg": lg}


def _peg_axis(scene):
    d, ids = scene["data"], scene["ids"]
    tip = d.site_xpos[ids["tip"]].copy()
    top = d.site_xpos[ids["top"]].copy()
    a = top - tip
    return tip, a / np.linalg.norm(a)


def peg_set_pose(scene, tip_xyz, tilt: float, tilt_axis=(0, 1, 0)) -> np.ndarray:
    """ペグを運動学的に置く(mujoco が要る): 先端を ``tip_xyz`` に、軸を ``tilt_axis``(x か y)の回りに ``tilt`` [rad] 傾ける。
    傾きは手首のヒンジ、位置は搬送台のスライドで与え、mj_forward を呼ぶ。返り = 置いた後の先端位置。"""
    mujoco = _mujoco()
    m, d, ids = scene["model"], scene["data"], scene["ids"]
    d.qpos[:] = 0
    d.qvel[:] = 0
    ax = np.asarray(tilt_axis, np.float64)
    d.qpos[ids["qadr"]["wrx" if abs(ax[0]) > 0.5 else "wry"]] = float(tilt)
    mujoco.mj_forward(m, d)
    delta = np.asarray(tip_xyz, np.float64) - d.site_xpos[ids["tip"]]
    for k, n in enumerate(("cx", "cy", "cz")):
        d.qpos[ids["qadr"][n]] += delta[k]
    mujoco.mj_forward(m, d)
    return d.site_xpos[ids["tip"]].copy()


def peg_wrist_render(scene, cam: str = "wrist", depth: bool = True) -> dict:
    """手首(または側面)カメラで描く(mujoco が要る): RGB は 4×MSAA、depth は ``offsamples=0`` で別にコンパイルした同じ場面から。

    MSAA のまま depth を取ると、値は画素中心でなく**サンプル 0 の位置 (u − 0.125, v + 0.375) px** の深度になる(傾けた平面で実測、
    :func:`peg_depth_sample_offset`)。Fullseye の camera.py は画素中心を仮定するので別コンパイル。返り: ``rgb``(H, W, 3) uint8、
    ``depth``(H, W) float [m](depth=False なら None)、``K``、``R``・``t``(世界 → OpenCV カメラ)、``R_cam_to_world``。"""
    mujoco = _mujoco()
    m, d, kp = scene["model"], scene["data"], scene["kp"]
    W, H = kp["image_size"]
    if "_ren" not in scene:
        m_dep = mujoco.MjModel.from_xml_string(peg_scene_mjcf(kp, lg=scene.get("lg"), offsamples=0))
        ren_rgb = mujoco.Renderer(m, height=H, width=W)
        ren_dep = mujoco.Renderer(m_dep, height=H, width=W)
        ren_dep.enable_depth_rendering()
        scene["_ren"] = {"rgb": ren_rgb, "dep": ren_dep, "m_dep": m_dep, "d_dep": mujoco.MjData(m_dep)}
    ren = scene["_ren"]
    ren["rgb"].update_scene(d, camera=cam)
    rgb = ren["rgb"].render().copy()
    z = None
    if depth:
        ren["d_dep"].qpos[:] = d.qpos
        ren["d_dep"].qvel[:] = 0
        mujoco.mj_forward(ren["m_dep"], ren["d_dep"])
        ren["dep"].update_scene(ren["d_dep"], camera=cam)
        z = ren["dep"].render().copy()
    cid = scene["ids"]["cam_wrist" if cam == "wrist" else "cam_side"]
    K = render3d.intrinsics_from_fov(float(m.cam_fovy[cid]), W, H)
    ext = camera_world_to_cv(d.cam_xmat[cid].reshape(3, 3), d.cam_xpos[cid])
    return {"rgb": rgb, "depth": z, "K": K, "R": ext["R"], "t": ext["t"], "R_cam_to_world": ext["R_cam_to_world"]}


def peg_scene_close(scene) -> None:
    """描画器を閉じる(持っていなければ何もしない)。facade には出さない補助(``_`` でないのは __del__ 代わりに呼ぶため)。"""
    ren = scene.pop("_ren", None)
    if ren:
        ren["rgb"].close()
        ren["dep"].close()


def _peg_contacts(scene):
    mujoco = _mujoco()
    m, d, ids = scene["model"], scene["data"], scene["ids"]
    out = []
    f6 = np.zeros(6)
    for i in range(d.ncon):
        c = d.contact[i]
        g1, g2 = int(c.geom1), int(c.geom2)
        if ids["peg"] not in (g1, g2):
            continue
        other = g2 if g1 == ids["peg"] else g1
        kind = ("wall" if other in ids["wall_set"] else "chamfer" if other in ids["chamf_set"]
                else "floor" if other == ids["floor"] else "other")
        mujoco.mj_contactForce(m, d, i, f6)
        out.append({"kind": kind, "pos": np.array(c.pos), "fn": float(f6[0]), "dist": float(c.dist)})
    return out


def peg_contact_state(scene) -> dict:
    """接触計算(mj_contact)から Whitney の分類で状態を読む(mujoco が要る): 接触点を先端からの軸方向位置で先端側(端面から 1.5 mm
    以内 = 先端の縁が遠い側の壁 / 面取りの上)と口側(胴が最狭部の縁)に分ける。MuJoCo は 1 組の geom に複数の接触点を縁に沿って
    出すので、生の点数やユークリッド距離のクラスタでは数え過ぎる —— 軸方向で割ると数え過ぎない。

    返り: ``state``(:data:`CONTACT_STATES`)、``n``(0/1/2)、``contacts``(kind / pos / fn / dist の列)、``force``(法線力の和)、
    ``depth``(口の面からの先端深さ)、``tilt`` [rad]。"""
    kp = scene["kp"]
    cons = _peg_contacts(scene)
    tip, a = _peg_axis(scene)
    depth = -float(tip[2])
    tilt = math.atan2(math.hypot(float(a[0]), float(a[1])), abs(float(a[2])))
    force = float(sum(c["fn"] for c in cons))
    base = {"contacts": cons, "force": force, "depth": depth, "tilt": tilt}
    if any(c["kind"] == "floor" for c in cons):
        return dict(base, state="bottomed", n=0)
    tip_side = mouth_side = cham = 0
    for c in cons:
        if c["kind"] not in ("wall", "chamfer"):
            continue
        t_ax = float((c["pos"] - tip) @ a)
        if t_ax < 1.5e-3:
            tip_side += 1
            cham += int(c["kind"] == "chamfer")
        else:
            mouth_side += 1
    W = kp["chamfer"]
    if tip_side == 0 and mouth_side == 0:
        return dict(base, state="air" if depth < W else "inserting", n=0)
    if tip_side and not mouth_side:
        return dict(base, state="chamfer" if (cham and depth < W + 0.3e-3) else "one_point", n=1)
    if mouth_side and not tip_side:
        return dict(base, state="one_point", n=1)
    return dict(base, state="two_point", n=2)


def peg_two_point_depth_sim(kp, theta: float, scene=None) -> float:
    """二点接触が始まる深さ l₂ を**接触計算から**測る(mujoco が要る、:func:`two_point_depth` の第 2 実装): 傾き θ で先端が −x の壁に
    触れる横位置を mj_geomDistance の二分法で取り、+x の壁との隙間が 0 になる深さ(最狭部から)をもう 1 段の二分法で求める。

    穴の深さの中で二点接触が起きない(l₂ が穴より深い)なら ``ValueError``。試作: θ = 1.5〜6° で閉形式 (1′) と −0.07〜−0.02 mm。"""
    mujoco = _mujoco()
    kp = _kp(kp)
    sc = scene if scene is not None else peg_scene_build(kp)
    m, d, ids = sc["model"], sc["data"], sc["ids"]
    th = float(theta)
    peg, wall_px, wall_mx = ids["peg"], ids["wall"][0], ids["wall"][kp["n_seg"] // 2]
    fromto = np.zeros(6)
    W = kp["chamfer"]

    def dist(g1, g2):
        return float(mujoco.mj_geomDistance(m, d, g1, g2, 0.01, fromto))

    def mouth_gap(ell):
        lo, hi = -0.3e-3, 0.3e-3
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            peg_set_pose(sc, (mid, 0.0, -(ell + W)), th)
            if dist(peg, wall_mx) > 0:
                hi = mid
            else:
                lo = mid
        peg_set_pose(sc, (0.5 * (lo + hi), 0.0, -(ell + W)), th)
        return dist(peg, wall_px)

    lo, hi = 0.3e-3, kp["hole_depth"] - W
    g_lo, g_hi = mouth_gap(lo), mouth_gap(hi)
    if not (g_lo > 0 > g_hi):
        raise ValueError("peg_two_point_depth_sim: no two-point contact inside the hole depth at theta=%.4f rad "
                         "(gap %.3f mm at %.1f mm, %.3f mm at %.1f mm)" % (th, g_lo * 1e3, lo * 1e3, g_hi * 1e3, hi * 1e3))
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if mouth_gap(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def peg_depth_sample_offset(offsamples: int = 4, width: int = 320, height: int = 240) -> dict:
    """MuJoCo の深度バッファが**どの位置の深度か**を傾けた平面で測る(mujoco が要る): 45° に傾けた無限平面を描き、画素中心から
    (du, dv) ずらした光線が平面に当たる距離と比べ、残差が最小の (du, dv) を 1/8 px 刻みで返す。

    実測(640×480、試作): offsamples=4 → (du, dv) = (−0.125, +0.375)(サンプル 0 の位置)、offsamples=0 → (0, 0)(画素中心)。
    返り: ``du_px``・``dv_px``・``resid_mm``(最良の残差の平均)、``frontal_rel_err``(正対の平面の相対誤差)。"""
    mujoco = _mujoco()
    W, H = int(width), int(height)
    fovy, dist = 40.0, 0.092
    fy = (H / 2) / math.tan(math.radians(fovy) / 2)
    sn, cs = math.sin(math.radians(45)), math.cos(math.radians(45))
    xml = """<mujoco><statistic extent="0.3" center="0 0 0"/><visual><global offwidth="%d" offheight="%d"/>
    <map znear="0.01" zfar="60"/><quality offsamples="%d"/></visual><worldbody>
    <geom type="box" size="1 1 0.01" pos="0 0 -0.01" rgba="0.5 0.5 0.5 1"/>
    <camera name="f" pos="0 0 %g" xyaxes="1 0 0 0 1 0" fovy="%g"/>
    <camera name="t" pos="0 %g %g" xyaxes="1 0 0 0 %.9f %.9f" fovy="%g"/>
    <camera name="s" pos="%g 0 %g" xyaxes="%.9f 0 %.9f 0 1 0" fovy="%g"/>
    </worldbody></mujoco>""" % (W, H, int(offsamples), dist, fovy, -dist * sn, dist * cs, cs, sn, fovy,
                                -dist * sn, dist * cs, cs, sn, fovy)
    m2 = mujoco.MjModel.from_xml_string(xml)
    d2 = mujoco.MjData(m2)
    mujoco.mj_forward(m2, d2)
    ren = mujoco.Renderer(m2, height=H, width=W)
    ren.enable_depth_rendering()
    try:
        ren.update_scene(d2, camera="f")
        zf = ren.render().copy()
        v, u = np.mgrid[0:H, 0:W].astype(np.float64)
        out = {"frontal_rel_err": float((zf[H // 2, W // 2] - dist) / dist), "offsamples": int(offsamples)}
        for ci, name, key in ((1, "t", "dv_px"), (2, "s", "du_px")):
            ren.update_scene(d2, camera=name)
            zt = ren.render().copy()
            ext = camera_world_to_cv(d2.cam_xmat[ci].reshape(3, 3), d2.cam_xpos[ci])
            n_cam = ext["R"] @ np.array([0.0, 0.0, 1.0])
            best = None
            for s in np.arange(-0.5, 0.51, 0.125):
                du, dv = (0.0, s) if key == "dv_px" else (s, 0.0)
                rays = np.stack([(u + du - (W - 1) / 2) / fy, (v + dv - (H - 1) / 2) / fy, np.ones_like(u)], -1)
                za = (ext["t"] @ n_cam) / (rays @ n_cam)
                e = float(np.abs((zt - za)[H // 5:4 * H // 5, W // 5:4 * W // 5]).mean())
                if best is None or e < best[0]:
                    best = (e, float(s))
            out[key] = best[1]
            out["resid_mm_" + key[:2]] = best[0] * 1e3
    finally:
        ren.close()
    out["resid_mm"] = max(out["resid_mm_du"], out["resid_mm_dv"])
    return out


def peg_measure_overlay(rgb, truth_uv, est_uv, edge_uv=None, size: int = 12, zoom: int = 3, crop: int = 40) -> np.ndarray:
    """計測の重ね図(numpy だけ): 真値 = 緑の大きな十字、推定 = 赤の小さな十字、円当てはめに使った縁の点 = 黄の点(imagedraw)。
    右下に真値の重心まわり ``crop`` px 四方を ``zoom`` 倍にした拡大を貼る(副画素の一致を目で見るため)。

    ``rgb`` は (H, W, 3) uint8、``truth_uv``・``est_uv`` は (N, 2) の (u, v)。返りは同じ大きさの uint8。
    **Raises** ``ValueError``: rgb の形が違う、点が無い。"""
    rgb = np.asarray(rgb)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("peg_measure_overlay: rgb must be (H, W, 3)")
    if np.asarray(truth_uv).size == 0 or np.asarray(est_uv).size == 0:
        raise ValueError("peg_measure_overlay: truth_uv and est_uv must hold at least one point")
    hole_edge_uv = edge_uv
    img = rgb.astype(np.float64) / 255.0
    if hole_edge_uv is not None and len(hole_edge_uv):
        img = imagedraw.draw_markers(img, hole_edge_uv, color=(1.0, 1.0, 0.0), size=0, shape="dot")
    truth_uv = np.asarray(truth_uv, np.float64).reshape(-1, 2)
    est_uv = np.asarray(est_uv, np.float64).reshape(-1, 2)
    img = imagedraw.draw_markers(img, truth_uv, color=(0.0, 1.0, 0.0), size=size, shape="cross", width=1)
    img = imagedraw.draw_markers(img, est_uv, color=(1.0, 0.0, 0.0), size=size // 2, shape="cross", width=1)
    out = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    H, W = out.shape[:2]
    cx, cy = truth_uv.mean(axis=0)
    x0 = int(np.clip(cx - crop, 0, W - 2 * crop))
    y0 = int(np.clip(cy - crop, 0, H - 2 * crop))
    patch = out[y0:y0 + 2 * crop, x0:x0 + 2 * crop]
    patch = np.repeat(np.repeat(patch, zoom, axis=0), zoom, axis=1)
    ph, pw = min(patch.shape[0], H // 2), min(patch.shape[1], W // 2)
    patch = patch[:ph, :pw]
    out[H - ph:, W - pw:] = patch
    out[H - ph:H - ph + 2, W - pw:] = (255, 255, 255)
    out[H - ph:, W - pw:W - pw + 2] = (255, 255, 255)
    return out


def peg_insertion_run(kp=None, eps_mm=(2.0, 1.0), tilt_deg: float = 2.0, correct: bool = True, gain: float = 0.5,
                      lg: float | None = None, record: bool = False, frame_every: float = 0.02, servo_iters: int = 8,
                      v_fast: float = 12e-3, v_slow: float = 3e-3, f_slow: float = 2.5, f_max: float = 12.0,
                      success_depth: float = 15e-3, t_max: float = 7.0) -> dict:
    """ルールベースの挿入を 1 走行(mujoco が要る、学習なし): (i) 先端を口の 10 mm 上、横ずれ ε [mm]・傾き θ [deg](把持の誤差 =
    手首ヒンジのばねの静止角)で構える、(ii) ``correct`` なら手首 RGB-D から (dx, dy) を測って(穴の円は治具の図面の半径 R + W で当てる)搬送台を −gain·(dx, dy) 動かす
    (|d| < 0.05 mm か ``servo_iters`` 回まで)、(iii) ``v_fast`` で下げる(面取りが柔らかい手首を横へ押す)、(iv) 法線力の和が
    ``f_slow`` を超えたら ``v_slow``、``f_max`` を超えたら止まる(かじり候補)、(v) 先端深さ ≥ ``success_depth`` で成功、
    ``t_max`` [s](シミュ時間)で timeout。

    各 10 ms ごとに接触状態(:func:`peg_contact_state`)と幾何の予測(:func:`contact_state_predict`)を記録する。
    返り: ``status``("success" / "timeout" / "bottomed")、``success``、``final_depth_mm``、``final_tilt_deg``、``max_force_N``、
    ``servo``(反復ごとの測定値と真値)、``rec``(t / depth / tilt / state / n_con / n_pred / force / tip_xy)、``steps``、``sim_time``、
    ``wall_s``、``frames_side``(record のとき側面カメラのコマ)、``overlays``(サーボ反復ごとの重ね図)。"""
    import time as _time
    mujoco = _mujoco()
    t_wall = _time.perf_counter()
    kp = _kp(kp)
    sc = peg_scene_build(kp, lg=lg)
    m, d, ids = sc["model"], sc["data"], sc["ids"]
    dt = float(m.opt.timestep)
    m.qpos_spring[ids["qadr"]["wry"]] = math.radians(tilt_deg)
    d.qpos[ids["qadr"]["wry"]] = math.radians(tilt_deg)
    d.ctrl[:] = [0.0, 0.0, 0.0]
    mujoco.mj_forward(m, d)
    frames_side, overlays, servo_log = [], [], []
    rec = {"t": [], "depth": [], "tilt": [], "state": [], "n_con": [], "n_pred": [], "where_pred": [], "force": [], "tip_xy": []}
    nsteps = [0]
    last_frame = [-1.0]
    need_render = correct or record

    def settle(steps):
        for _ in range(int(steps)):
            mujoco.mj_step(m, d)
            nsteps[0] += 1
            if record and d.time - last_frame[0] >= frame_every:
                last_frame[0] = d.time
                frames_side.append(peg_wrist_render(sc, "side", depth=False)["rgb"])

    def sample():
        st = peg_contact_state(sc)
        tip, a = _peg_axis(sc)
        pred = contact_state_predict(kp, tip, a)
        rec["t"].append(float(d.time))
        rec["depth"].append(st["depth"])
        rec["tilt"].append(math.degrees(st["tilt"]))
        rec["state"].append(st["state"])
        rec["n_con"].append(st["n"])
        rec["n_pred"].append(pred["n"])
        rec["where_pred"].append(pred["where"])
        rec["force"].append(st["force"])
        rec["tip_xy"].append(tip[:2].copy())
        return st

    settle(0.4 / dt)
    for _ in range(3):                                       # 先端(手首原点でなく)を指定の横ずれに置く
        tip = d.site_xpos[ids["tip"]]
        d.ctrl[0] += eps_mm[0] * 1e-3 - tip[0]
        d.ctrl[1] += eps_mm[1] * 1e-3 - tip[1]
        settle(0.3 / dt)
    tip0 = d.site_xpos[ids["tip"]].copy()
    if correct:
        for it in range(int(servo_iters)):
            img = peg_wrist_render(sc, "wrist", depth=True)
            try:
                res = peg_offset_from_rgbd(img["rgb"], img["depth"], img["K"], img["R_cam_to_world"], r_peg=kp["r"],
                                           hole_radius=kp["R"] + kp["chamfer"])
            except (RuntimeError, ValueError) as exc:
                servo_log.append({"iter": it, "error": repr(exc)})
                break
            true_d = d.site_xpos[ids["tip"]][:2] - d.site_xpos[ids["hole_center"]][:2]
            servo_log.append({"iter": it, "dx_mm": res["dx"] * 1e3, "dy_mm": res["dy"] * 1e3,
                              "true_dx_mm": float(true_d[0]) * 1e3, "true_dy_mm": float(true_d[1]) * 1e3})
            if record:
                truth = np.vstack([d.site_xpos[ids["tip"]], d.site_xpos[ids["hole_center"]]])
                uv_true, _ = camera.project_points(truth, img["K"], img["R"], img["t"])
                overlays.append(peg_measure_overlay(img["rgb"], uv_true, np.vstack([res["tip"]["uv"], res["hole"]["uv"]]),
                                                    res["hole"]["edge_uv"]))
            if math.hypot(res["dx"], res["dy"]) < 0.05e-3:
                break
            d.ctrl[0] -= gain * res["dx"]
            d.ctrl[1] -= gain * res["dy"]
            settle(0.3 / dt)
    tip_after = d.site_xpos[ids["tip"]].copy()
    t0 = d.time
    status = "timeout"
    while d.time - t0 < t_max:
        st = sample()
        F, depth = st["force"], st["depth"]
        if depth >= success_depth:
            status = "success"
            break
        if st["state"] == "bottomed":
            status = "bottomed"
            break
        v = v_slow if F > f_slow else v_fast
        if F <= f_max:
            d.ctrl[2] -= v * dt * 20
        settle(20)                                           # 制御は 10 ms ごと
    sample()
    if need_render:
        peg_scene_close(sc)
    return {"status": status, "success": status == "success", "eps_mm": [float(e) for e in eps_mm], "tilt_deg": float(tilt_deg),
            "correct": bool(correct), "lg": lg, "tip0_mm": (tip0[:2] * 1e3).tolist(),
            "tip_after_servo_mm": (tip_after[:2] * 1e3).tolist(), "final_depth_mm": rec["depth"][-1] * 1e3,
            "final_tilt_deg": rec["tilt"][-1], "max_force_N": float(max(rec["force"]) if rec["force"] else 0.0),
            "servo": servo_log, "rec": rec, "steps": nsteps[0], "sim_time": float(d.time),
            "wall_s": _time.perf_counter() - t_wall, "frames_side": frames_side, "overlays": overlays}


def peg_insertion_grid(kp=None, eps_mm_list=(0.0, 1.0, 2.0, 3.0), tilt_deg_list=(0.0, 1.0, 2.0, 3.0),
                       correct_flags=(False, True), direction_deg: float = 30.0, lg: float | None = None, log=None) -> dict:
    """成功率の格子(mujoco が要る): 初期横ずれ ε₀ × 傾き θ₀ × {補正なし, あり} で :func:`peg_insertion_run` を回し、
    :func:`insertion_grid_summary` で集計する。ずれの向きは軸に揃えない(``direction_deg``、既定 30°)。

    返り: ``rows``(走行ごとの status / depth / 力 / 見た状態 / 幾何予測との一致率)、``summary``。試作(4 × 4 × 2 = 32 走行、20 s):
    補正なしは ε₀ ≤ 1 mm で成功・2 mm 以上は timeout(面取りの許容 1.2 mm)、補正ありは 16 / 16。"""
    rows = []
    cd, sd = math.cos(math.radians(direction_deg)), math.sin(math.radians(direction_deg))
    for corr in correct_flags:
        for eps in eps_mm_list:
            for tilt in tilt_deg_list:
                r = peg_insertion_run(kp, eps_mm=(eps * cd, eps * sd), tilt_deg=tilt, correct=corr, lg=lg)
                nc, npd = np.asarray(r["rec"]["n_con"]), np.asarray(r["rec"]["n_pred"])
                rows.append({"eps_mm": float(eps), "tilt_deg": float(tilt), "correct": bool(corr), "status": r["status"],
                             "success": r["success"], "final_depth_mm": r["final_depth_mm"], "max_force_N": r["max_force_N"],
                             "steps": r["steps"], "wall_s": r["wall_s"], "sim_time_s": r["sim_time"],
                             "states_seen": sorted(set(r["rec"]["state"])), "n_servo": len(r["servo"]),
                             "agree_raw": float(np.mean(nc == npd)) if len(nc) else float("nan"),
                             "agree_within1": float(np.mean(np.abs(nc - npd) <= 1)) if len(nc) else float("nan")})
                if log:
                    log("eps=%.1f tilt=%.1f correct=%s -> %s depth=%.2f mm Fmax=%.1f N wall=%.1f s"
                        % (eps, tilt, corr, r["status"], r["final_depth_mm"], r["max_force_N"], r["wall_s"]))
    return {"rows": rows, "summary": insertion_grid_summary(rows)}
