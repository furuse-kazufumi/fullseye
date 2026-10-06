# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mathgeometry — 離散幾何と位相の古典(オイラー標数・角欠損(Gauss–Bonnet)・Delaunay 分割・熱法の測地距離)。

2026-10-03 の棚卸しで、どの層にも op として無かったもの(numpy + scipy だけ):

* **オイラー標数と種数** —— 三角形メッシュの V − E + F。閉じた向き付け可能な曲面なら χ = 2 − 2g(g = 穴の数)。
  メッシュ修復の検査(閉じているか・穴は何個か)にそのまま使える。
* **角欠損(離散 Gauss 曲率)** —— 頂点のまわりの角の和が 2π からどれだけ欠けているか。**閉じたメッシュでは総和が
  厳密に 2πχ**(Descartes の定理 = 離散 Gauss–Bonnet)。どんなに歪んだメッシュでも、穴の数だけで総和が決まる。
* **Delaunay 分割** —— 平面の点を「どの三角形の外接円の中にも他の点が無い」ように結ぶ。Voronoi 図と双対。
  三角形の数は 2n − h − 2(h = 凸包上の点の数)。
* **熱法の測地距離**(Crane, Weischedel & Wardetzky 2013)—— 曲面上の最短距離を、熱を少しだけ広げる → 勾配の向きを
  正規化する → Poisson 方程式を解く、の 3 段で求める。辺をたどる Dijkstra(``geodesic_mesh``)は辺の方向にしか
  進めず距離を過大に見積もるが、熱法は面の中を斜めに進める。
* **NURBS 曲線・曲面**(Piegl & Tiller 1997)—— 重みつきの有理 B スプライン。多項式では描けない円・球・トーラスを
  **厳密に** 描け、射影変換と可換。制御点は一般に通らない(旧 ``gen_contour_nurbs_xld`` は通る補間だった)。

門は ``tests/test_mathgeometry.py``。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import sparse
from scipy.sparse import linalg as splinalg

__all__ = ["angle_defect", "delaunay_triangulate", "geodesic_heat", "geodesic_heat_grid", "mesh_euler_characteristic",
           "mesh_torus", "nurbs_circle", "nurbs_curve", "nurbs_revolve", "nurbs_surface"]


def _mesh(vertices, faces=None):
    if faces is None:
        if not (isinstance(vertices, (tuple, list)) and len(vertices) == 2):
            raise ValueError("メッシュ: (vertices, faces) を別々に渡すか、mesh の組 (V, F) を 1 つ渡す")
        vertices, faces = vertices
    V = np.asarray(vertices, dtype=np.float64)
    F = np.asarray(faces)
    if V.ndim != 2 or V.shape[1] not in (2, 3) or V.shape[0] < 3:
        raise ValueError("メッシュ: 頂点は (N, 3)(または (N, 2))で 3 個以上")
    if F.ndim != 2 or F.shape[1] != 3 or F.shape[0] < 1:
        raise ValueError("メッシュ: 面は三角形の (M, 3) 整数")
    if not np.all(np.isfinite(V)):
        raise ValueError("メッシュ: 頂点に NaN/inf がある")
    F = F.astype(np.int64)
    if F.min() < 0 or F.max() >= V.shape[0]:
        raise ValueError("メッシュ: 面が存在しない頂点を指している")
    if V.shape[1] == 2:
        V = np.hstack([V, np.zeros((V.shape[0], 1))])
    return V, F


def _edges(F):
    e = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    uniq, counts = np.unique(e, axis=0, return_counts=True)
    return uniq, counts


def mesh_torus(R: float = 2.0, r: float = 0.7, n_u: int = 32, n_v: int = 16) -> tuple:
    """トーラス(ドーナツ)の閉じた三角形メッシュ (vertices, faces)。大きい半径 R・管の半径 r(R > r > 0)。

    種数 1 の曲面の見本: χ = 0、角欠損の総和 = 0(外側の凸の部分が正、内側の鞍の部分が負で打ち消し合う)。
    頂点は (u, v) の格子(u が大円、v が管のまわり)の順で、``u = i·2π/n_u``、``v = j·2π/n_v`` の頂点が i·n_v + j 番。
    """
    R, r, n_u, n_v = float(R), float(r), int(n_u), int(n_v)
    if not (R > r > 0) or n_u < 3 or n_v < 3:
        raise ValueError("mesh_torus: R > r > 0、n_u, n_v >= 3")
    u, v = np.meshgrid(np.arange(n_u) * 2 * math.pi / n_u, np.arange(n_v) * 2 * math.pi / n_v, indexing="ij")
    V = np.stack([(R + r * np.cos(v)) * np.cos(u), (R + r * np.cos(v)) * np.sin(u), r * np.sin(v)], -1).reshape(-1, 3)
    i, j = np.meshgrid(np.arange(n_u), np.arange(n_v), indexing="ij")
    a_ = (i * n_v + j).ravel()
    b_ = (((i + 1) % n_u) * n_v + j).ravel()
    c_ = (((i + 1) % n_u) * n_v + (j + 1) % n_v).ravel()
    d_ = (i * n_v + (j + 1) % n_v).ravel()
    F = np.concatenate([np.stack([a_, b_, c_], 1), np.stack([a_, c_, d_], 1)])
    return V, F


