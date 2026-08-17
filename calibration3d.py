"""カメラ校正の幾何(HALCON "Calibration" chapter の genuine core, numpy).

3D アフィン変換、放射歪みの画像適用、カメラ内部パラメータ+ポーズ→4x4 行列。純粋な幾何式。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def affine_trans_point_3d(points, H=None) -> np.ndarray:
    """3D 点に 4x4 同次アフィン変換を適用(affine_trans_point_3d)。"""
    p = np.asarray(points, dtype=np.float64).reshape(-1, 3)
    H = np.eye(4) if H is None else np.asarray(H, dtype=np.float64)
    hom = np.column_stack([p, np.ones(len(p))]) @ H.T
    return hom[:, :3]


def cam_par_pose_to_hom_mat3d(pose) -> np.ndarray:
    """カメラポーズ [rx,ry,rz(rad), tx,ty,tz] を 4x4 同次変換行列に変換(cam_par_pose_to_hom_mat3d)。"""
    rx, ry, rz, tx, ty, tz = (float(x) for x in pose)
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    R = Rz @ Ry @ Rx
    H = np.eye(4)
    H[:3, :3] = R
    H[:3, 3] = [tx, ty, tz]
    return H


def change_radial_distortion_image(image, kappa: float = 0.0):
    """画像に放射歪み r' = r(1 + kappa r^2) を適用して再サンプル(change_radial_distortion_image)。"""
    img = np.asarray(image, dtype=np.float64)
    h, w = img.shape
    cy, cx = (h - 1) / 2, (w - 1) / 2
    scale = max(h, w) / 2
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    dy, dx = (yy - cy) / scale, (xx - cx) / scale
    r2 = dx * dx + dy * dy
    f = 1 + kappa * r2
    src_y = cy + dy * f * scale
    src_x = cx + dx * f * scale
    return ndimage.map_coordinates(img, [src_y, src_x], order=1, mode="reflect")


def change_radial_distortion_cam_par(cam_par, kappa_new: float = 0.0) -> np.ndarray:
    """カメラパラメータの放射歪み係数を kappa_new に置換(change_radial_distortion_cam_par)。"""
    cp = np.array(cam_par, dtype=np.float64).copy()
    if len(cp) >= 2:
        cp[1] = kappa_new                                 # 慣例: [focal, kappa, ...]
    return cp
