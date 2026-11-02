# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mvstereo —— 平行化ステレオの視差と距離、円の像からの 3-D 姿勢。

``binocular_disparity_ms`` は ``stereo.disparity_sgm`` の整数視差に、左右一致の検査と
SAD の放物線による小数の補間を足す。``get_circle_pose`` は楕円の像が作る錐から円の中心と
法線を閉形式で求める。解は 2 つあり、1 枚の像からは区別できないので両方返す。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

import stereo


def _pair(left, right, op):
    L = np.asarray(left, dtype=np.float64)
    R = np.asarray(right, dtype=np.float64)
    if L.size == 0 or R.size == 0:
        raise ValueError("%s: left/right are empty — pass at least one pixel" % op)
    if L.ndim != 2 or L.shape != R.shape:
        raise ValueError("%s: left/right must be equal-shape 2-D arrays" % op)
    if not (np.isfinite(L).all() and np.isfinite(R).all()):
        raise ValueError("%s: left/right have NaN/inf pixels" % op)
    return L, R


def _sad_volume(L, R, max_disp, window):
    """窓 SAD のコスト体積 (D+1, H, W)。参照できない列は inf。"""
    H, W = L.shape
    vol = np.full((max_disp + 1, H, W), np.inf)
    for d in range(max_disp + 1):
        diff = np.abs(L[:, d:] - R[:, :W - d])
        vol[d, :, d:] = ndimage.uniform_filter(diff, size=int(window), mode="nearest")
    return vol


def binocular_disparity_ms(left, right, max_disp=32, window=5, P1=5.0, P2=50.0, paths=4,
                           lr_tolerance=1.0):
    """平行化ステレオの視差を半大域マッチングで求め、左右一致で検査して小数へ補間する。

    左基準と右基準の視差を ``stereo.disparity_sgm`` で 1 回ずつ計算し、対応点で
    ``lr_tolerance`` より食い違う画素と参照できない左端の列を無効にする。残りの画素は SAD の
    3 点放物線で小数の視差へ補間する。無効の画素は ``disparity`` が NaN になる。
    空の入力(``left`` が 0 要素)は ValueError。

    Args:
        left: 左の画像 (H, W)。視差はこの画像を基準にする。
        right: 右の画像 (H, W)。
        max_disp: 探す視差の上限(画素、>= 1)。
        window: census と SAD の窓(奇数)。
        P1: 視差 1 の段差の罰則。
        P2: 視差 2 以上の段差の罰則。
        paths: 集約の方向数(2 / 4)。
        lr_tolerance: 左右一致の許容差(画素)。

    Returns:
        ``disparity``(float、無効は NaN)、``valid``(bool)、``score``(0..1、大きいほど
        コストの谷が深い)を持つ dict。

    出典: H. Hirschmüller, IEEE Trans. PAMI 30(2), 328-341 (2008), doi:10.1109/TPAMI.2007.1166。
    """
    op = "binocular_disparity_ms"
    L, R = _pair(left, right, op)
    D, win = int(max_disp), int(window)
    if D < 1 or win < 1 or win % 2 == 0:
        raise ValueError("%s: max_disp must be >= 1 and window a positive odd number" % op)
    if not np.isfinite(float(lr_tolerance)) or float(lr_tolerance) < 0:
        raise ValueError("%s: lr_tolerance must be finite and non-negative" % op)
    H, W = L.shape
    if W <= D:
        raise ValueError("%s: the image width %d must exceed max_disp %d" % (op, W, D))
    dl = stereo.disparity_sgm(L, R, max_disp=D, window=win, P1=P1, P2=P2, paths=paths)
    dr = stereo.disparity_sgm(R[:, ::-1], L[:, ::-1], max_disp=D, window=win, P1=P1, P2=P2,
                              paths=paths)[:, ::-1]
    dl = np.asarray(dl, dtype=np.float64)
    di = np.clip(np.rint(np.nan_to_num(dl, nan=0.0)).astype(int), 0, D)
    rr, cc = np.mgrid[0:H, 0:W]
    target = cc - di
    inside = target >= 0
    valid = np.isfinite(dl) & inside
    back = np.abs(di - np.asarray(dr, dtype=np.float64)[rr, np.clip(target, 0, W - 1)])
    valid &= back <= float(lr_tolerance)
    vol = _sad_volume(L, R, D, win)
    c0 = vol[di, rr, cc]
    cm = vol[np.clip(di - 1, 0, D), rr, cc]
    cp = vol[np.clip(di + 1, 0, D), rr, cc]
    with np.errstate(invalid="ignore"):                  # 左端の列は inf - inf になる
        denom = cm - 2.0 * c0 + cp
    ok = np.isfinite(denom) & (denom > 1e-12) & (di > 0) & (di < D)
    delta = np.zeros((H, W))
    delta[ok] = np.clip((cm[ok] - cp[ok]) / (2.0 * denom[ok]), -0.5, 0.5)
    disparity = np.where(valid, di + delta, np.nan)
    finite = np.where(np.isfinite(vol), vol, np.nan)
    with np.errstate(invalid="ignore"):
        mean_cost = np.nanmean(finite, axis=0) if finite.size else np.zeros((H, W))
    mean_cost = np.where(np.isfinite(mean_cost), mean_cost, 0.0)
    score = np.where(mean_cost > 1e-12, np.clip(1.0 - np.nan_to_num(c0, posinf=1e9) / np.maximum(mean_cost, 1e-12), 0, 1), 0.0)
    return {"disparity": disparity, "valid": valid, "score": np.where(valid, score, 0.0)}