def mesh_euler_characteristic(vertices, faces=None) -> dict:
    """三角形メッシュの V − E + F と、閉じた向き付け可能な曲面なら種数 g = (2 − χ)/2。

    使われていない頂点は数えない(浮いた頂点で χ がずれるのを防ぐ)。境界辺(1 枚の面にしか属さない辺)と
    非多様体辺(3 枚以上)も返す —— 境界があると χ = 2 − 2g − b(b = 境界の輪の数)になり、種数は ``None``。
    門: 正二十面体 χ = 2、トーラス χ = 0・種数 1、円板 χ = 1。
    """
    V, F = _mesh(vertices, faces)
    used = np.unique(F)
    E, counts = _edges(F)
    chi = int(used.size - E.shape[0] + F.shape[0])
    boundary = int(np.sum(counts == 1))
    nonmanifold = int(np.sum(counts > 2))
    closed = boundary == 0 and nonmanifold == 0
    genus = (2 - chi) // 2 if closed and (2 - chi) % 2 == 0 else None
    return {"V": int(used.size), "E": int(E.shape[0]), "F": int(F.shape[0]), "chi": chi, "genus": genus,
            "closed": closed, "boundary_edges": boundary, "nonmanifold_edges": nonmanifold}


def _corner_angles(V, F):
    ang = np.empty(F.shape)
    for k in range(3):
        a, b, c = V[F[:, k]], V[F[:, (k + 1) % 3]], V[F[:, (k + 2) % 3]]
        u, w = b - a, c - a
        ang[:, k] = np.arctan2(np.linalg.norm(np.cross(u, w), axis=1), np.einsum("ij,ij->i", u, w))
    return ang


def angle_defect(vertices, faces=None) -> dict:
    """頂点ごとの角欠損(離散 Gauss 曲率)K_v = 2π − Σ(その頂点での三角形の角)。境界の頂点は π − Σ(測地曲率)。

    閉じたメッシュでは Σ K_v = 2πχ が**厳密に**成り立つ(Descartes の定理)。境界があるときは
    Σ(内部の K) + Σ(境界の π − Σθ) = 2πχ(離散 Gauss–Bonnet)。
    返り値 ``{"defect", "total", "two_pi_chi", "is_boundary"}``。
    """
    V, F = _mesh(vertices, faces)
    ang = _corner_angles(V, F)
    s = np.zeros(V.shape[0])
    np.add.at(s, F.ravel(), ang.ravel())
    E, counts = _edges(F)
    bnd = np.zeros(V.shape[0], dtype=bool)
    bnd[E[counts == 1].ravel()] = True
    used = np.zeros(V.shape[0], dtype=bool)
    used[F.ravel()] = True
    d = np.where(bnd, math.pi - s, 2 * math.pi - s)
    d[~used] = 0.0
    chi = mesh_euler_characteristic(V, F)["chi"]
    return {"defect": d, "total": float(d.sum()), "two_pi_chi": 2 * math.pi * chi, "is_boundary": bnd}


