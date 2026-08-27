"""外れ値に頑健な RANSAC プリミティブ適合(平面/球/直線/円筒)。

match3d.py の ``fit_*`` は全点の最小二乗(代数フィット)で、外れ値が数 % 混じると
法線や中心が引きずられる。ここでは RANSAC(RANdom SAmple Consensus)で

  1. 最小サンプル(平面 3 / 球 4 / 直線 2 / 円筒 2+法線)から仮説プリミティブを作り、
  2. 点-プリミティブ距離 < ``thresh`` の inlier 数を数え、
  3. inlier 最大の仮説を採用 → その inlier だけで最小二乗リフィット、

という手順で外れ値を排除する。numpy in / numpy out。各関数は
``(パラメータ dict, inlier_mask (N,) bool, info dict)`` を返す。

決定論: 乱数は ``np.random.default_rng(seed)`` のみを用い、``seed`` を固定すれば
サンプリング列が再現するので同一入力・同一 seed で結果はビット一致する。

info には少なくとも ``n_inliers`` / ``inlier_ratio`` / ``iters`` を含む。

制約(honest): RANSAC は確率的探索なので iters 不足だと最良仮説を引けず精度が落ちる。
縮退配置(平面サンプル 3 点が共線 / 球サンプル 4 点が同一平面 / 直線サンプル 2 点が同一)
の仮説は自動でスキップする。円筒は法線品質と軸推定の局所最適に敏感(法線が要る)。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "ransac_plane",
    "ransac_sphere",
    "ransac_line",
    "ransac_cylinder",
]


# ═══════════════════════════════════════════════════════════════════════════
# 内部ヘルパ
# ═══════════════════════════════════════════════════════════════════════════
def _unit(v):
    """単位ベクトル化(ゼロ割は 1e-12 でクリップ)。"""
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / (n if n > 1e-12 else 1e-12)


def _check_points(points, k, name):
    """(N,3) 検証と最小サンプル数チェック。返り値 = float 化した (N,3) 配列。"""
    P = np.asarray(points, float)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"{name}: points は (N,3) 形状が必要(得た shape={P.shape})")
    if len(P) < k:
        raise ValueError(f"{name}: 最小 {k} 点必要(得た N={len(P)})")
    return P


def _perp_basis(axis):
    """軸に直交する正規直交基底 (e1, e2) を作る。"""
    a = _unit(axis)
    t = np.array([1.0, 0.0, 0.0]) if abs(a[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = _unit(np.cross(a, t))
    e2 = np.cross(a, e1)
    return e1, e2


def _fit_plane_ls(P):
    """点群 → 最小二乗平面。返り (unit_normal, centroid)。法線=最小主軸。"""
    c = P.mean(0)
    w, v = np.linalg.eigh((P - c).T @ (P - c))
    return _unit(v[:, 0]), c


def _fit_sphere_ls(P):
    """点群 → 代数最小二乗球。返り (center(3,), radius)。coplanar 等で失敗時 None。"""
    A = np.hstack([2.0 * P, np.ones((len(P), 1))])
    b = (P ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    r2 = sol[3] + c @ c
    if not np.isfinite(r2) or r2 < 0:
        return None
    return c, float(np.sqrt(r2))


def _fit_line_ls(P):
    """点群 → 最小二乗直線。返り (centroid, unit_direction)。方向=最大主軸。"""
    c = P.mean(0)
    _, v = np.linalg.eigh((P - c).T @ (P - c))
    return c, _unit(v[:, -1])


def _fit_circle_2d(q):
    """2D 点 (M,2) → 代数最小二乗円。返り (center2d(2,), radius) or None。"""
    A = np.hstack([2.0 * q, np.ones((len(q), 1))])
    b = (q ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c2 = sol[:2]
    r2 = sol[2] + c2 @ c2
    if not np.isfinite(r2) or r2 < 0:
        return None
    return c2, float(np.sqrt(r2))


def _info(mask, iters, degenerate=False):
    """共通 info dict を組む。

    ``degenerate=True`` は「有効な RANSAC 仮説が得られず、フォールバック(全点 or
    法線 SVD)から params を作った」ことを示す honest フラグ。この場合でも
    ``n_inliers`` / ``inlier_ratio`` はフォールバック params の下で実際に
    ``dist < thresh`` を満たす点の実測値であり、縮退を満点(ratio=1.0)と詐称しない。"""
    n = int(mask.sum())
    return {"n_inliers": n, "inlier_ratio": float(n) / len(mask), "iters": int(iters),
            "n_points": int(len(mask)), "degenerate": bool(degenerate)}


# ═══════════════════════════════════════════════════════════════════════════
# 1. 平面(3 点サンプル)
# ═══════════════════════════════════════════════════════════════════════════
def ransac_plane(points, thresh, iters=500, seed=0):
    """外れ値に頑健な RANSAC 平面適合。

    3 点をサンプル → 平面法線(2 辺の外積)→ 点-平面距離 |n·(p-p0)| < ``thresh`` の
    inlier を最大化 → 最終 inlier で最小二乗リフィット(法線=共分散の最小主軸)。

    Args:
        points: (N,3) 点群。
        thresh: inlier とみなす点-平面距離のしきい値。
        iters: RANSAC 反復数。
        seed: 乱数シード(決定論)。

    Returns:
        (params, inlier_mask, info)。params = {"normal": (3,), "d": float, "point": (3,)}
        で平面は ``normal·x + d = 0``。inlier_mask=(N,) bool。
    """
    P = _check_points(points, 3, "ransac_plane")
    rng = np.random.default_rng(seed)
    N = len(P)

    best_mask = None
    best_n = -1
    for _ in range(iters):
        idx = rng.choice(N, size=3, replace=False)
        p0, p1, p2 = P[idx]
        n = np.cross(p1 - p0, p2 - p0)
        ln = np.linalg.norm(n)
        if ln < 1e-12:                       # 共線 → 縮退、スキップ
            continue
        n = n / ln
        dist = np.abs((P - p0) @ n)
        mask = dist < thresh
        cnt = int(mask.sum())
        if cnt > best_n:
            best_n, best_mask = cnt, mask

    fallback = best_mask is None or best_n < 3
    if fallback:                             # 有効仮説なし → 全点フォールバック
        best_mask = np.ones(N, bool)

    normal, point = _fit_plane_ls(P[best_mask])
    # リフィット法線で inlier を再判定(仮説より精度が上がる)
    dist = np.abs((P - point) @ normal)
    mask = dist < thresh
    if int(mask.sum()) >= 3:
        normal, point = _fit_plane_ls(P[mask])
    elif not fallback:
        # 実仮説はあったがリフィット後に縮退 → 実測 consensus(best_mask)を保持。
        mask = best_mask
    # フォールバック時は実測 mask(dist<thresh)を honest に返す。
    # 全点フォールバックの all-True mask を「満点(ratio=1.0)」と詐称しない。
    params = {"normal": normal, "d": float(-normal @ point), "point": point}
    return params, mask, _info(mask, iters, degenerate=fallback)


# ═══════════════════════════════════════════════════════════════════════════
# 2. 球(4 点サンプル)
# ═══════════════════════════════════════════════════════════════════════════
def ransac_sphere(points, thresh, iters=500, seed=0):
    """外れ値に頑健な RANSAC 球適合。

    4 点をサンプル → 線形法(代数フィット)で球中心・半径 → |‖p-c‖ - r| < ``thresh`` の
    inlier を最大化 → 最終 inlier で最小二乗リフィット。配管ボール/球面計測用。

    Args:
        points: (N,3) 点群。
        thresh: inlier とみなす |距離-r| のしきい値。
        iters: RANSAC 反復数。
        seed: 乱数シード(決定論)。

    Returns:
        (params, inlier_mask, info)。params = {"center": (3,), "radius": float}。
    """
    P = _check_points(points, 4, "ransac_sphere")
    rng = np.random.default_rng(seed)
    N = len(P)

    best_mask = None
    best_n = -1
    for _ in range(iters):
        idx = rng.choice(N, size=4, replace=False)
        fit = _fit_sphere_ls(P[idx])         # 4 点なら厳密解(coplanar は None)
        if fit is None:
            continue
        c, r = fit
        dist = np.abs(np.linalg.norm(P - c, axis=1) - r)
        mask = dist < thresh
        cnt = int(mask.sum())
        if cnt > best_n:
            best_n, best_mask = cnt, mask

    fallback = best_mask is None or best_n < 4
    if fallback:
        best_mask = np.ones(N, bool)

    fit = _fit_sphere_ls(P[best_mask])
    if fit is None:
        fit = _fit_sphere_ls(P)              # 最終フォールバック
        fallback = True
    if fit is None:
        raise ValueError("ransac_sphere: 球フィット不能(点が同一平面上など)")
    c, r = fit
    dist = np.abs(np.linalg.norm(P - c, axis=1) - r)
    mask = dist < thresh
    if int(mask.sum()) >= 4:
        fit2 = _fit_sphere_ls(P[mask])
        if fit2 is not None:
            c, r = fit2
    elif not fallback:
        # 実仮説はあったがリフィット後に縮退 → 実測 consensus(best_mask)を保持。
        mask = best_mask
    # フォールバック時は実測 mask を honest に返す(all-True の満点詐称をしない)。
    params = {"center": c, "radius": float(r)}
    return params, mask, _info(mask, iters, degenerate=fallback)


# ═══════════════════════════════════════════════════════════════════════════
# 3. 直線(2 点サンプル)
# ═══════════════════════════════════════════════════════════════════════════
def ransac_line(points, thresh, iters=300, seed=0):
    """外れ値に頑健な RANSAC 直線適合。

    2 点をサンプル → 直線(通過点 + 方向)→ 点-直線距離 ‖(p-p0)×d‖ < ``thresh`` の
    inlier を最大化 → 最終 inlier で最小二乗リフィット(方向=共分散の最大主軸)。

    Args:
        points: (N,3) 点群。
        thresh: inlier とみなす点-直線距離のしきい値。
        iters: RANSAC 反復数。
        seed: 乱数シード(決定論)。

    Returns:
        (params, inlier_mask, info)。params = {"point": (3,), "direction": (3,)}(単位方向)。
    """
    P = _check_points(points, 2, "ransac_line")
    rng = np.random.default_rng(seed)
    N = len(P)

    best_mask = None
    best_n = -1
    for _ in range(iters):
        idx = rng.choice(N, size=2, replace=False)
        p0, p1 = P[idx]
        d = p1 - p0
        ld = np.linalg.norm(d)
        if ld < 1e-12:                       # 同一点 → 縮退、スキップ
            continue
        d = d / ld
        dist = np.linalg.norm(np.cross(P - p0, d), axis=1)
        mask = dist < thresh
        cnt = int(mask.sum())
        if cnt > best_n:
            best_n, best_mask = cnt, mask

    fallback = best_mask is None or best_n < 2
    if fallback:
        best_mask = np.ones(N, bool)

    point, direction = _fit_line_ls(P[best_mask])
    dist = np.linalg.norm(np.cross(P - point, direction), axis=1)
    mask = dist < thresh
    if int(mask.sum()) >= 2:
        point, direction = _fit_line_ls(P[mask])
    elif not fallback:
        # 実仮説はあったがリフィット後に縮退 → 実測 consensus(best_mask)を保持。
        mask = best_mask
    # フォールバック時は実測 mask を honest に返す(all-True の満点詐称をしない)。
    params = {"point": point, "direction": direction}
    return params, mask, _info(mask, iters, degenerate=fallback)


# ═══════════════════════════════════════════════════════════════════════════
# 4. 円筒(2 点 + 法線サンプル)
# ═══════════════════════════════════════════════════════════════════════════
def ransac_cylinder(points, normals, thresh, iters=800, seed=0):
    """外れ値に頑健な RANSAC 円筒適合(点法線が必要)。

    円筒表面の法線は軸に直交するので、2 点の法線の外積で軸方向を推定 → 軸に直交な平面へ
    全点を投影 → その平面内で円をフィット → |投影距離 - r| < ``thresh`` の inlier を
    最大化。最終 inlier ではより頑健に軸を再推定(法線群の SVD の最小特異方向 = 軸)し、
    投影円を最小二乗リフィットする。法線が無ければ呼び出し側で estimate してから渡す。

    Args:
        points: (N,3) 点群。
        normals: (N,3) 各点の(単位)法線。
        thresh: inlier とみなす |投影距離-r| のしきい値。
        iters: RANSAC 反復数。
        seed: 乱数シード(決定論)。

    Returns:
        (params, inlier_mask, info)。params = {"axis": (3,) 単位軸, "point": (3,) 軸上の一点,
        "radius": float}。info には inlier 数 ``n_inliers`` / 比 ``inlier_ratio`` / ``iters``。
    """
    P = _check_points(points, 2, "ransac_cylinder")
    Nrm = np.asarray(normals, float)
    if Nrm.shape != P.shape:
        raise ValueError(f"ransac_cylinder: normals は points と同形状 (N,3) が必要"
                         f"(points={P.shape}, normals={Nrm.shape})")
    # 法線は単位化(未正規化でも安全に)
    Nn = Nrm / np.linalg.norm(Nrm, axis=1, keepdims=True).clip(1e-12)
    rng = np.random.default_rng(seed)
    N = len(P)

    def circle_refit(axis):
        """軸に直交な平面で「全投影点」に円を最小二乗フィットし (mask,axis,point3d,r)。
        外れ値を含む全点で円を張るのでリフィット/フォールバック専用(仮説評価には使わない)。"""
        e1, e2 = _perp_basis(axis)
        q = np.stack([P @ e1, P @ e2], 1)
        fit = _fit_circle_2d(q)
        if fit is None:
            return None
        c2, r = fit
        dist = np.abs(np.linalg.norm(q - c2, axis=1) - r)
        return dist < thresh, _unit(axis), c2[0] * e1 + c2[1] * e2, r

    best_mask = None
    best_n = -1
    best_axis = None
    for _ in range(iters):
        i, j = rng.choice(N, size=2, replace=False)
        axis = np.cross(Nn[i], Nn[j])
        la = np.linalg.norm(axis)
        if la < 1e-6:                        # 法線が平行 → 軸不定、スキップ
            continue
        axis = axis / la
        e1, e2 = _perp_basis(axis)
        # 仮説の円中心は「最小サンプルのみ」から決める(外れ値で仮説を汚さない):
        # 2 点を投影平面に落とし、各点の投影法線が張る 2 直線の交点 = 中心。
        qi = np.array([P[i] @ e1, P[i] @ e2]); qj = np.array([P[j] @ e1, P[j] @ e2])
        mi = np.array([Nn[i] @ e1, Nn[i] @ e2]); mj = np.array([Nn[j] @ e1, Nn[j] @ e2])
        lmi = np.linalg.norm(mi); lmj = np.linalg.norm(mj)
        if lmi < 1e-9 or lmj < 1e-9:         # 法線が軸とほぼ平行 → 投影が消える、スキップ
            continue
        mi /= lmi; mj /= lmj
        A2 = np.array([[mi[0], -mj[0]], [mi[1], -mj[1]]])
        if abs(np.linalg.det(A2)) < 1e-9:    # 2 法線が投影平面で平行 → 交点不定、スキップ
            continue
        t = np.linalg.solve(A2, qj - qi)
        center2d = qi + t[0] * mi
        r = 0.5 * (abs(t[0]) + abs(t[1]))
        if not np.isfinite(r) or r <= 1e-9:
            continue
        q_all = np.stack([P @ e1, P @ e2], 1)
        dist = np.abs(np.linalg.norm(q_all - center2d, axis=1) - r)
        mask = dist < thresh
        cnt = int(mask.sum())
        if cnt > best_n:
            best_n, best_mask, best_axis = cnt, mask, axis

    fallback = best_mask is None or best_n < 2
    if best_mask is None:                    # 有効仮説なし → 法線 SVD で全点フォールバック
        _, _, vt = np.linalg.svd(Nn, full_matrices=False)
        best_axis = vt[-1]
        res = circle_refit(best_axis)
        if res is None:
            raise ValueError("ransac_cylinder: 円筒フィット不能(投影円が縮退)")
        best_mask = res[0]

    # リフィット: inlier 法線から軸を頑健再推定(法線 ⟂ 軸 → 最小特異方向)
    n_in = Nn[best_mask]
    if len(n_in) >= 2:
        _, _, vt = np.linalg.svd(n_in, full_matrices=False)
        axis = vt[-1]
        # 仮説軸と符号/向きが大きくずれたら仮説軸を優先(SVD 縮退保険)
        if abs(axis @ best_axis) < 0.5:
            axis = best_axis
    else:
        axis = best_axis
    axis = _unit(axis)

    # 円のリフィットは「inlier だけ」で行う(外れ値で中心/半径を汚さない)。
    # 全点で fit すると外れ値バイアスが戻るので circle_refit(全点)は使わない。
    e1, e2 = _perp_basis(axis)
    q_all = np.stack([P @ e1, P @ e2], 1)
    fit = _fit_circle_2d(q_all[best_mask])
    if fit is None:                          # 縮退時は全点フォールバック
        res = circle_refit(axis)
        mask, axis, point3d, r = res
    else:
        c2, r = fit
        point3d = c2[0] * e1 + c2[1] * e2
        dist = np.abs(np.linalg.norm(q_all - c2, axis=1) - r)
        mask = dist < thresh
        # 更新後 inlier でもう一度だけ収束(1 回)
        if int(mask.sum()) >= 3:
            fit2 = _fit_circle_2d(q_all[mask])
            if fit2 is not None:
                c2, r = fit2
                point3d = c2[0] * e1 + c2[1] * e2
                dist = np.abs(np.linalg.norm(q_all - c2, axis=1) - r)
                mask = dist < thresh
    params = {"axis": _unit(axis), "point": point3d, "radius": float(r)}
    return params, mask, _info(mask, iters)
