# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""hull3d — 最小包含球(minimum enclosing sphere)。

点群 (N,3) を「囲む」プリミティブのうち、**fullseye にまだ存在しなかった 1 つ**だけを足す
モジュール。検査・衝突判定・把持計画・粗い占有見積りで最初に欲しくなる「その物体はどこに・
どれだけの大きさで存在するか」のうち、他の外接プリミティブは既に公開 API で揃っているため、
ここではそれらを**再実装せず**、欠けていた最小包含球のみを提供する。

正直な新規性の開示(既存公開 API との関係)
--------------------------------------------------
点群の外接プリミティブは、その多くが既に fullseye の公開 API として存在する。本モジュールは
それらを置き換えず、**唯一 repo に無かった最小包含球だけ**を追加する:

- **凸包**       — 既存: ``fs.convex_hull``(実体 ``meshrepair.convex_hull``)。同じ
  ``scipy.spatial.ConvexHull``(Qhull)ラッパで、さらに各三角面を重心から外向きに巻き直す
  **上位互換**(inertia_tensor / MuJoCo convex collider にそのまま渡せる)。→ そちらを使う。
- **AABB**       — 既存: ``fs.aabb``(実体 ``pcseg.aabb``)。軸整列の min/max。→ そちらを使う。
- **OBB**        — 既存: ``fs.obb``(実体 ``pcseg.obb``)。共分散 PCA による向き付き箱
  (``axes`` は列ベクトル・``extents`` は半幅の規約)。→ そちらを使う。
- **球フィット** — 既存だが**別問題**: ``match3d.fit_sphere_3d``(点が球**面上**にある前提の
  最小二乗代数フィット)/ ``ransac_sphere`` / ``match3d.hough_sphere_3d``(球の検出)。
  いずれも「全点を内包する最小の球」ではない。

したがって本モジュールが実際に足す新規 op は ``min_enclosing_sphere`` の 1 本だった。
2026-11-15 に、囲むのではなく**2 つの凸包のあいだ**を測る ``convex_hull_gap`` を足した(下の一覧)。
「全点を含む最小の球」は最小二乗フィットや検出とは異なる最適化問題(最小包含球, MEB)で、
把持前のクリアランス確保・衝突球・視錐台カリング等で「取りこぼしゼロで最小の余白」を欲しい
場面に対応する。凸包 / AABB / OBB が要るときは上記の既存公開 API を呼ぶこと。

- ``min_enclosing_sphere`` — 全点を含む(近似)最小包含球(Ritter 初期化 + Bădoiu–Clarkson
  精緻化)。重心中心の素朴球より中心を寄せて半径を詰める。全点内包を保証(構成上、各点を
  含むよう最後に半径を確定する安全側)。
- ``convex_hull_gap`` — 2 つの頂点集合の凸包どうしの隙間(Wolfe の最小ノルム点、有限回で厳密)を、
  実際に作った最も近い点の組(上限)と分離の帯の幅(下限)の保証つきで返す。独立な線形計画(HiGHS)で
  離れ方を別に決め、食い違えば例外。頂点どうしの距離では重なりを否定できない(十字の棒)。

numpy in / numpy(+dict) out。``min_enclosing_sphere`` は numpy だけで動く。``convex_hull_gap`` の
既定の検算(線形計画)は scipy を使う(``check="none"`` なら numpy だけ)。入力検証は fail-closed
(形状不正・非有限・点数不足は例外)。