def delaunay_triangulate(points) -> dict:
    """平面 (N, 2) の三角形分割、または空間 (N, 3) の四面体分割(Delaunay、scipy.spatial = Qhull)。

    返り値 ``{"simplices", "hull", "n_simplices", "circumcenters", "circumradii", "dim"}``(2-D では ``triangles`` /
    ``n_triangles`` も同じ中身で返す)。外接円・外接球は描画・Voronoi 用。
    門: **どの外接円(球)の中にも他の点が無い**(空円性。2-D は既存の ``is_delaunay_2d`` も真値)/ 2-D の三角形の数は
    2n − h − 2(h = 凸包の頂点数)/ 3-D の四面体の集まりは凸な塊なので V − E + F − T = 1(Euler)。
    共円・共球の点が多いと分割は一意でない(どれも Delaunay)。
    """
    from scipy.spatial import ConvexHull, Delaunay
    P = np.asarray(points, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] not in (2, 3) or P.shape[0] < P.shape[1] + 1 or not np.all(np.isfinite(P)):
        raise ValueError("delaunay_triangulate: 有限な (N, 2) か (N, 3) の点が次元 + 1 個以上")
    if np.unique(P, axis=0).shape[0] != P.shape[0]:
        raise ValueError("delaunay_triangulate: 重複した点がある")
    try:
        tri = Delaunay(P)
    except Exception as exc:                                    # noqa: BLE001  Qhull の退化(全点が一直線・一平面)
        raise ValueError("delaunay_triangulate: 退化した点集合(一直線・一平面など): %s" % exc) from exc
    S = tri.simplices
    d = P.shape[1]
    # 外接中心: |c − p0|² = |c − pk|² → 2 (pk − p0)·c = |pk|² − |p0|²(k = 1..d)を単体ごとに解く
    p0 = P[S[:, 0]]
    A = 2 * (P[S[:, 1:]] - p0[:, None, :])
    rhs = (P[S[:, 1:]] ** 2).sum(-1) - (p0 ** 2).sum(-1)[:, None]
    cc = np.linalg.solve(A, rhs[..., None])[..., 0]
    out = {"simplices": S, "hull": ConvexHull(P).vertices, "n_simplices": int(S.shape[0]),
           "circumcenters": cc, "circumradii": np.linalg.norm(cc - p0, axis=1), "dim": d}
    if d == 2:
        out["triangles"], out["n_triangles"] = S, int(S.shape[0])
    return out


def _cotan_laplacian(V, F):
    n = V.shape[0]
    I, J, W = [], [], []
    for k in range(3):
        i, j, o = F[:, (k + 1) % 3], F[:, (k + 2) % 3], F[:, k]
        u, w = V[i] - V[o], V[j] - V[o]
        cot = np.einsum("ij,ij->i", u, w) / np.maximum(np.linalg.norm(np.cross(u, w), axis=1), 1e-300)
        I += [i, j]
        J += [j, i]
        W += [0.5 * cot, 0.5 * cot]
    I, J, W = np.concatenate(I), np.concatenate(J), np.concatenate(W)
    L = sparse.coo_matrix((W, (I, J)), shape=(n, n)).tocsr()
    L = L - sparse.diags(np.asarray(L.sum(axis=1)).ravel())
    return L                                                     # 負半定値(−Δ の弱形式)


def _spd_solve(A, b):
    """対称正定値の疎な方程式。小さければ直接法、大きければ対角前処理つき共役勾配法
    (3-D の 33³ で直接法は fill-in で 10 秒、CG は 1 秒未満、2026-10-03 実測)。"""
    if A.shape[0] <= 20000:
        return splinalg.spsolve(A.tocsc(), b)
    d = A.diagonal()
    Minv = sparse.diags(1.0 / np.where(d > 0, d, 1.0))
    x, info = splinalg.cg(A, b, M=Minv, rtol=1e-10, maxiter=20000)
    if info != 0:
        raise RuntimeError("geodesic_heat_grid: 共役勾配法が収束しなかった(info=%d)" % info)
    return x


