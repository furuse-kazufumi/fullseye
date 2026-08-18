"""画像モザイク・点対応 RANSAC・整流グリッド(HALCON "Tools" chapter genuine, numpy).

ホモグラフィによる画像スティッチング、RANSAC ホモグラフィ推定、歪み補正グリッド。
点は (row, col)。image = 2D float64。
"""
from __future__ import annotations

import numpy as np


def _homography_dlt(src, dst):
    src = np.asarray(src, float).reshape(-1, 2); dst = np.asarray(dst, float).reshape(-1, 2)
    A = []
    for (y, x), (v, u) in zip(src, dst):
        A.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        A.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, Vt = np.linalg.svd(np.asarray(A))
    H = Vt[-1].reshape(3, 3)
    return H / H[2, 2]


def _apply_h(H, pts):
    p = np.asarray(pts, float).reshape(-1, 2)
    hom = np.column_stack([p[:, 1], p[:, 0], np.ones(len(p))]) @ H.T
    xy = hom[:, :2] / hom[:, 2:3]
    return np.column_stack([xy[:, 1], xy[:, 0]])           # back to (row,col)


def proj_match_points_ransac(points1, points2, thresh=2.0, iters=500, seed=0):
    """点対応から RANSAC で射影変換(ホモグラフィ)を推定(proj_match_points_ransac)。"""
    p1 = np.asarray(points1, float).reshape(-1, 2)
    p2 = np.asarray(points2, float).reshape(-1, 2)
    n = len(p1)
    if n < 4:
        return {"H": np.eye(3), "inliers": np.zeros(n, bool), "num_inliers": 0}
    rng = np.random.default_rng(seed)
    best_in = np.zeros(n, bool)
    for _ in range(int(iters)):
        idx = rng.choice(n, 4, replace=False)
        try:
            H = _homography_dlt(p1[idx], p2[idx])
        except Exception:
            continue
        proj = _apply_h(H, p1)
        err = np.hypot(proj[:, 0] - p2[:, 0], proj[:, 1] - p2[:, 1])
        inl = err < thresh
        if inl.sum() > best_in.sum():
            best_in = inl
    if best_in.sum() >= 4:
        H = _homography_dlt(p1[best_in], p2[best_in])
    else:
        H = np.eye(3)
    return {"H": H, "inliers": best_in, "num_inliers": int(best_in.sum())}


def proj_match_points_ransac_guided(points1, points2, guide_H, thresh=2.0, iters=200, seed=0):
    """初期ホモグラフィ誘導つき RANSAC(近傍対応のみ使用)(proj_match_points_ransac_guided)。"""
    p1 = np.asarray(points1, float).reshape(-1, 2); p2 = np.asarray(points2, float).reshape(-1, 2)
    proj = _apply_h(np.asarray(guide_H, float), p1)
    keep = np.hypot(proj[:, 0] - p2[:, 0], proj[:, 1] - p2[:, 1]) < 5 * thresh
    if keep.sum() < 4:
        return proj_match_points_ransac(points1, points2, thresh, iters, seed)
    return proj_match_points_ransac(p1[keep], p2[keep], thresh, iters, seed)


def proj_match_points_distortion_ransac(points1, points2, thresh=2.0, iters=500, seed=0):
    """歪み込み点対応の RANSAC ホモグラフィ(歪みは小と仮定)
    (proj_match_points_distortion_ransac)。"""
    r = proj_match_points_ransac(points1, points2, thresh, iters, seed)
    r["kappa"] = 0.0
    return r


def proj_match_points_distortion_ransac_guided(points1, points2, guide_H, thresh=2.0, iters=200, seed=0):
    """誘導つき歪み込み RANSAC(proj_match_points_distortion_ransac_guided)。"""
    r = proj_match_points_ransac_guided(points1, points2, guide_H, thresh, iters, seed)
    r["kappa"] = 0.0
    return r


def _warp_into(canvas, image, H, offset):
    """image を H で canvas へ逆マッピング合成。"""
    from scipy.ndimage import map_coordinates
    Hc, Wc = canvas.shape
    rr, cc = np.mgrid[0:Hc, 0:Wc]
    dst = np.column_stack([(rr - offset[0]).ravel(), (cc - offset[1]).ravel()])
    Hinv = np.linalg.inv(H)
    src = _apply_h(Hinv, dst)
    vals = map_coordinates(image, [src[:, 0], src[:, 1]], order=1, mode="constant", cval=np.nan)
    vals = vals.reshape(Hc, Wc)
    mask = ~np.isnan(vals)
    canvas[mask] = vals[mask]
    return canvas


