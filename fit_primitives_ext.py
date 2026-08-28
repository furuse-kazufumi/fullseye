# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""プリミティブ適合の拡張: 円錐 / トーラス / 楕円体(cone / torus / ellipsoid)。

``ransac_fit`` は平面・球・直線・円筒、``superquadric`` は把持向けの体積プリミティブを
当てる。本モジュールはそこに **曲率が場所で変わる 3 種のプリミティブ** を足す:

  * :func:`fit_cone` … 頂点 ``apex`` から半角 ``half_angle`` で広がる無限円錐。
    漏斗・ノズル・旋盤の面取り・砂山などの計測に。
  * :func:`fit_torus` … 中心 ``center`` ・軸 ``axis`` 周りに主半径 ``R`` の輪、
    管半径 ``r`` の管を持つトーラス。O リング・配管の曲がり・ドーナツ状部品に。
  * :func:`fit_ellipsoid` … 任意姿勢の 3 軸楕円体(``center`` ・主軸 ``axes`` ・
    半径 ``radii``)。細胞・小惑星・慣性楕円体・扁平な粒などに。

**既存 op との違い(固有価値, honest)**:
  * ``ransac_sphere`` は等方球(半径 1 個)のみ。3 軸が異なる楕円体は当てられない。
  * ``superquadric.fit_superquadric`` は ``eps=(1,1)`` で楕円体を*近似*できるが、
    Gross-Boult の半径距離近似を ``least_squares`` で回す **反復・局所最適**器で、
    初期姿勢に依存する。本 :func:`fit_ellipsoid` は二次形式 ``x^T A x + b·x + c = 0`` の
    **代数フィット**(Li & Griffiths 2004 の楕円体特化・一般化固有値)で、初期値不要・
    決定論・大域解。用途が違う(代数 1 発 vs 反復体積当てはめ)。
  * 円錐・トーラスは既存のどのカテゴリにも無い(新規)。

手法:
  * **円錐 / トーラス** … 対称軸を PCA(共分散の「仲間外れ」固有ベクトル= 2 つの近い
    固有値の残り 1 つ)で初期化し、点-表面距離を ``scipy.optimize.least_squares`` で最小化。
    円錐の点-面距離は子午面での「点-母線」直交距離 ``a·sinα − ρ·cosα``、トーラスは
    「点-管中心円距離 − r」= ``sqrt((ρ−R)² + a²) − r`` で、いずれも真の直交距離(頂点近傍を
    除き)なので残差 RMS がそのまま幾何的な当てはめ精度になる。
  * **楕円体** … 一般二次曲面の代数フィット。設計行列 ``D`` の散布 ``S=DᵀD`` を
    二次項 6 + 一次/定数 4 に分割し、楕円体を保証する拘束 ``4J − I² = 1``(``I=a+b+c``,
    ``J=ab+bc+ca−f²−g²−h²``)の下で一般化固有問題 ``Sr v = λ C v`` を解く
    (``scipy.linalg.eig``)。拘束を満たす(``vᵀCv>0``)固有ベクトルのうち残差最小の
    実解を選び、正定値性(= 実在する楕円体)を検査してから中心・主軸・半径へ復元する。
    数値安定化のため点群を重心・RMS 半径で無次元化してから解き、パラメータを戻す。

限界(honest):
  * 円錐 / トーラスの ``least_squares`` は局所最適器。PCA 初期化が外れる病的配置
    (点が軸方向に薄い/角度被覆が半周未満)では収束しないことがある。半角 ~0 の円錐は
    円柱に縮退するので ``fit_cone`` は fail-closed(``ValueError``)。
  * 楕円体の代数フィットは外れ値に無防備(全点最小二乗)。外れ値があれば ``ransac_fit`` で
    inlier を選別してから渡す。点配置が縮退(平面状・軸不足)で正定値解が無ければ
    fail-closed(``ValueError``)。半周未満のような部分被覆では代数フィットが双曲面側へ
    落ちて解無しになりうる。

Reference (public):
  Q. Li, J. G. Griffiths, "Least Squares Ellipsoid Specific Fitting",
  Geometric Modeling and Processing (GMP), 2004.