def geodesic_heat_grid(mask, source=None, *, spacing=1.0, t: float | None = None) -> dict:
    """2-D 画像・3-D ボリュームの格子の上で、障害物を避けた測地距離を熱法で求める(Crane et al. 2013 の格子版)。

    ``mask`` は通れる画素/ボクセルが True の bool 配列(2-D か 3-D)、``source`` は始点の添字(1 点 ``(i, j[, k])``
    か点の列。省略すると最初の通れる画素)。``spacing`` は軸ごとの画素の大きさ(スカラーか軸ごと)。
    1) (I − tΔ) u = δ(熱を広げる、Δ は通れる画素の間だけを結ぶ 2d+1 点の Laplacian = 障害物は断熱)
    2) X = −∇u / |∇u|(面の間の差分で)  3) Δφ = ∇·X を解いて始点で 0 にずらす。
    返り値 ``{"distance", "t"}``(通れない画素と、始点と繋がらない画素は inf)。
    門: 障害物の無い空間ではユークリッド距離へ収束する。画素の Dijkstra(4/8 近傍)は格子の向きの誤差
    (4 近傍で最大 41%、8 近傍で最大 8%)が細かくしても消えないが、熱法は消えていく。
    """
    M = np.asarray(mask, dtype=bool)
    if M.ndim not in (2, 3) or M.size < 4:
        raise ValueError("geodesic_heat_grid: mask は 2-D か 3-D の bool 配列")
    sp = np.broadcast_to(np.asarray(spacing, dtype=np.float64), (M.ndim,)).copy()
    if np.any(sp <= 0):
        raise ValueError("geodesic_heat_grid: spacing は正")
    if source is None:
        if not M.any():
            raise ValueError("geodesic_heat_grid: 通れる画素が 1 つも無い")
        source = np.argwhere(M)[0]
    src = np.atleast_2d(np.asarray(source, dtype=np.int64))
    if src.shape[1] != M.ndim:
        raise ValueError("geodesic_heat_grid: source は %d 次元の添字" % M.ndim)
    if np.any(src < 0) or np.any(src >= np.array(M.shape)) or not np.all(M[tuple(src.T)]):
        raise ValueError("geodesic_heat_grid: source は mask の中の通れる画素")
    from scipy import ndimage
    lab, _ = ndimage.label(M)
    comp = np.isin(lab, np.unique(lab[tuple(src.T)]))
    idx = -np.ones(M.shape, dtype=np.int64)
    idx[comp] = np.arange(int(comp.sum()))
    n = int(comp.sum())
    # 辺(隣り合う通れる画素の組)ごとの差分行列 G: (G u)_e = (u_j − u_i) / h。Δ = −GᵀG、∇· = −Gᵀ。
    # ★最初は発散を np.gradient(中心差分)で取り、Poisson を 5 点 Laplacian で解いていた —— 2 つが互いの随伴でなく、
    #   縁で発散の総和も釣り合わず、隅で距離が真値の 0.52 倍に縮んだ(2026-10-03)。同じ G から両方を作ると
    #   Poisson は「勾配が X に最も近い φ」の最小二乗そのものになり、縁(断熱)でも無矛盾になる。
    er, ec, ev, eax = [], [], [], []
    m = 0
    for ax in range(M.ndim):
        a = [slice(None)] * M.ndim
        b = [slice(None)] * M.ndim
        a[ax], b[ax] = slice(0, -1), slice(1, None)
        both = comp[tuple(a)] & comp[tuple(b)]
        i, j = idx[tuple(a)][both], idx[tuple(b)][both]
        k = np.arange(m, m + i.size)
        er += [k, k]
        ec += [i, j]
        ev += [np.full(i.size, -1.0 / sp[ax]), np.full(i.size, 1.0 / sp[ax])]
        eax.append((ax, i, j))
        m += i.size
    G = sparse.coo_matrix((np.concatenate(ev), (np.concatenate(er), np.concatenate(ec))), shape=(m, n)).tocsr()
    L = -(G.T @ G)
    h = float(np.mean(sp))
    t = h * h if t is None else float(t)
    delta = np.zeros(n)
    delta[idx[tuple(src.T)]] = 1.0
    # ★熱の段は直接法で解く: u は距離とともに e^{−r/h} で 1e-30 まで落ち、遠くの勾配の「向き」はその極小値の
    #   相対精度に乗っている。CG は絶対誤差 ~1e-12 で止まり、極小値を塗りつぶして遠くの向きを壊した
    #   (3-D で誤差 0.045 → 0.279、2026-10-03)。定数のずれが無害な Poisson の段だけ CG にする。
    u = splinalg.spsolve((sparse.eye(n) - t * L).tocsc(), delta)
    # 画素ごとの勾配(隣の辺の平均)で向きを正規化し、辺の成分に戻す
    gu = G @ u
    cell = np.zeros((n, M.ndim))
    cnt = np.zeros((n, M.ndim))
    off = 0
    for ax, i, j in eax:
        ge = gu[off:off + i.size]
        np.add.at(cell[:, ax], i, ge)
        np.add.at(cell[:, ax], j, ge)
        np.add.at(cnt[:, ax], i, 1)
        np.add.at(cnt[:, ax], j, 1)
        off += i.size
    cell /= np.maximum(cnt, 1)
    Xc = -cell / np.maximum(np.linalg.norm(cell, axis=1, keepdims=True), 1e-300)
    Xe = np.empty(m)
    off = 0
    for ax, i, j in eax:
        Xe[off:off + i.size] = 0.5 * (Xc[i, ax] + Xc[j, ax])
        off += i.size
    A = (G.T @ G + 1e-10 * sparse.eye(n)).tocsr()
    phi_c = _spd_solve(A, G.T @ Xe)
    phi_c = phi_c - phi_c[idx[tuple(src.T)]].mean()
    D = np.full(M.shape, np.inf)
    D[comp] = phi_c
    return {"distance": D, "t": t}


