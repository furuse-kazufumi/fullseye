# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mvimage —— 画像の幾何変換と注目点: 写像の適用・平面への平行化・歪みの変換・Lepetit 点。

全部 numpy / scipy だけで動く。実装は公開の教科書と論文の数式から起こした。出典は各関数の
docstring に書く。比較で測っていない優劣は書かない。

写像表(``row_map`` / ``col_map``)の向きは ``calib.gen_radial_distortion_map`` と同じで、
**出力の画素 → 入力の座標**。出力の画素を順に埋めるための逆写像なので穴が開かない。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _image2d(image, op):
    """2-D の有限な float 画像を返す。空・形違い・非有限は ValueError。"""
    a = np.asarray(image, dtype=np.float64)
    if a.size == 0:
        raise ValueError("%s: image is empty — pass at least one pixel" % op)
    if a.ndim != 2:
        raise ValueError("%s: image must be 2-D, got shape %r" % (op, a.shape))
    if not np.isfinite(a).all():
        raise ValueError("%s: image has NaN/inf pixels" % op)
    return a


def _cam(cam_par, op):
    """``{fx, fy, cx, cy[, kappa]}`` を検査して float の組で返す。"""
    if not isinstance(cam_par, dict):
        raise ValueError("%s: cam_par must be a dict with fx/fy/cx/cy" % op)
    missing = [k for k in ("fx", "fy", "cx", "cy") if k not in cam_par]
    if missing:
        raise ValueError("%s: cam_par lacks %s" % (op, ", ".join(missing)))
    vals = [float(cam_par[k]) for k in ("fx", "fy", "cx", "cy")]
    kappa = float(cam_par.get("kappa", 0.0))
    if not np.isfinite(vals + [kappa]).all() or vals[0] <= 0 or vals[1] <= 0:
        raise ValueError("%s: cam_par must be finite with fx, fy > 0" % op)
    return vals[0], vals[1], vals[2], vals[3], kappa


