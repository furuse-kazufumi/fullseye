"""range_image — organized(格子構造)深度画像の処理(深度センサ → 特徴の橋渡し)。

depth camera(RGB-D / ToF / structured-light)の出力は画素格子に整列した organized な
深度画像。非整列点群の kNN 法線推定より、隣接画素の外積で O(HW) に**向き付き**法線が出せる。
bearing-angle 画像・遮蔽エッジも range image 特有の古典特徴。すべて閉形式・GT 検証可能。

差別化: match3d.estimate_point_normals は unorganized 点群向け(kNN・符号曖昧)。ここは格子構造を
使い、視点向きに符号を確定する。Physical AI のナビ/把持で depth→法線→接触判定に直結。
"""
import numpy as np


def depth_to_organized_points(depth, fx=None, fy=None, cx=None, cy=None):
    """organized 深度画像 → 格子整列 3D 点 (H,W,3)。

    fx,fy 指定で透視逆投影 P=((u-cx)/fx*d, (v-cy)/fy*d, d)。未指定は正射(P=(x,y,depth), 格子間隔1)。
    """
    d = np.asarray(depth, float)
    H, W = d.shape
    uu, vv = np.meshgrid(np.arange(W), np.arange(H))
    if fx is None or fy is None:
        return np.stack([uu.astype(float), vv.astype(float), d], axis=-1)
    if cx is None:
        cx = (W - 1) / 2.0
    if cy is None:
        cy = (H - 1) / 2.0
    x = (uu - cx) / fx * d
    y = (vv - cy) / fy * d
    return np.stack([x, y, d], axis=-1)


def normals_from_depth(depth, fx=None, fy=None, cx=None, cy=None, orient_to_camera=True):
    """organized 深度 → 向き付き単位法線 (H,W,3)。隣接画素の 3D 点の外積(格子構造を利用、O(HW))。

    fx,fy 指定で透視、未指定で正射。orient_to_camera=True で法線をカメラ(原点)向きに符号統一。
    """
    P = depth_to_organized_points(depth, fx, fy, cx, cy)
    dPy, dPx = np.gradient(P, axis=0), np.gradient(P, axis=1)  # (H,W,3) each
    n = np.cross(dPx, dPy)
    nrm = np.linalg.norm(n, axis=-1, keepdims=True)
    n = n / (nrm + 1e-12)
    if orient_to_camera:
        # 視線 = 点→カメラ(原点)= -P。n·(-P) < 0 の画素を反転して視点向きに揃える。
        view = -P
        flip = np.sum(n * view, axis=-1) < 0
        n[flip] = -n[flip]
    return n.astype(np.float32)


def occlusion_edges(depth, rel_thresh=0.05):
    """深度の不連続(前景/背景境界 = 遮蔽エッジ)を検出。→ bool HxW。

    近傍との深度差が rel_thresh*median_depth を超える画素を境界とする(range image 特有の边缘)。
    """
    d = np.asarray(depth, float)
    gy, gx = np.gradient(d)
    grad = np.hypot(gx, gy)
    med = np.median(d[d > 0]) if np.any(d > 0) else 1.0
    return grad > (rel_thresh * med)


def bearing_angle_image(depth, direction="down"):
    """bearing-angle 画像: 走査方向に沿った視線と局所面のなす角(range image の古典記述子)。→ HxW(度)。

    隣接深度差から局所傾斜角 atan2(Δdepth, step) を計算。斜面の向きに敏感で照明不変。
    direction ∈ {down,up,right,left}。
    """
    d = np.asarray(depth, float)
    if direction in ("down", "up"):
        diff = np.gradient(d, axis=0)
    else:
        diff = np.gradient(d, axis=1)
    if direction in ("up", "left"):
        diff = -diff
    ba = np.degrees(np.arctan2(diff, 1.0))
    return ba.astype(np.float32)


def valid_mask(depth, min_depth=1e-6):
    """有効深度マスク(0/NaN/負を除外)。→ bool HxW。"""
    d = np.asarray(depth, float)
    return np.isfinite(d) & (d > min_depth)