def geodesic_heat(vertices, faces=None, source=0, *, t: float | None = None) -> dict:
    """熱法による曲面上の測地距離(Crane et al. 2013)。``source`` は頂点番号(または番号の列、既定は頂点 0)。
    メッシュは ``(vertices, faces)`` でも mesh の組 1 つでもよい。

    1) (M − tL) u = δ を 1 ステップ解く(熱を時間 t だけ広げる、t の既定 = 平均辺長²)
    2) 各三角形で X = −∇u / |∇u|(熱が来た向きと逆 = 距離が増える向き)
    3) L φ = ∇·X を解き、source で 0 になるようずらす
    門: 平面メッシュでユークリッド距離、球面で大円距離 Rθ に、細かくするほど近づく。
    返り値 ``{"distance", "t"}``(どの面にも使われない頂点と、始点と繋がらない頂点は inf)。
    """
    V, F = _mesh(vertices, faces)
    n = V.shape[0]
    src = np.atleast_1d(np.asarray(source, dtype=np.int64))
    if src.size == 0 or src.min() < 0 or src.max() >= n:
        raise ValueError("geodesic_heat: source は存在する頂点番号")
    e1, e2 = V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]
    nrm = np.cross(e1, e2)
    area2 = np.linalg.norm(nrm, axis=1)
    if np.any(area2 <= 1e-300):
        raise ValueError("geodesic_heat: 面積 0 の三角形がある")
    Nf = nrm / area2[:, None]
    A = 0.5 * area2
    E, _ = _edges(F)
    h = float(np.mean(np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)))
    t = h * h if t is None else float(t)
    # ★2026-10-07: 面に使われない頂点が 1 個あると M と L にその行が 0 で入り、熱の段が特異 → 全頂点 NaN
    #   (513 頂点で例外なし)。始点と繋がらない成分は φ が任意の定数(実測 0.755)で有限に見えた。
    #   始点を含む連結成分だけで解き、残り(未使用・非連結)は inf にする(geodesic_heat_grid と同じ約束)。
    from scipy.sparse.csgraph import connected_components
    used = np.zeros(n, dtype=bool)
    used[F.ravel()] = True
    if not used[src].all():
        raise ValueError("geodesic_heat: source がどの面にも使われていない頂点(距離が定義できない)")
    _, comp = connected_components(
        sparse.coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(n, n)), directed=False)
    keep = np.isin(comp, comp[src])
    n_all = n
    if not keep.all():
        remap = -np.ones(n_all, dtype=np.int64)
        remap[keep] = np.arange(int(keep.sum()))
        fk = keep[F[:, 0]]                                        # 面は 1 つの成分に丸ごと属する
        V, F, A, Nf = V[keep], remap[F[fk]], A[fk], Nf[fk]
        src = remap[src]
        n = V.shape[0]
    M = np.zeros(n)
    np.add.at(M, F.ravel(), np.repeat(A / 3.0, 3))
    L = _cotan_laplacian(V, F)
    delta = np.zeros(n)
    delta[src] = 1.0
    u = splinalg.spsolve((sparse.diags(M) - t * L).tocsc(), delta)
    # 各面の勾配: ∇u = Σ u_i (N × e_i) / (2A)、e_i は頂点 i の対辺(向きつき)
    g = np.zeros((F.shape[0], 3))
    for k in range(3):
        i, j, l = F[:, k], F[:, (k + 1) % 3], F[:, (k + 2) % 3]
        g += u[i][:, None] * np.cross(Nf, V[l] - V[j])
    g /= (2 * A)[:, None]
    X = -g / np.maximum(np.linalg.norm(g, axis=1), 1e-300)[:, None]
    div = np.zeros(n)
    # 発散 ∇·X(頂点 i): ½ Σ_faces [cot θ1 (e1·X) + cot θ2 (e2·X)]
    for k in range(3):
        i, j, l = F[:, k], F[:, (k + 1) % 3], F[:, (k + 2) % 3]
        e_ij, e_il = V[j] - V[i], V[l] - V[i]

        def _cot(p, q, r):
            u_, w_ = V[q] - V[p], V[r] - V[p]
            return np.einsum("ij,ij->i", u_, w_) / np.maximum(np.linalg.norm(np.cross(u_, w_), axis=1), 1e-300)
        cot_l = _cot(l, i, j)                                     # 頂点 l の角(辺 ij の対角)
        cot_j = _cot(j, l, i)                                     # 頂点 j の角(辺 il の対角)
        np.add.at(div, i, 0.5 * (cot_l * np.einsum("ij,ij->i", e_ij, X) + cot_j * np.einsum("ij,ij->i", e_il, X)))
    Lr = (L + 1e-12 * sparse.eye(n)).tocsc()
    phi = splinalg.spsolve(Lr, div)
    ck = comp[keep]
    cs = np.unique(ck[src])
    if cs.size == 1:
        phi = phi - phi[src].mean()
        dist = phi - phi[src].min()
    else:
        # ★2026-10-07: 始点が別々の成分にあると φ の定数は成分ごとに任意 → 成分ごとに始点で 0 に合わせる
        dist = np.empty(n)
        for c in cs:
            sel = ck == c
            s_c = src[ck[src] == c]
            pc = phi[sel] - phi[s_c].mean()
            dist[sel] = pc - (phi[s_c] - phi[s_c].mean()).min()
    D = np.full(n_all, np.inf)
    D[keep] = dist
    return {"distance": D, "t": t}