def distort_division(x, y, kappa):
    """歪みのない座標を除算モデルで歪ませる(主点からの画素、``undistort_division`` の逆)。

    除算モデル ``u = d / (1 + kappa |d|^2)`` を ``d`` について解いた閉形式
    ``d = 2 u / (1 + sqrt(1 - 4 kappa |u|^2))``。根号の中が負になる座標は像を持たず NaN を返す。
    出典: R. Lenz and D. Fritsch, ISPRS J. Photogramm. Remote Sens. 45(2), 90-110 (1990)。
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    disc = 1.0 - 4.0 * float(kappa) * (x * x + y * y)
    root = np.where(disc >= 0.0, np.sqrt(np.maximum(disc, 0.0)), np.nan)
    f = 2.0 / (1.0 + root)
    return x * f, y * f


def undistort_division(x, y, kappa):
    """歪んだ座標を除算モデルで戻す(``u = d / (1 + kappa |d|^2)``)。"""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    f = 1.0 / (1.0 + float(kappa) * (x * x + y * y))
    return x * f, y * f


def _sample(im, row, col, fill):
    """線形補間で読む。端の画素へ丸め屑ぶんはみ出した座標は内側へ戻す(1e-9 画素より細かい差を
    「画像の外」と数えると、恒等の写像で右端と下端の列が ``fill`` に化ける)。"""
    H, W = im.shape
    row = np.where(np.abs(row - (H - 1)) < 1e-9, H - 1.0, np.where(np.abs(row) < 1e-9, 0.0, row))
    col = np.where(np.abs(col - (W - 1)) < 1e-9, W - 1.0, np.where(np.abs(col) < 1e-9, 0.0, col))
    return ndimage.map_coordinates(im, [row, col], order=1, mode="constant", cval=float(fill))


def map_image(image, image_map, fill=0.0):
    """逆写像表を画像へ適用して再標本化する(出力の画素ごとに入力の座標を読む)。

    ``image_map`` は ``row_map`` / ``col_map`` の dict(``gen_radial_distortion_map`` の返りを
    そのまま渡せる)。線形補間で読み、画像の外は ``fill`` で埋める。``image_map`` に写像の鍵が
    無い(``x_map`` / ``y_map`` は画素 → ワールドの順写像で、このままでは穴が開く)と ValueError。
    空の入力(``image`` が 0 要素)は ValueError。

    Args:
        image: (H, W) の画像。
        image_map: ``row_map`` と ``col_map`` を持つ dict。形が出力の形になる。
        fill: 入力の外を読んだ画素の値。

    Returns:
        ``image_map`` と同じ形の float 画像。
    """
    op = "map_image"
    im = _image2d(image, op)
    if not isinstance(image_map, dict) or "row_map" not in image_map or "col_map" not in image_map:
        raise ValueError("%s: image_map must hold row_map and col_map (output pixel -> input "
                         "coordinate); x_map/y_map are the forward direction" % op)
    rm = np.asarray(image_map["row_map"], dtype=np.float64)
    cm = np.asarray(image_map["col_map"], dtype=np.float64)
    if rm.shape != cm.shape or rm.ndim != 2 or rm.size == 0:
        raise ValueError("%s: row_map/col_map must be equal-shape 2-D arrays" % op)
    if not (np.isfinite(rm).all() and np.isfinite(cm).all()):
        raise ValueError("%s: the map has NaN/inf entries" % op)
    return _sample(im, rm, cm, fill)


def rectify_to_world_plane(image, cam_par, pose, width, height, scale, origin=(0.0, 0.0), fill=0.0):
    """画像をワールド平面 z=0 の正面図へ平行化する(1 画素 = ``scale`` のワールド単位)。

    世界の点 ``(x, y, 0)`` を ``pose``(ワールド → カメラの 4x4)で写し、ピンホール投影と
    除算モデルの歪み(``cam_par`` に ``kappa`` があるとき)を通して入力の座標を求める。
    出力の行は y、列は x に沿う。``origin`` は出力の (0, 0) に当たる世界の ``(x, y)``。
    カメラの後ろへ落ちる画素は ``fill``。空の入力(``image`` が 0 要素)は ValueError。

    Args:
        image: (H, W) の画像。
        cam_par: ``fx`` / ``fy`` / ``cx`` / ``cy``(と任意で ``kappa``)の dict。
        pose: 4x4 の同次変換(ワールド → カメラ)。
        width: 出力の列数。
        height: 出力の行数。
        scale: 1 画素あたりのワールド単位(> 0)。
        origin: 出力の左上の画素が指す世界の ``(x, y)``。
        fill: 入力の外とカメラの後ろの画素の値。

    Returns:
        (height, width) の float 画像。

    出典: R. Hartley and A. Zisserman, Multiple View Geometry, 2nd ed., ch. 2 (平面の射影変換)。
    """
    op = "rectify_to_world_plane"
    im = _image2d(image, op)
    fx, fy, cx, cy, kappa = _cam(cam_par, op)
    T = np.asarray(pose, dtype=np.float64)
    if T.shape != (4, 4) or not np.isfinite(T).all():
        raise ValueError("%s: pose must be a finite 4x4 matrix" % op)
    w, h, s = int(width), int(height), float(scale)
    if w <= 0 or h <= 0 or not np.isfinite(s) or s <= 0:
        raise ValueError("%s: width, height and scale must be positive" % op)
    rr, cc = np.mgrid[0:h, 0:w].astype(np.float64)
    xw = float(origin[0]) + cc * s
    yw = float(origin[1]) + rr * s
    X = T[0, 0] * xw + T[0, 1] * yw + T[0, 3]
    Y = T[1, 0] * xw + T[1, 1] * yw + T[1, 3]
    Z = T[2, 0] * xw + T[2, 1] * yw + T[2, 3]
    front = Z > 1e-12
    safe_z = np.where(front, Z, 1.0)
    u, v = fx * X / safe_z, fy * Y / safe_z
    if kappa != 0.0:
        u, v = distort_division(u, v, kappa)
    col, row = u + cx, v + cy
    bad = ~(front & np.isfinite(col) & np.isfinite(row))
    return _sample(im, np.where(bad, -1e6, row), np.where(bad, -1e6, col), fill)


def change_radial_distortion_image(image, cam_in, cam_out, fill=0.0):
    """除算モデルの歪みを持つカメラの画像を、別の歪み・内部パラメータの画像へ描き直す。

    ``cam_out`` の画素を歪み除去 → 正規化座標 → ``cam_in`` の焦点距離 → ``cam_in`` の歪みの順に
    写して読む。``kappa`` の単位は 1/画素^2 で、主点からの画素座標に掛かる。``cam_out`` の
    ``kappa`` を 0 にすると歪み除去になる。空の入力(``image`` が 0 要素)は ValueError。

    Args:
        image: (H, W) の画像。
        cam_in: 入力のカメラ(``fx`` / ``fy`` / ``cx`` / ``cy`` / ``kappa``)。
        cam_out: 出力のカメラ(同じ鍵)。
        fill: 入力の外の画素の値。

    Returns:
        入力と同じ形の float 画像。

    出典: R. Lenz and D. Fritsch, ISPRS J. Photogramm. Remote Sens. 45(2), 90-110 (1990)。
    """
    op = "change_radial_distortion_image"
    im = _image2d(image, op)
    fxi, fyi, cxi, cyi, ki = _cam(cam_in, op)
    fxo, fyo, cxo, cyo, ko = _cam(cam_out, op)
    h, w = im.shape
    rr, cc = np.mgrid[0:h, 0:w].astype(np.float64)
    ux, uy = undistort_division(cc - cxo, rr - cyo, ko)
    dx, dy = distort_division(ux / fxo * fxi, uy / fyo * fyi, ki)
    col, row = dx + cxi, dy + cyi
    bad = ~(np.isfinite(col) & np.isfinite(row))
    return _sample(im, np.where(bad, -1e6, row), np.where(bad, -1e6, col), fill)


def _circle_offsets(radius):
    """半径 ``radius`` の離散円の、向かい合う点の組 (dr, dc) を半周ぶん返す。"""
    n = max(8, int(np.ceil(2.0 * np.pi * radius)))
    n += n % 2
    ang = 2.0 * np.pi * np.arange(n // 2) / n
    return np.rint(radius * np.sin(ang)).astype(int), np.rint(radius * np.cos(ang)).astype(int)


def points_lepetit(image, radius=3, check_neighbor=1, min_check_neighbor_diff=0.06,
                   min_score=0.2, subpix=True):
    """円周上の向かい合う 2 点の比較で注目点を検出する(Lepetit と Fua の点検出)。

    中心の灰色値に近い向かい合う 2 点が円周のどこかにあれば、そこを通る直線が伸びていると
    見なして落とす。残った画素を、円周の 2 階差分の総和(離散ラプラシアンの近似)で採点し、
    半径 ``radius`` の窓の極大だけを残す。``subpix`` が真なら応答の放物線で小数の位置へ寄せる。
    灰色の範囲は ``[0, 1]`` を想定するので、``min_check_neighbor_diff`` と ``min_score`` は
    その尺度で渡す。平らな画像は空の点列を返す。
    空の入力(``image`` が 0 要素)は ValueError。

    Args:
        image: (H, W) の画像。
        radius: 比較する円の半径(画素、>= 1)。
        check_neighbor: 円周で左右に何点まで一緒に比べるか(>= 0)。
        min_check_neighbor_diff: 「近い」と見なす灰色の差の上限。
        min_score: 応答(円周平均の 2 階差分の絶対値)の下限。
        subpix: 位置を小数へ寄せるか。

    Returns:
        (N, 2) の ``(row, col)``。応答の強い順。

    出典: V. Lepetit and P. Fua, IEEE Trans. PAMI 28(9), 1465-1479 (2006), doi:10.1109/TPAMI.2006.188。
    """
    op = "points_lepetit"
    im = _image2d(image, op)
    R = int(radius)
    nb = int(check_neighbor)
    if R < 1 or nb < 0:
        raise ValueError("%s: radius must be >= 1 and check_neighbor >= 0" % op)
    tau = float(min_check_neighbor_diff)
    thr = float(min_score)
    if not (np.isfinite(tau) and np.isfinite(thr)) or tau < 0 or thr < 0:
        raise ValueError("%s: thresholds must be finite and non-negative" % op)
    H, W = im.shape
    if H <= 2 * R or W <= 2 * R:
        return np.zeros((0, 2))
    drs, dcs = _circle_offsets(R)
    m = len(drs)
    rr, cc = np.mgrid[R:H - R, R:W - R]
    center = im[rr, cc]
    rejected = np.zeros(center.shape, bool)
    lap = np.zeros(center.shape)
    near_plus, near_minus = [], []
    for dr, dc in zip(drs, dcs):
        plus, minus = im[rr + dr, cc + dc], im[rr - dr, cc - dc]
        near_plus.append(np.abs(plus - center) <= tau)
        near_minus.append(np.abs(minus - center) <= tau)
        lap += plus + minus - 2.0 * center
    for i in range(m):
        # 直線は円周の向かい合う 2 点を中心と同じ灰色にする。隣の点まで見るのは、
        # 離散の円では直線の向きが刻みの間に落ちるため。
        p = np.zeros(center.shape, bool)
        q = np.zeros(center.shape, bool)
        for k in range(-nb, nb + 1):
            p |= near_plus[(i + k) % m]
            q |= near_minus[(i + k) % m]
        rejected |= p & q
    score = np.abs(lap) / (2.0 * m)
    score[rejected] = 0.0
    full = np.zeros((H, W))
    full[rr, cc] = score
    # 円の半径より内の 2 重の検出を抑える(応答の輪が物体の周りに 2 次の山を作るため)。
    peak = (full > 0) & (full >= thr) & (full == ndimage.maximum_filter(full, size=2 * R + 1))
    rows, cols = np.nonzero(peak)
    if rows.size == 0:
        return np.zeros((0, 2))
    order = np.argsort(-full[rows, cols], kind="stable")
    rows, cols = rows[order], cols[order]
    # 同じ高さの山は最大値の窓では 1 つに絞れない(物体が画素の境に乗ると隣の 2 画素が同点になる)。
    kept = []
    for i in range(rows.size):
        if all((rows[i] - rows[j]) ** 2 + (cols[i] - cols[j]) ** 2 > R * R for j in kept):
            kept.append(i)
    rows, cols = rows[kept], cols[kept]
    pts = np.column_stack([rows, cols]).astype(np.float64)
    if subpix:
        for i, (r, c) in enumerate(zip(rows, cols)):
            if 0 < r < H - 1:
                d = 2.0 * full[r, c] - full[r - 1, c] - full[r + 1, c]
                if d > 0:
                    pts[i, 0] += float(np.clip((full[r + 1, c] - full[r - 1, c]) / (2.0 * d), -0.5, 0.5))
            if 0 < c < W - 1:
                d = 2.0 * full[r, c] - full[r, c - 1] - full[r, c + 1]
                if d > 0:
                    pts[i, 1] += float(np.clip((full[r, c + 1] - full[r, c - 1]) / (2.0 * d), -0.5, 0.5))
    return pts


def get_grayval_contour_xld(image, contour, order=1):
    """輪郭の点列に沿って灰色値を補間で読み、1 本の信号にする。

    ``contour`` は (N, 2) の ``(row, col)`` か、輪郭が 1 本だけの XLD dict。``order`` は補間の
    次数(0 最近傍 / 1 線形 / 3 三次)。画像の外の点があると ValueError(外挿の値を実測の
    顔で返さない)。空の入力(``image`` が 0 要素)は ValueError。

    Args:
        image: (H, W) の画像。
        contour: (N, 2) の点列、または ``{"shape", "cs"}`` の XLD dict。
        order: 補間の次数(0 / 1 / 3)。

    Returns:
        長さ N の float 信号。
    """
    op = "get_grayval_contour_xld"
    im = _image2d(image, op)
    if isinstance(contour, dict):
        cs = contour.get("cs") or []
        if len(cs) != 1:
            raise ValueError("%s: pass exactly one contour, got %d" % (op, len(cs)))
        contour = cs[0]
    p = np.asarray(contour, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or p.shape[0] == 0:
        raise ValueError("%s: contour must be a non-empty (N, 2) array" % op)
    if not np.isfinite(p).all():
        raise ValueError("%s: contour has NaN/inf points" % op)
    if int(order) not in (0, 1, 3):
        raise ValueError("%s: order must be 0, 1 or 3" % op)
    H, W = im.shape
    if p[:, 0].min() < 0 or p[:, 1].min() < 0 or p[:, 0].max() > H - 1 or p[:, 1].max() > W - 1:
        raise ValueError("%s: the contour leaves the image" % op)
    return ndimage.map_coordinates(im, [p[:, 0], p[:, 1]], order=int(order), mode="nearest")