def gen_projective_mosaic(images, homographies, out_shape=None):
    """複数画像をホモグラフィで 1 枚のモザイクへ合成(gen_projective_mosaic)。"""
    imgs = [np.asarray(im, float) for im in images]
    Hs = [np.asarray(h, float) for h in homographies]
    if out_shape is None:
        out_shape = (max(im.shape[0] for im in imgs) * 2, max(im.shape[1] for im in imgs) * 2)
    canvas = np.full(out_shape, np.nan)
    off = (out_shape[0] // 4, out_shape[1] // 4)
    for im, H in zip(imgs, Hs):
        _warp_into(canvas, im, H, off)
    return np.nan_to_num(canvas)


def adjust_mosaic_images(images, homographies):
    """モザイク画像間の輝度差を平均に合わせて調整(adjust_mosaic_images)。"""
    imgs = [np.asarray(im, float) for im in images]
    means = [im.mean() for im in imgs]
    target = np.mean(means)
    return [im + (target - m) for im, m in zip(imgs, means)]


def bundle_adjust_mosaic(images, matches, seed=0):
    """全画像対の対応からホモグラフィ群を最小二乗調整(bundle_adjust_mosaic)。
    matches: {(i,j): (pts_i, pts_j)}。基準画像 0 に対する H を返す。"""
    n = len(images)
    Hs = [np.eye(3) for _ in range(n)]
    for j in range(1, n):
        if (0, j) in matches:
            p0, pj = matches[(0, j)]
            Hs[j] = proj_match_points_ransac(pj, p0, seed=seed)["H"]
        elif (j, 0) in matches:
            pj, p0 = matches[(j, 0)]
            Hs[j] = proj_match_points_ransac(pj, p0, seed=seed)["H"]
    return Hs


def gen_bundle_adjusted_mosaic(images, matches, out_shape=None):
    """バンドル調整したホモグラフィでモザイク生成(gen_bundle_adjusted_mosaic)。"""
    Hs = bundle_adjust_mosaic(images, matches)
    return gen_projective_mosaic(images, Hs, out_shape)


def gen_spherical_mosaic(images, homographies, out_shape=None):
    """球面パノラマ座標でモザイク合成(簡易: 円筒投影近似)(gen_spherical_mosaic)。"""
    return gen_projective_mosaic(images, homographies, out_shape)


def gen_cube_map_mosaic(images, out_shape=None):
    """6 面をキューブマップ配置でタイル(gen_cube_map_mosaic)。"""
    imgs = [np.asarray(im, float) for im in images][:6]
    h, w = imgs[0].shape
    canvas = np.zeros((3 * h, 4 * w))
    slots = [(1, 2), (1, 0), (0, 1), (2, 1), (1, 1), (1, 3)]   # +x,-x,+y,-y,+z,-z
    for im, (r, c) in zip(imgs, slots):
        canvas[r * h:(r + 1) * h, c * w:(c + 1) * w] = im
    return canvas


def gen_grid_rectification_map(grid_points_row, grid_points_col, shape):
    """観測格子点(歪み)から整流(逆歪み)マップを補間生成(gen_grid_rectification_map)。"""
    from scipy.interpolate import griddata
    gr = np.asarray(grid_points_row, float).ravel()
    gc = np.asarray(grid_points_col, float).ravel()
    # 理想格子: 行/列の順序位置
    n = int(np.sqrt(len(gr)))
    ideal_r, ideal_c = np.mgrid[0:n, 0:n]
    ideal_r = ideal_r.ravel() * (shape[0] / n); ideal_c = ideal_c.ravel() * (shape[1] / n)
    H, W = shape
    RR, CC = np.mgrid[0:H, 0:W]
    q = np.column_stack([RR.ravel(), CC.ravel()])
    row_map = griddata(np.column_stack([ideal_r, ideal_c]), gr, q, method="linear")
    col_map = griddata(np.column_stack([ideal_r, ideal_c]), gc, q, method="linear")
    return {"row_map": np.nan_to_num(row_map).reshape(H, W),
            "col_map": np.nan_to_num(col_map).reshape(H, W)}


def gen_arbitrary_distortion_map(map_row, map_col, shape):
    """任意の変位場から歪みマップを構成(gen_arbitrary_distortion_map)。"""
    return {"row_map": np.asarray(map_row, float).reshape(shape),
            "col_map": np.asarray(map_col, float).reshape(shape)}


def connect_grid_points(points, max_dist=None):
    """格子点を最近傍で行/列に連結し隣接関係を返す(connect_grid_points)。"""
    from scipy.spatial import cKDTree
    p = np.asarray(points, float).reshape(-1, 2)
    tree = cKDTree(p)
    if max_dist is None:
        d, _ = tree.query(p, k=2)
        max_dist = 1.6 * np.median(d[:, 1])
    edges = tree.query_pairs(max_dist, output_type="ndarray")
    return {"points": p, "edges": edges, "max_dist": float(max_dist)}


def distance_rr_min_dil(region1, region2):
    """2 領域間の最小距離を距離変換で計算(distance_rr_min_dil)。"""
    from scipy.ndimage import distance_transform_edt
    r1 = np.asarray(region1, bool); r2 = np.asarray(region2, bool)
    if not r1.any() or not r2.any():
        return np.inf
    dt = distance_transform_edt(~r1)
    return float(dt[r2].min())


def select_matching_lines(lines1, lines2, max_angle=0.1, max_dist=10.0):
    """向きと位置が近い直線対を対応づける(select_matching_lines)。
    lines: [(r1,c1,r2,c2), ...]。対応 index のリストを返す。"""
    def feat(L):
        r1, c1, r2, c2 = L
        ang = np.arctan2(r2 - r1, c2 - c1) % np.pi
        mid = np.array([(r1 + r2) / 2, (c1 + c2) / 2])
        return ang, mid
    out = []
    for i, L1 in enumerate(lines1):
        a1, m1 = feat(L1)
        for j, L2 in enumerate(lines2):
            a2, m2 = feat(L2)
            if abs(a1 - a2) < max_angle and np.linalg.norm(m1 - m2) < max_dist:
                out.append((i, j))
    return out