# ── NURBS(非一様有理 B スプライン)——重みつきで、制御点を通らない本物 ─────────────────────────── #
# 旧 ``contours_xld2.gen_contour_nurbs_xld`` は重みを持たず点を通す補間 B スプラインだった(名前と中身が違う)。
# ここでは Piegl & Tiller "The NURBS Book"(1997)の定義どおり: 節点列 U・次数 p・制御点 P_i・重み w_i で
#     C(u) = Σ N_{i,p}(u) w_i P_i / Σ N_{i,p}(u) w_i
# 門は「重み 1 なら scipy の B スプラインと一致」「9 点の 2 次 NURBS が円そのもの(半径誤差 1e-15)」
# 「射影変換と可換」「回転面が球・トーラスそのもの」。

def _clamped_knots(n_ctrl: int, p: int) -> np.ndarray:
    """両端を p+1 重にした一様節点列(端点で制御点を通る = clamped)。"""
    inner = n_ctrl - p - 1
    return np.concatenate([np.zeros(p + 1), np.arange(1, inner + 1) / (inner + 1), np.ones(p + 1)])


def _check_knots(U, n_ctrl: int, p: int) -> np.ndarray:
    U = np.asarray(U, dtype=np.float64).ravel()
    if U.size != n_ctrl + p + 1:
        raise ValueError(f"NURBS: 節点の数は 制御点数 + 次数 + 1 = {n_ctrl + p + 1}(渡されたのは {U.size})")
    if np.any(np.diff(U) < 0):
        raise ValueError("NURBS: 節点列は単調非減少")
    if U[p] >= U[n_ctrl]:
        raise ValueError("NURBS: 定義域 [U[p], U[n]] が空(節点が重なりすぎ)")
    return U


def _bspline_basis(U: np.ndarray, p: int, n_ctrl: int, u: np.ndarray) -> np.ndarray:
    """Cox–de Boor の漸化式で全基底 N_{i,p}(u) を (len(u), n_ctrl) で返す(右端 u = U[n] も含める)。"""
    u = np.asarray(u, dtype=np.float64)
    m = U.size - 1
    N = np.zeros((u.size, m))
    for i in range(m):
        N[:, i] = (U[i] <= u) & (u < U[i + 1])
    # 右端: 定義域の最後の空でない区間に入れる(半開区間だと u = U[n] で全基底が 0 になる)
    last = max(i for i in range(n_ctrl) if U[i] < U[i + 1])
    N[u >= U[n_ctrl], :] = 0.0
    N[u >= U[n_ctrl], last] = 1.0
    for k in range(1, p + 1):
        Nk = np.zeros((u.size, m - k))
        for i in range(m - k):
            d1, d2 = U[i + k] - U[i], U[i + k + 1] - U[i + 1]
            a = (u - U[i]) / d1 * N[:, i] if d1 > 0 else 0.0
            b = (U[i + k + 1] - u) / d2 * N[:, i + 1] if d2 > 0 else 0.0
            Nk[:, i] = a + b
        N = Nk
    return N[:, :n_ctrl]