def binocular_distance_ms(left, right, focal, baseline, doffs=0.0, max_disp=32, window=5,
                          P1=5.0, P2=50.0, paths=4, lr_tolerance=1.0):
    """平行化ステレオの距離画像を求める(``Z = focal * baseline / (disparity + doffs)``)。

    視差は :func:`binocular_disparity_ms` の値をそのまま使う。無効の画素と、視差が 0 以下で
    距離の決まらない画素は ``distance`` が NaN になる。
    空の入力(``left`` が 0 要素)は ValueError。

    Args:
        left: 左の画像 (H, W)。
        right: 右の画像 (H, W)。
        focal: 焦点距離(画素、> 0)。
        baseline: 基線長(距離の単位がこの単位になる、> 0)。
        doffs: 主点の差 ``cx_right - cx_left``(画素)。
        max_disp: 探す視差の上限。
        window: census と SAD の窓(奇数)。
        P1: 視差 1 の段差の罰則。
        P2: 視差 2 以上の段差の罰則。
        paths: 集約の方向数(2 / 4)。
        lr_tolerance: 左右一致の許容差(画素)。

    Returns:
        ``distance``(無効は NaN)、``disparity``、``valid``、``score`` を持つ dict。
    """
    op = "binocular_distance_ms"
    f, b, off = float(focal), float(baseline), float(doffs)
    if not np.isfinite([f, b, off]).all() or f <= 0 or b <= 0:
        raise ValueError("%s: focal and baseline must be positive and finite" % op)
    res = binocular_disparity_ms(left, right, max_disp=max_disp, window=window, P1=P1, P2=P2,
                                 paths=paths, lr_tolerance=lr_tolerance)
    d = res["disparity"] + off
    usable = res["valid"] & (d > 1e-9)
    distance = np.full(d.shape, np.nan)
    distance[usable] = f * b / d[usable]
    return {"distance": distance, "disparity": res["disparity"], "valid": usable,
            "score": np.where(usable, res["score"], 0.0)}


def _fit_conic(x, y):
    """正規化した点に一般の円錐曲線を当てはめ、3x3 の対称行列を返す。"""
    A = np.column_stack([x * x, x * y, y * y, x, y, np.ones_like(x)])
    scale = np.linalg.norm(A, axis=0)
    _, _, Vt = np.linalg.svd(A / np.where(scale > 0, scale, 1.0), full_matrices=False)
    a, b, c, d, e, f = Vt[-1] / np.where(scale > 0, scale, 1.0)
    return np.array([[a, b / 2.0, d / 2.0], [b / 2.0, c, e / 2.0], [d / 2.0, e / 2.0, f]])


def _ray_residual(x, y, center, normal, radius):
    """視線を円の平面へ当て、円周からの距離(世界の単位)を点ごとに返す。"""
    rays = np.column_stack([x, y, np.ones_like(x)])
    s = (normal @ center) / (rays @ normal)
    hit = rays * s[:, None]
    return np.linalg.norm(hit - center, axis=1) - radius