"""
from __future__ import annotations

import numpy as np
from scipy import linalg as sla
from scipy.optimize import least_squares

__all__ = ["fit_cone", "fit_torus", "fit_ellipsoid"]


# ═══════════════════════════════════════════════════════════════════════════
# 共通ヘルパ
# ═══════════════════════════════════════════════════════════════════════════
def _as_points(points, k: int, name: str) -> np.ndarray:
    """入力を (N,3) float64 へ検証。fail-closed(形状不正/非有限/点数不足は ValueError)。"""
    P = np.asarray(points, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"{name}: points は (N,3) 形状が必要(得た shape={P.shape})")
    if not np.all(np.isfinite(P)):
        raise ValueError(f"{name}: points に非有限値が含まれる")
    if len(P) < k:
        raise ValueError(f"{name}: 最低 {k} 点必要(得た N={len(P)})")
    return P


def _unit(v: np.ndarray) -> np.ndarray:
    """単位ベクトル化(ゼロ長は 1e-12 でクリップ)。"""
    v = np.asarray(v, dtype=np.float64)
    n = float(np.linalg.norm(v))
    return v / (n if n > 1e-12 else 1e-12)


def _symmetry_axis(Q: np.ndarray) -> np.ndarray:
    """中心化点群 ``Q`` の対称軸を PCA で初期推定(「仲間外れ」固有ベクトル)。

    円錐・トーラスは軸周りに回転対称なので、軸に直交する 2 主軸の分散は(ほぼ)等しく、
    軸方向の固有値だけが異なる。3 固有値のうち **互いに近い 2 つ以外** の固有ベクトルを
    軸とする(トーラスなら軸=最小分散、細長い円錐なら軸=最大分散、平たい円錐なら軸=最小と
    向きが変わるため、大小固定でなく「近い 2 つの残り」で選ぶのが頑健)。
    """
    evals, evecs = np.linalg.eigh(Q.T @ Q)     # 昇順 evals[0]<=evals[1]<=evals[2]
    d01 = evals[1] - evals[0]
    d12 = evals[2] - evals[1]
    axis_idx = 2 if d01 <= d12 else 0          # 近い方のペアの残り = 軸
    return _unit(evecs[:, axis_idx])


def _axial_radial(P: np.ndarray, v: np.ndarray, d: np.ndarray):
    """点群を軸 ``(v, d)`` に対する (軸成分 a, 半径 ρ) へ分解。d は単位前提。"""
    w = P - v
    a = w @ d
    perp = w - np.outer(a, d)
    rho = np.linalg.norm(perp, axis=1)
    return a, rho


# ═══════════════════════════════════════════════════════════════════════════
# 1. 円錐(cone)
# ═══════════════════════════════════════════════════════════════════════════
def fit_cone(points) -> dict:
    """点群に無限円錐を当てはめ ``{apex, axis, half_angle, residual}`` を返す。

    子午面での点-母線直交距離 ``a·sinα − ρ·cosα``(``a``=軸成分, ``ρ``=半径,
    ``α``=半角)を ``scipy.optimize.least_squares`` で最小化する。初期値は PCA 軸 +
    半径 ρ の軸成分 t に対する線形回帰(``ρ = m·t + b`` の傾き m=tanα, 切片ゼロ点=頂点)。
    軸の向きは「頂点から離れるほど ρ が増える(+方向に開く)」に正規化する。

    Args:
        points: (N,3) 点群(最低 6 点)。

    Returns:
        dict: ``{"apex": (3,), "axis": (3,) 単位軸(開く向き), "half_angle": float [rad],
        "residual": float 点-面距離の RMS}``。

    Raises:
        ValueError: 形状不正/点数不足/半角 ~0(円柱へ縮退)など fail-closed。
    """
    P = _as_points(points, 6, "fit_cone")
    centroid = P.mean(0)
    Q = P - centroid
    diag = float(np.linalg.norm(P.max(0) - P.min(0))) + 1e-12

    # --- 初期化: PCA 軸 + 半径の線形回帰 ---
    d0 = _symmetry_axis(Q)
    t = Q @ d0
    rho = np.linalg.norm(Q - np.outer(t, d0), axis=1)
    m, b = np.polyfit(t, rho, 1)               # ρ ≈ m t + b
    if m < 0:                                   # 開く向きが逆 → 軸反転して再フィット
        d0 = -d0
        t = -t
        m, b = np.polyfit(t, rho, 1)
    if abs(m) < 1e-6:
        raise ValueError("fit_cone: 円錐の広がりが検出できない(半角 ~0、円柱に縮退)")
    t_apex = -b / m
    apex0 = centroid + t_apex * d0
    alpha0 = float(np.clip(np.arctan(abs(m)), 1e-3, np.pi / 2 - 1e-3))

    # --- least_squares 精密化(軸は 3 ベクトルを内部正規化 = 極特異点なし)---
    def resid(p):
        v = p[0:3]
        d = _unit(p[3:6])
        alpha = p[6]
        a, r = _axial_radial(P, v, d)
        return a * np.sin(alpha) - r * np.cos(alpha)

    p0 = np.concatenate([apex0, d0, [alpha0]])
    lb = np.array([-np.inf] * 6 + [1e-3])
    ub = np.array([np.inf] * 6 + [np.pi / 2 - 1e-3])
    sol = least_squares(resid, p0, bounds=(lb, ub), method="trf",
                        xtol=1e-12, ftol=1e-12, max_nfev=8000)

    apex = np.asarray(sol.x[0:3], dtype=np.float64)
    axis = _unit(sol.x[3:6])
    half_angle = float(sol.x[6])

    # 開く向きの正規化(点は +axis 側の nappe にあるはず): 平均軸成分が負なら向き付けを直す。
    a, _ = _axial_radial(P, apex, axis)
    if float(np.mean(a)) < 0.0:
        axis = -axis                            # 幾何は同一(頂点は不変、向きだけ反転)

    r = resid(sol.x)
    residual = float(np.sqrt(np.mean(r ** 2)))
    # スケール非依存の妥当性: 残差が形状スケールに対して大きすぎたら honest に開示(例外にはしない)
    return {"apex": apex, "axis": axis, "half_angle": half_angle,
            "residual": residual, "scale": diag}


# ═══════════════════════════════════════════════════════════════════════════
# 2. トーラス(torus)
# ═══════════════════════════════════════════════════════════════════════════
def fit_torus(points) -> dict:
    """点群にトーラスを当てはめ ``{center, axis, R, r, residual}`` を返す。

    点-トーラス距離 ``sqrt((ρ−R)² + a²) − r``(``a``=軸成分, ``ρ``=軸からの半径,
    ``R``=主半径, ``r``=管半径)を ``scipy.optimize.least_squares`` で最小化する。
    初期値は PCA 軸(仲間外れ固有ベクトル)+ ``R0=mean(ρ)``・``r0=mean(管中心円までの距離)``。

    Args:
        points: (N,3) 点群(最低 7 点)。

    Returns:
        dict: ``{"center": (3,), "axis": (3,) 単位軸, "R": float 主半径,
        "r": float 管半径, "residual": float 点-面距離の RMS}``。

    Raises:
        ValueError: 形状不正/点数不足 fail-closed。
    """
    P = _as_points(points, 7, "fit_torus")
    center0 = P.mean(0)
    Q = P - center0
    diag = float(np.linalg.norm(P.max(0) - P.min(0))) + 1e-12

    # --- 初期化: PCA 軸 + 主/管半径のモーメント推定 ---
    n0 = _symmetry_axis(Q)
    a, rho = _axial_radial(P, center0, n0)
    R0 = float(np.mean(rho))
    r0 = float(np.mean(np.sqrt((rho - R0) ** 2 + a ** 2)))
    R0 = max(R0, 1e-6 * diag)
    r0 = max(r0, 1e-6 * diag)

    def resid(p):
        c = p[0:3]
        n = _unit(p[3:6])
        R = p[6]
        r = p[7]
        aa, rr = _axial_radial(P, c, n)
        return np.sqrt((rr - R) ** 2 + aa ** 2) - r

    p0 = np.concatenate([center0, n0, [R0, r0]])
    lb = np.array([-np.inf] * 6 + [1e-9, 1e-9])
    ub = np.array([np.inf] * 8)
    sol = least_squares(resid, p0, bounds=(lb, ub), method="trf",
                        xtol=1e-12, ftol=1e-12, max_nfev=8000)

    center = np.asarray(sol.x[0:3], dtype=np.float64)
    axis = _unit(sol.x[3:6])
    R = float(sol.x[6])
    r = float(sol.x[7])
    residual = float(np.sqrt(np.mean(resid(sol.x) ** 2)))
    return {"center": center, "axis": axis, "R": R, "r": r,
            "residual": residual, "scale": diag}


# ═══════════════════════════════════════════════════════════════════════════
# 3. 楕円体(ellipsoid)— 代数フィット(Li & Griffiths 2004)
# ═══════════════════════════════════════════════════════════════════════════
# 楕円体拘束 4J − I² = 1 の二次形式行列 C(6x6, k=4)。v1=(a,b,c,f,g,h) に対し
# v1ᵀ C v1 = 4J − I²(> 0 が楕円体条件)。
_ELLIPSOID_C = np.array([
    [-1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
    [1.0, -1.0, 1.0, 0.0, 0.0, 0.0],
    [1.0, 1.0, -1.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, -4.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, -4.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 0.0, -4.0],
], dtype=np.float64)


def _ellipsoid_taubin_distance(P, center, axes, radii):
    """点-楕円体の 1 次(Taubin)近似直交距離 ``|g| / ||∇g||``。

    ``g(x) = Σ (u_i/radii_i)² − 1``(``u = axesᵀ(x − center)``、canonical 座標)。
    表面近傍で真の直交距離に 1 次まで一致する。半径方向の素朴距離より曲面近傍で正確。
    """
    u = (P - center) @ axes                    # (N,3) canonical 座標
    inv_r2 = 1.0 / (radii ** 2)
    g = (u ** 2) @ inv_r2 - 1.0                 # (N,)
    grad_u = 2.0 * u * inv_r2                   # ∂g/∂u
    grad_x = grad_u @ axes.T                    # world 勾配(axes は回転)
    gn = np.linalg.norm(grad_x, axis=1)
    return np.abs(g) / np.maximum(gn, 1e-12)


def _ellipsoid_from_coeffs(v, centroid, scale):
    """代数係数 v(無次元座標)→ ``{center, axes, radii}``(world 座標)。非楕円体は None。

    v = (a,b,c,f,g,h,p,q,r,d) で ``F = xᵀA₃x + 2·(p,q,r)·x + d``。中心・正定値性を検査し、
    正定値(= 実在する楕円体)なら固有分解で主軸と半径へ復元、無次元化を戻す。
    """
    a, b, c, f, g, h, p, q, r, d = v
    A3 = np.array([[a, h, g], [h, b, f], [g, f, c]], dtype=np.float64)
    lin = np.array([p, q, r], dtype=np.float64)
    # 中心: ∇F = 0 → 2 A3 x + 2 lin = 0
    try:
        center_n = np.linalg.solve(A3, -lin)
    except np.linalg.LinAlgError:
        return None
    k_const = float(lin @ center_n + d)         # F(center)
    if abs(k_const) < 1e-15:
        return None
    A_norm = A3 / (-k_const)                     # (x−c)ᵀ A_norm (x−c) = 1
    A_norm = 0.5 * (A_norm + A_norm.T)           # 対称化(数値誤差除去)
    evals, evecs = np.linalg.eigh(A_norm)
    if np.any(evals <= 0) or not np.all(np.isfinite(evals)):
        return None                              # 正定値でない → 楕円体でない(双曲面等)
    radii_n = 1.0 / np.sqrt(evals)               # 無次元半径
    # 無次元化を戻す(一様スケール + 平行移動: 主軸=回転は不変)
    center = centroid + scale * center_n
    radii = scale * radii_n
    axes = evecs
    # 半径降順に整列(決定論)+ 主軸の符号を正準化(最大絶対成分を正に)
    order = np.argsort(radii)[::-1]
    radii = radii[order]
    axes = axes[:, order]
    for j in range(3):
        if axes[np.argmax(np.abs(axes[:, j])), j] < 0:
            axes[:, j] = -axes[:, j]
    return {"center": center, "axes": axes, "radii": radii}


def fit_ellipsoid(points) -> dict:
    """点群に任意姿勢の 3 軸楕円体を代数フィットし ``{center, axes, radii, residual}`` を返す。

    一般二次曲面 ``xᵀA x + b·x + c = 0`` を、楕円体を保証する拘束 ``4J − I² = 1`` の下で
    一般化固有問題 ``Sr v1 = λ C v1``(``scipy.linalg.eig``)として解く(Li & Griffiths 2004)。
    拘束を満たす(``v1ᵀ C v1 > 0``)実固有ベクトルのうち、正定値(実在する楕円体)へ復元でき
    残差 RMS が最小のものを採用する。初期値不要・決定論・大域解。数値安定化のため点群を
    重心と RMS 半径で無次元化してから解き、パラメータを world 座標へ戻す。

    Args:
        points: (N,3) 点群(最低 10 点)。外れ値には無防備(必要なら事前に inlier 選別)。

    Returns:
        dict: ``{"center": (3,), "axes": (3,3) 列=主軸(半径降順), "radii": (3,) 半径(降順),
        "residual": float Taubin 近似の点-面距離 RMS}``。

    Raises:
        ValueError: 形状不正/点数不足/正定値な楕円体解が得られない(平面状の退化・
            非楕円面・被覆不足)など fail-closed。
    """
    P = _as_points(points, 10, "fit_ellipsoid")
    centroid = P.mean(0)
    d = P - centroid
    scale = float(np.sqrt(np.mean(np.sum(d ** 2, axis=1))))   # RMS 半径
    if scale < 1e-12:
        raise ValueError("fit_ellipsoid: 点が 1 点に縮退している(スケール 0)")
    Pn = d / scale
    x, y, z = Pn[:, 0], Pn[:, 1], Pn[:, 2]
    # 設計行列 D(列 = χ = [x²,y²,z²,2yz,2xz,2xy,2x,2y,2z,1])
    D = np.column_stack([x * x, y * y, z * z, 2 * y * z, 2 * x * z, 2 * x * y,
                         2 * x, 2 * y, 2 * z, np.ones_like(x)])
    S = D.T @ D
    S11 = S[0:6, 0:6]
    S12 = S[0:6, 6:10]
    S22 = S[6:10, 6:10]
    try:
        S22inv = np.linalg.inv(S22)
    except np.linalg.LinAlgError:
        S22inv = np.linalg.pinv(S22)
    Sr = S11 - S12 @ S22inv @ S12.T             # 一次/定数を消去した縮約 6x6

    try:
        evals, evecs = sla.eig(Sr, _ELLIPSOID_C)
    except (np.linalg.LinAlgError, ValueError) as exc:
        raise ValueError(f"fit_ellipsoid: 一般化固有問題が解けない({exc})")

    best = None
    best_rms = np.inf
    for i in range(evecs.shape[1]):
        v1 = np.real(evecs[:, i])
        if not np.all(np.isfinite(v1)):
            continue
        con = float(v1 @ _ELLIPSOID_C @ v1)     # v1ᵀ C v1(> 0 が楕円体条件)
        if con <= 1e-12:
            continue
        v1 = v1 / np.sqrt(con)                   # 拘束 v1ᵀ C v1 = 1 へ正規化
        v2 = -S22inv @ (S12.T @ v1)
        v = np.concatenate([v1, v2])
        params = _ellipsoid_from_coeffs(v, centroid, scale)
        if params is None:
            continue
        rms = float(np.sqrt(np.mean(
            _ellipsoid_taubin_distance(P, params["center"], params["axes"],
                                       params["radii"]) ** 2)))
        if rms < best_rms:
            best, best_rms = params, rms

    if best is None:
        raise ValueError(
            "fit_ellipsoid: 正定値な楕円体解が得られない(平面状の退化・非楕円面・"
            "角度被覆不足)")
    best["residual"] = best_rms
    return best