def nurbs_curve(control_points, weights=None, *, degree: int = 3, knots=None, n: int = 200) -> dict:
    """NURBS 曲線を評価する(重みつき・制御点は一般に通らない)。

    Args:
        control_points: (m, d) の制御点(d = 2 なら平面、3 なら空間)。
        weights: 長さ m の正の重み。省略すると全部 1(= 普通の B スプライン)。重みを大きくすると曲線がその点に寄る。
        degree: 次数 p(m − 1 以下)。
        knots: 長さ m + p + 1 の節点列。省略すると両端 p+1 重の一様節点(端点だけは制御点を通る)。
        n: 評価する点の数(定義域を等分)。

    Returns:
        ``points`` (n, d) 曲線上の点、``u`` パラメータ、``basis`` (n, m) 有理基底 R_i(u)(各行の和は 1)、
        ``knots``・``weights``・``degree``。

    例: 9 点の 2 次 NURBS で円を **厳密に** 描く(``nurbs_circle`` が制御点・重み・節点を返す)。多項式の
    B スプラインでは円は近似しかできない —— 重みが要る理由がここにある。
    """
    P = np.asarray(control_points, dtype=np.float64)
    if P.ndim != 2 or P.shape[0] < 2 or P.shape[1] not in (2, 3):
        raise ValueError("nurbs_curve: 制御点は (m, 2) か (m, 3) で 2 個以上")
    m = P.shape[0]
    p = int(degree)
    if not 1 <= p <= m - 1:
        raise ValueError(f"nurbs_curve: 次数は 1〜{m - 1}(制御点 {m} 個)")
    w = np.ones(m) if weights is None else np.asarray(weights, dtype=np.float64).ravel()
    if w.size != m or np.any(~np.isfinite(w)) or np.any(w <= 0):
        raise ValueError("nurbs_curve: 重みは制御点と同じ数の正の有限値")
    U = _clamped_knots(m, p) if knots is None else _check_knots(knots, m, p)
    if int(n) < 2:
        raise ValueError("nurbs_curve: n は 2 以上")
    u = np.linspace(U[p], U[m], int(n))
    N = _bspline_basis(U, p, m, u)
    Nw = N * w[None, :]
    R = Nw / Nw.sum(axis=1, keepdims=True)
    return {"points": R @ P, "u": u, "basis": R, "knots": U, "weights": w, "degree": p}


def nurbs_circle(radius: float = 1.0, center=(0.0, 0.0)) -> dict:
    """円を厳密に表す 2 次 NURBS(Piegl & Tiller 例 7.1: 正方形の 4 隅と 4 辺の中点、隅の重みは 1/√2)。

    返す ``control_points``・``weights``・``knots``・``degree`` をそのまま ``nurbs_curve`` に渡すと、どの点も中心から
    ``radius`` の距離にある(丸め誤差まで)。隅の制御点は円の外 (√2 − 1)·radius の所にあり、曲線は通らない。
    """
    r = float(radius)
    if not (r > 0 and math.isfinite(r)):
        raise ValueError("nurbs_circle: 半径は正の有限値")
    c = np.asarray(center, dtype=np.float64).ravel()
    if c.size != 2:
        raise ValueError("nurbs_circle: 中心は (x, y)")
    sq = np.array([[1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1], [1, 0]], dtype=np.float64)
    h = 1.0 / math.sqrt(2.0)
    w = np.array([1, h, 1, h, 1, h, 1, h, 1], dtype=np.float64)
    U = np.array([0, 0, 0, .25, .25, .5, .5, .75, .75, 1, 1, 1], dtype=np.float64)
    return {"control_points": c + r * sq, "weights": w, "knots": U, "degree": 2}