Reference (public): J. Ritter, "An efficient bounding sphere", Graphics Gems (1990);
M. Bădoiu, K. L. Clarkson, "Smaller core-sets for balls", SODA (2003);
P. Wolfe, "Finding the nearest point in a polytope", Mathematical Programming 11 (1976) 128–149
(convex_hull_gap の最小ノルム点)。
"""
from __future__ import annotations

from typing import Dict

import numpy as np

__all__ = [
    "min_enclosing_sphere",
    "convex_hull_gap",
]


def _as_points(points, min_n: int = 1) -> np.ndarray:
    """入力を (N,3) float64 に検証・正規化。fail-closed(形状不正/非有限/点数不足は ValueError)。"""
    P = np.asarray(points, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"points must be an (N,3) point cloud (got shape={P.shape})")
    if len(P) < min_n:
        raise ValueError(f"not enough points (need >= {min_n}, got {len(P)})")
    if not np.isfinite(P).all():
        raise ValueError("points contains NaN/Inf")
    return P


# ═══════════════════════════════════════════════════════════════════════════
# min_enclosing_sphere: 全点を含む(近似)最小包含球(Ritter + Bădoiu–Clarkson)
#
# 新規性: 「全点を内包する最小の球」= 最小包含球(MEB)。既存の fit_sphere_3d(点が球面上に
# ある前提の最小二乗フィット)/ ransac_sphere / hough_sphere_3d(球の検出)とは別の最適化問題で、
# repo に不在だった。凸包/AABB/OBB は既存の fs.convex_hull / fs.aabb / fs.obb を使うこと。
# ═══════════════════════════════════════════════════════════════════════════
def min_enclosing_sphere(points, refine_iters: int = 1000) -> Dict[str, object]:
    """点群 (N,3) → 全点を含む(近似)最小包含球 {center(3), radius}。

    ``fit_sphere_3d``(球面フィット)や ``ransac_sphere`` / ``hough_sphere_3d``(球検出)とは
    異なり、**全点を内包する最小の球**(minimum enclosing ball, MEB)を解く。2 段構成で
    「全点内包」を厳守しつつ半径を詰める:

    1. **Ritter (1990) 初期化** — 最遠の点対を粗く取り初期球にし、各点を走査して球外の点が
       あれば「その点と既存球の両方を含む」最小の球へ 1 回膨らませる(膨張式
       ``new_r=(r+d)/2`` / 中心を点方向へ ``(d-r)/(2d)`` 進める)。新球が旧球を完全に含むため、
       1 パスで全点内包を保証する。
    2. **Bădoiu–Clarkson (2003) core-set 反復による精緻化** — 反復 ``i`` で最遠点 ``q`` へ
       中心を ``1/(i+2)`` だけ寄せる。真の最小包含球へ単調収束する(半径過大な Ritter の
       ドリフトを詰める)。最後に半径を「中心からの最大距離」で確定するので、精緻化後も
       **必ず全点を内包**(近似ゆえ半径が過小になり点が漏れることはない、安全側)。

    精緻化した中心が Ritter より外接半径を縮められたときのみ採用する(常に Ritter 以下)。
    真の最小球(厳密解は Welzl の乱択線形時間法)ではなく高速な (1+ε) 近似。

    Parameters
    ----------
    points : array_like (N,3)
        入力点群(>= 1 点)。
    refine_iters : int
        Bădoiu–Clarkson 精緻化の反復数(既定 1000)。0 で Ritter のみ。

    Returns
    -------
    dict
        - ``center``: (3,) float64 — 球中心(世界座標)。
        - ``radius``: float — 半径(全点を内包)。

    Raises
    ------
    ValueError
        形状不正・非有限・点数 0、または ``refine_iters`` が負のとき(fail-closed)。
    """
    P = _as_points(points, min_n=1)
    if refine_iters < 0:
        raise ValueError("refine_iters must be non-negative")
    if len(P) == 1:
        return {"center": P[0].astype(np.float64), "radius": 0.0}

    # --- 1) Ritter 初期化: 最遠点対 → 中心/半径、球外の点ごとに最小膨張 ---
    x = P[0]
    y = P[int(np.argmax(np.linalg.norm(P - x, axis=1)))]
    z = P[int(np.argmax(np.linalg.norm(P - y, axis=1)))]
    c = (y + z) / 2.0
    r = float(np.linalg.norm(y - z) / 2.0)
    for p in P:
        diff = p - c
        d = float(np.linalg.norm(diff))
        if d > r:
            r_new = (r + d) / 2.0
            c = c + ((d - r_new) / d) * diff   # (d - r_new)/d == (d - r)/(2d)
            r = r_new
    c_ritter, r_ritter = c.copy(), r

    # --- 2) Bădoiu–Clarkson 精緻化: 最遠点へ 1/(i+2) だけ中心を寄せる ---
    c_bc = c_ritter.copy()
    for it in range(refine_iters):
        d = np.linalg.norm(P - c_bc, axis=1)
        j = int(np.argmax(d))
        c_bc = c_bc + (P[j] - c_bc) / (it + 2)
    # 半径は「中心からの最大距離」で確定 → 全点内包を厳守(過小にならない安全側)
    r_bc = float(np.linalg.norm(P - c_bc, axis=1).max())

    # Ritter を上回る(半径を縮める)ときのみ採用 → 常に Ritter 以下を保証
    if r_bc < r_ritter:
        return {"center": c_bc.astype(np.float64), "radius": r_bc}
    return {"center": c_ritter.astype(np.float64), "radius": float(r_ritter)}
# ═══════════════════════════════════════════════════════════════════════════
# convex_hull_gap: 2 つの凸包の隙間(Wolfe の最小ノルム点 + 線形計画の独立な判定)
#
# 新規性(2026-11-15): 3-D の凸集合どうしの隙間を、保証つきの上下限と一緒に返す op が無かった。
# 近い op は別の量を返す: hausdorff_distance / chamfer_distance は点どうし(凸包が交わる十字の棒でも
# 「離れている」と出る)、polygon_fit_check は 2-D の平行移動だけの LP、cr_collision は 2-D 矩形の SAT、
# distance_segment_segment は 2 点ずつの凸包に限った特例(門の独立な検算に使う)。
# ═══════════════════════════════════════════════════════════════════════════
def _as_cloud(points, name: str, op: str) -> np.ndarray:
    """(N, d) float64(d = 2 か 3)に検証・正規化する。1 点なら (d,) も受ける。fail-closed。"""
    P = np.asarray(points, dtype=np.float64)
    if P.size == 0:
        raise ValueError("%s: %s is empty — pass at least one point" % (op, name))
    if P.ndim == 1:
        P = P.reshape(1, -1)
    if P.ndim != 2 or P.shape[1] not in (2, 3):
        raise ValueError("%s: %s must be (N, 3) or (N, 2) points (got shape %r)" % (op, name, P.shape))
    if not np.isfinite(P).all():
        raise ValueError("%s: %s contains NaN/Inf" % (op, name))
    return P


def _affine_minimizer(S: np.ndarray) -> np.ndarray:
    """点 S (m, d) の**アフィン包**の上で原点に最も近い点の重み μ(Σμ = 1、負も可)。

    S[0] を基準に ``min ‖S[0] + Σ c_k (S[k] − S[0])‖`` を最小二乗で解く(rank が落ちても lstsq の
    最小ノルム解で点は一意に決まる)。"""
    if len(S) == 1:
        return np.ones(1)
    E = (S[1:] - S[0]).T
    c, *_ = np.linalg.lstsq(E, -S[0], rcond=None)
    return np.concatenate([[1.0 - float(c.sum())], c])


def _hull_gap_lp(A0: np.ndarray, B0: np.ndarray) -> float:
    """``‖w‖∞ ≤ 1`` で ``w·a ≤ c ≤ w·b − t``(全頂点)を満たす最大の t(scipy の HiGHS)。

    最小ノルム点と何も共有しない独立な判定。t > 0 ⇔ 凸包が離れていて ``t/√d ≤ 隙間 ≤ t``、
    t = 0 ⇔ 接するか重なる(w = 0 は常に実行可能なので t は負にならない)。上限の打ち切りは置かない
    (``‖w‖∞ ≤ 1`` で t は有界)。"""
    from scipy.optimize import linprog
    na, nb, d = len(A0), len(B0), A0.shape[1]
    a_ub = np.zeros((na + nb, d + 2))
    a_ub[:na, :d], a_ub[:na, d] = A0, -1.0
    a_ub[na:, :d], a_ub[na:, d], a_ub[na:, d + 1] = -B0, 1.0, 1.0
    cost = np.zeros(d + 2)
    cost[d + 1] = -1.0
    res = linprog(cost, A_ub=a_ub, b_ub=np.zeros(na + nb),
                  bounds=[(-1.0, 1.0)] * d + [(None, None), (0.0, None)], method="highs")
    if res.status != 0:
        raise RuntimeError("convex_hull_gap: the separation LP did not solve: %s" % res.message)
    return max(0.0, float(res.x[d + 1]))


def convex_hull_gap(points_a, points_b, tol: float = 1e-9, max_iter: int = 1000,
                    check: str = "lp") -> Dict[str, object]:
    """2 つの頂点集合の凸包どうしの隙間(最短距離)を、保証つきの上下限と一緒に返す。

    凸包 conv(A) と conv(B) の距離 ``min ‖a − b‖``(a ∈ conv(A), b ∈ conv(B))は、差の集合
    D = {aᵢ − bⱼ} の凸包の中で原点に最も近い点のノルムに等しい。これを **Wolfe (1976) の最小ノルム
    点の方法**で解く。D を作らずに ``argmin x·p`` だけを A と B から別々に引く(``A @ x`` の最小と
    ``B @ x`` の最大)ので、手間は 1 反復 O(N_A + N_B)。Wolfe の方法は有限回で厳密な点に着く
    (Frank–Wolfe の O(1/k) の収束ではない)。

    止める条件は上下限の差 ``≤ tol``:

    * 上限 ``gap_upper = ‖b* − a*‖`` —— a* ∈ conv(A)、b* ∈ conv(B) を重みつきで実際に作った点の距離。
    * 下限 ``gap_lower = min_b n·b − max_a n·a`` —— n = (b* − a*)/‖b* − a*‖ の向きの、頂点から直接
      測った**分離の帯の幅**(この幅の帯があることがそのまま「離れている」証明)。

    ``check="lp"``(既定)では、最小ノルム点と何も共有しない線形計画(scipy の HiGHS)で離れ方を
    別に決める: ``‖w‖∞ ≤ 1`` で ``w·a ≤ c ≤ w·b − t`` を満たす最大の t。t > 0 ⇔ 離れていて
    ``t/√d ≤ 隙間 ≤ t``、t = 0 ⇔ 接するか重なる。2 つの答えが食い違えば RuntimeError(黙って片方を
    返さない)。``check="none"`` で線形計画を省く(numpy だけで走る)。食い違いの判定には丸めの幅
    slack = max(tol, 1e-6·scale)(scale = 平均を引いた座標の最大の絶対値、1 以上。HiGHS の可能性の許容より広く)を
    持たせるので、**隙間が slack より小さいと、線形計画が「接触」(t = 0)と言っても食い違いにならない**(座標が
    1e3 の桁なら 1e-3 未満の隙間)。その帯の中で効くのは最小ノルム点の上下限の保証だけ。

    **頂点どうしの距離では重なりを否定できない**(製作の教訓): 細い棒 2 本の十字は、凸包が交わるのに
    頂点の間は離れている。hausdorff_distance や最近頂点の距離は「離れている」と出すが、この op は
    重なり(``separated = False``)と判定する。

    * 非凸の物体(部品・リンクのメッシュ)に直接使うと、**凸包の**重なりを部品の干渉と読み違える。
      凸に分けた部品ごとに使うこと(凸包は物体より大きいので、離れていれば物体も離れている)。
    * 重なっているときの**貫通の深さは返さない**(``gap = 0``、``witness_a`` ≈ ``witness_b`` は共通の点)。
    * ``gap ≤ tol`` は接触と数える(``separated = False``)。座標は平均を引いてから解く(並進で値が
      変わらない)。2-D の点 (N, 2) にも使える(線形計画の比は √2)。

    Parameters
    ----------
    points_a, points_b : array_like (N, 3) または (N, 2)
        凸包の頂点(全点でもよい。凸包を先に作らなくてよい)。次元はそろえる。1 点なら (d,) も可。
    tol : float
        上下限の差の許容(座標と同じ単位、既定 1e-9)。> 0。
    max_iter : int
        Wolfe の反復(主・副の合計)の上限(既定 1000)。上下限の差が ``tol`` を切る前に届いたら
        RuntimeError(保証の無い近似値を黙って返さない)。
    check : {"lp", "none"}
        線形計画の独立な判定を足すか。

    Returns
    -------
    dict
        ``separated`` (bool)、``gap``(離れていれば隙間 = ``gap_upper``、接触・重なりなら 0.0)、
        ``gap_lower``・``gap_upper``(保証つきの下限と上限)、``witness_a``・``witness_b``(最も近い点の組、
        (d,))、``separating_normal``(A から B へ向く単位ベクトル (d,)、離れていなければ None)、
        ``lp_t``(線形計画の t、``check="none"`` なら None)、``iterations``。

    Raises
    ------
    ValueError
        形状不正・非有限・次元の不一致・``tol ≤ 0``・``max_iter < 1``・``check`` が未知のとき(fail-closed)。
    RuntimeError
        ``max_iter`` までに上下限の差が ``tol`` を切らないとき、線形計画が解けないとき、最小ノルム点と
        線形計画の離れ方の判定が食い違うとき。

    空の入力(``points_a`` が 0 要素)は ValueError で拒否する。

    English: distance between the convex hulls of two vertex sets by Wolfe's minimum-norm-point method on
    the implicit Minkowski difference (finite and exact, not Frank–Wolfe), returned with certified bounds
    (an explicit pair of hull points above, a separating slab below). An independent HiGHS LP decides
    separation (t > 0 iff disjoint, ``t/sqrt(d) <= gap <= t``); a disagreement raises. Penetration depth
    is not computed. Use convex pieces: the hull of a non-convex part over-reports contact.

    呼び出し例::

        import numpy as np
        import hull3d
        g = np.array(np.meshgrid([0, 1], [0, 1], [0, 1])).reshape(3, -1).T.astype(float)
        r = hull3d.convex_hull_gap(g, g + [1.25, 0.0, 0.0])            # x に 0.25 離れた単位立方体
        assert r["separated"] and abs(r["gap"] - 0.25) < 1e-12
        rod_a = np.array([[-1.0, -0.01, 0.0], [1.0, -0.01, 0.0], [-1.0, 0.01, 0.0], [1.0, 0.01, 0.0]])
        rod_b = rod_a[:, [1, 0, 2]]                                    # 十字に交わる棒
        assert not hull3d.convex_hull_gap(rod_a, rod_b)["separated"]  # 頂点の間は 1.4 離れている
    """
    op = "convex_hull_gap"
    A = _as_cloud(points_a, "points_a", op)
    B = _as_cloud(points_b, "points_b", op)
    if A.shape[1] != B.shape[1]:
        raise ValueError("%s: points_a and points_b must have the same dimension (got %d and %d)"
                         % (op, A.shape[1], B.shape[1]))
    tol = float(tol)
    if not (np.isfinite(tol) and tol > 0.0):
        raise ValueError("%s: tol must be a positive finite length (got %r)" % (op, tol))
    if isinstance(max_iter, bool) or int(max_iter) != max_iter or int(max_iter) < 1:
        raise ValueError("%s: max_iter must be an integer >= 1 (got %r)" % (op, max_iter))
    max_iter = int(max_iter)
    if check not in ("lp", "none"):
        raise ValueError("%s: check must be 'lp' or 'none' (got %r)" % (op, check))
    d = A.shape[1]
    c0 = 0.5 * (A.mean(0) + B.mean(0))                    # 並進で値を変えない(桁落ちを避ける)
    A0, B0 = A - c0, B - c0

    def support(x):
        """D の上で x·p を最小にする点 p = a − b(a は A @ x の最小、b は B @ x の最大)。"""
        ia = int(np.argmin(A0 @ x))
        ib = int(np.argmax(B0 @ x))
        return ia, ib, A0[ia] - B0[ib]

    x0 = A0.mean(0) - B0.mean(0)
    if not np.any(x0):
        x0 = np.ones(d)
    ia, ib, p = support(x0)
    S = p[None, :].copy()                                 # 囲い(corral)の点
    pairs = [(ia, ib)]                                    # 各点の (A の添字, B の添字)
    lam = np.ones(1)                                      # 凸結合の重み
    x = p.copy()
    it, converged = 0, False
    while it < max_iter:
        it += 1
        nx = float(np.sqrt(x @ x))
        if nx <= tol:                                     # 原点に届いた = 接するか重なる
            converged = True
            break
        ia, ib, p = support(x)
        if nx - float(x @ p) / nx <= tol:                 # 上限 − 下限 ≤ tol(Wolfe の最適性)
            converged = True
            break
        if (ia, ib) in pairs:                             # 進めない(丸めの床)
            break
        S = np.vstack([S, p])
        pairs.append((ia, ib))
        lam = np.append(lam, 0.0)
        while it < max_iter:                              # 副の反復: 囲いのアフィン最小点へ
            mu = _affine_minimizer(S)
            if np.all(mu > 1e-12):
                lam, x = mu, mu @ S
                break
            it += 1
            neg = (mu <= 1e-12) & (lam - mu > 0.0)
            theta = float(np.min(lam[neg] / (lam[neg] - mu[neg]))) if neg.any() else 1.0
            lam = (1.0 - theta) * lam + theta * mu
            keep = lam > 1e-12
            if keep.all():
                keep[int(np.argmin(lam))] = False
            S, lam = S[keep], lam[keep]
            pairs = [q for q, k in zip(pairs, keep) if k]
            lam = lam / lam.sum()
            x = lam @ S
    wa = np.zeros(d)
    wb = np.zeros(d)
    for w, (i, j) in zip(lam, pairs):
        wa += w * A[i]
        wb += w * B[j]
    upper = float(np.linalg.norm(wb - wa))
    normal, lower = None, 0.0
    if upper > 0.0:
        normal = (wb - wa) / upper
        lower = float(np.min(B @ normal) - np.max(A @ normal))
    if not converged:
        # 止める条件そのものが保証(上限 = 作った点の組、下限 = 分離の帯)なので、そこに届かない答えは
        # 出さない(fail-closed)。囲いの計算が壊れても、黙って違う隙間は返らない。
        raise RuntimeError("%s: no certified answer within max_iter = %d (bounds %.6g .. %.6g, tol %.3g); "
                           "raise max_iter or tol" % (op, max_iter, max(lower, 0.0), upper, tol))
    separated = upper > tol
    out = {"separated": bool(separated), "gap": upper if separated else 0.0,
           "gap_lower": max(lower, 0.0), "gap_upper": upper,
           "witness_a": wa, "witness_b": wb,
           "separating_normal": normal if separated else None,
           "lp_t": None, "iterations": int(it)}
    if check == "lp":
        t = _hull_gap_lp(A0, B0)
        scale = max(1.0, float(np.max(np.abs(np.vstack([A0, B0])))))
        slack = max(tol, 1e-6 * scale)                    # HiGHS の可能性の許容(1e-7 相対)より広く
        # 答えは t/√d ≤ 隙間 ≤ t の帯に入るはず(重なり = 隙間 0 なら t ≈ 0)
        agree = t / np.sqrt(d) - slack <= out["gap"] <= t + slack
        if not agree:
            raise RuntimeError("%s: the separation LP (t = %.6g) and the minimum-norm point (gap = %.6g, "
                               "separated = %s) disagree" % (op, t, out["gap"], separated))
        out["lp_t"] = t
    return out