def get_circle_pose(contour, radius, cam_par):
    """既知の半径の円の像(楕円の点列)から、円の中心と法線をカメラ座標で求める。

    点列に円錐曲線を当てはめ、視線の錐の固有分解から 3-D の円を閉形式で求める。解は鏡像の
    2 つで、1 枚の像からは区別できないので両方を、再投影の誤差つきで返す。正面視では 2 解が
    重なる。歪みは扱わない(歪みのある点列は先に戻す)。
    空の入力(``contour`` が 0 要素)は ValueError。

    Args:
        contour: (N, 2) の ``(row, col)``(N >= 5)。
        radius: 円の半径(> 0)。返す中心の単位がこの単位になる。
        cam_par: ``fx`` / ``fy`` / ``cx`` / ``cy`` の dict。

    Returns:
        ``center`` (2, 3)、``normal`` (2, 3)(カメラへ向く単位ベクトル)、``rms_px`` (2,) の dict。

    出典: Y. C. Shiu and S. Ahmad, IEEE Trans. Robot. Autom. 5(1), 16-29 (1989);
    Q. Chen, H. Wu, T. Wada, Proc. ECCV 2004, LNCS 3021, 302-315。
    """
    op = "get_circle_pose"
    p = np.asarray(contour, dtype=np.float64)
    if p.size == 0:
        raise ValueError("%s: contour is empty — pass at least 5 points" % op)
    if p.ndim != 2 or p.shape[1] != 2 or p.shape[0] < 5 or not np.isfinite(p).all():
        raise ValueError("%s: contour must be a finite (N, 2) array with N >= 5" % op)
    r = float(radius)
    if not np.isfinite(r) or r <= 0:
        raise ValueError("%s: radius must be positive and finite" % op)
    try:
        fx, fy, cx, cy = (float(cam_par[k]) for k in ("fx", "fy", "cx", "cy"))
    except (KeyError, TypeError) as exc:
        raise ValueError("%s: cam_par must hold fx/fy/cx/cy" % op) from exc
    if fx <= 0 or fy <= 0:
        raise ValueError("%s: fx and fy must be positive" % op)
    x, y = (p[:, 1] - cx) / fx, (p[:, 0] - cy) / fy
    Q = _fit_conic(x, y)
    w, V = np.linalg.eigh(Q)
    if np.sum(w > 0) == 1:           # 正 2 つ・負 1 つへ符号をそろえる
        w, V = -w, V
    order = np.argsort(-w)
    w, V = w[order], V[:, order]
    l1, l2, l3 = w
    if not (l2 > 1e-9 * l1 and l3 < -1e-9 * l1) or Q[0, 0] * Q[1, 1] - Q[0, 1] ** 2 <= 0:
        raise ValueError("%s: the points do not form an ellipse in view" % op)
    a = np.sqrt(max(l1 - l2, 0.0) / (l1 - l3))
    b = np.sqrt(max(l2 - l3, 0.0) / (l1 - l3))
    candidates = []
    for s1 in (1.0, -1.0):
        for s2 in (1.0, -1.0):
            for s3 in (1.0, -1.0):
                z0 = s3 * l2 * r / np.sqrt(-l1 * l3)
                c = z0 * V @ np.array([s2 * (l3 / l2) * a, 0.0, -s1 * (l1 / l2) * b])
                n = V @ np.array([s2 * a, 0.0, -s1 * b])
                if c[2] <= 0:
                    continue
                n = n / np.linalg.norm(n)
                if n @ c > 0:
                    n = -n
                d = _ray_residual(x, y, c, n, r) * 0.5 * (fx + fy) / c[2]
                candidates.append((float(np.sqrt(np.mean(d * d))), c, n))
    candidates.sort(key=lambda t: t[0])
    picked = []
    for cand in candidates:
        if all(np.linalg.norm(cand[2] - q[2]) > 1e-9 or np.linalg.norm(cand[1] - q[1]) > 1e-9
               for q in picked):
            picked.append(cand)
        if len(picked) == 2:
            break
    if not picked:
        raise ValueError("%s: no solution in front of the camera" % op)
    if len(picked) == 1:
        picked.append(picked[0])
    return {"center": np.array([q[1] for q in picked]), "normal": np.array([q[2] for q in picked]),
            "rms_px": np.array([q[0] for q in picked])}