def nurbs_surface(control_net, weights=None, *, degree=(3, 3), knots_u=None, knots_v=None, n=(48, 48)) -> dict:
    """NURBS 曲面(テンソル積)を評価する。

    Args:
        control_net: (mu, mv, 3) の制御網。
        weights: (mu, mv) の正の重み(省略で全部 1)。
        degree: (p, q)。
        knots_u, knots_v: 各方向の節点列(省略で clamped 一様)。
        n: (nu, nv) 評価点の格子。

    Returns:
        ``points`` (nu, nv, 3)、``mesh`` = (V, F) の三角形メッシュ(``geodesic_heat`` などにそのまま渡せる)、
        ``u``・``v``・``knots_u``・``knots_v``・``weights``。
    """
    P = np.asarray(control_net, dtype=np.float64)
    if P.ndim != 3 or P.shape[2] != 3 or P.shape[0] < 2 or P.shape[1] < 2:
        raise ValueError("nurbs_surface: 制御網は (mu, mv, 3) で各方向 2 個以上")
    mu, mv = P.shape[:2]
    p, q = (int(degree), int(degree)) if np.isscalar(degree) else (int(degree[0]), int(degree[1]))
    if not (1 <= p <= mu - 1 and 1 <= q <= mv - 1):
        raise ValueError(f"nurbs_surface: 次数は (1〜{mu - 1}, 1〜{mv - 1})")
    w = np.ones((mu, mv)) if weights is None else np.asarray(weights, dtype=np.float64)
    if w.shape != (mu, mv) or np.any(~np.isfinite(w)) or np.any(w <= 0):
        raise ValueError("nurbs_surface: 重みは (mu, mv) の正の有限値")
    Uu = _clamped_knots(mu, p) if knots_u is None else _check_knots(knots_u, mu, p)
    Uv = _clamped_knots(mv, q) if knots_v is None else _check_knots(knots_v, mv, q)
    nu, nv = (int(n), int(n)) if np.isscalar(n) else (int(n[0]), int(n[1]))
    if nu < 2 or nv < 2:
        raise ValueError("nurbs_surface: n は各方向 2 以上")
    u = np.linspace(Uu[p], Uu[mu], nu)
    v = np.linspace(Uv[q], Uv[mv], nv)
    Nu = _bspline_basis(Uu, p, mu, u)                              # (nu, mu)
    Nv = _bspline_basis(Uv, q, mv, v)                              # (nv, mv)
    num = np.einsum("ai,bj,ij,ijk->abk", Nu, Nv, w, P)
    den = np.einsum("ai,bj,ij->ab", Nu, Nv, w)
    S = num / den[..., None]
    ii, jj = np.meshgrid(np.arange(nu - 1), np.arange(nv - 1), indexing="ij")
    a = (ii * nv + jj).ravel()
    F = np.concatenate([np.column_stack([a, a + nv, a + 1]), np.column_stack([a + 1, a + nv, a + nv + 1])])
    return {"points": S, "mesh": (S.reshape(-1, 3), F), "u": u, "v": v, "knots_u": Uu, "knots_v": Uv, "weights": w}


def nurbs_revolve(profile, weights=None, *, degree: int = 2, knots=None, n=(48, 48)) -> dict:
    """平面の NURBS 曲線 (r, z) を z 軸のまわりに 1 周回した回転面(Piegl & Tiller §8.5)。

    断面の各制御点を ``nurbs_circle`` の 9 点で回し、重みを掛け合わせる。断面が厳密な円弧なら、出来る曲面も厳密な
    球・トーラス・円錐になる(多項式の曲面では近似しかできない)。

    Args:
        profile: (m, 2) の断面の制御点 (r, z)。r は軸からの距離(0 以上)。
        weights, degree, knots: 断面の NURBS(``nurbs_curve`` と同じ)。
        n: (周方向, 断面方向) の評価点数。

    Returns:
        ``nurbs_surface`` と同じ dict に ``control_net``・``net_weights`` を足したもの。
    """
    Q = np.asarray(profile, dtype=np.float64)
    if Q.ndim != 2 or Q.shape[1] != 2 or Q.shape[0] < 2:
        raise ValueError("nurbs_revolve: 断面は (m, 2) の (r, z)")
    if np.any(Q[:, 0] < 0):
        raise ValueError("nurbs_revolve: r(軸からの距離)は 0 以上")
    m = Q.shape[0]
    wq = np.ones(m) if weights is None else np.asarray(weights, dtype=np.float64).ravel()
    if wq.size != m or np.any(wq <= 0):
        raise ValueError("nurbs_revolve: 重みは断面の制御点と同じ数の正の値")
    circ = nurbs_circle(1.0)
    C, wc = circ["control_points"], circ["weights"]
    net = np.zeros((9, m, 3))
    net[:, :, 0] = C[:, 0][:, None] * Q[:, 0][None, :]
    net[:, :, 1] = C[:, 1][:, None] * Q[:, 0][None, :]
    net[:, :, 2] = Q[:, 1][None, :]
    W = wc[:, None] * wq[None, :]
    nn = (int(n), int(n)) if np.isscalar(n) else (int(n[0]), int(n[1]))
    out = nurbs_surface(net, W, degree=(2, int(degree)), knots_u=circ["knots"], knots_v=knots, n=nn)
    out["control_net"], out["net_weights"] = net, W
    return out
