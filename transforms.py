"""同次変換行列演算(HALCON "Transformations" chapter の genuine 実装, numpy).

hom_mat2d(3x3)/ hom_mat3d(4x4)の生成・合成・逆・分解と点/画素変換。純粋な行列代数=
曖昧さのない genuine 実装。行列は行優先 numpy。"local" 版は右乗算(局所座標系での適用)。
"""
from __future__ import annotations

import numpy as np


def _m(a):
    return np.asarray(a, dtype=np.float64)


# ── hom_mat2d(3x3)─────────────────────────────────────────────────────────── #
def hom_mat2d_identity() -> np.ndarray:
    return np.eye(3)


def _t2(tx, ty):
    return np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1.0]])


def _r2(phi):
    c, s = np.cos(phi), np.sin(phi)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def _s2(sx, sy):
    return np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1.0]])


def hom_mat2d_translate(H, tx=0.0, ty=0.0):
    return _t2(tx, ty) @ _m(H)


def hom_mat2d_translate_local(H, tx=0.0, ty=0.0):
    return _m(H) @ _t2(tx, ty)


def hom_mat2d_rotate(H, phi=0.0):
    return _r2(phi) @ _m(H)


def hom_mat2d_rotate_local(H, phi=0.0):
    return _m(H) @ _r2(phi)


def hom_mat2d_scale(H, sx=1.0, sy=1.0):
    return _s2(sx, sy) @ _m(H)


def hom_mat2d_scale_local(H, sx=1.0, sy=1.0):
    return _m(H) @ _s2(sx, sy)


def hom_mat2d_slant(H, theta=0.0):
    S = np.array([[1, np.tan(theta), 0], [0, 1, 0], [0, 0, 1.0]])
    return S @ _m(H)


def hom_mat2d_reflect(H, axis=0):
    R = np.diag([-1.0 if axis == 0 else 1.0, -1.0 if axis == 1 else 1.0, 1.0])
    return R @ _m(H)


def hom_mat2d_invert(H):
    return np.linalg.inv(_m(H))


def hom_mat2d_transpose(H):
    return _m(H).T


def hom_mat2d_determinant(H) -> float:
    return float(np.linalg.det(_m(H)))


def hom_mat2d_compose(H1, H2):
    return _m(H1) @ _m(H2)


def hom_mat2d_to_affine_par(H) -> dict:
    """2D アフィン行列を (sx, sy, phi, theta, tx, ty) に分解。"""
    H = _m(H)
    a, b, tx = H[0]
    c, d, ty = H[1]
    sx = np.hypot(a, c)
    phi = np.arctan2(c, a)
    msy = a * d - b * c
    sy = msy / (sx + 1e-12)
    theta = np.arctan2(a * b + c * d, sx * sx) if sx > 1e-12 else 0.0
    return {"sx": float(sx), "sy": float(sy), "phi": float(phi),
            "theta": float(theta), "tx": float(tx), "ty": float(ty)}


def affine_trans_point_2d(H, px, py):
    r = _m(H) @ np.array([px, py, 1.0])
    return np.array([r[0], r[1]])


def projective_trans_point_2d(H, px, py):
    r = _m(H) @ np.array([px, py, 1.0])
    w = r[2] if abs(r[2]) > 1e-12 else 1.0
    return np.array([r[0] / w, r[1] / w])


def affine_trans_pixel(H, row, col):
    """画素 (row,col) にアフィン変換を適用(HALCON は (row,col) 順)。"""
    r = _m(H) @ np.array([col, row, 1.0])
    return np.array([r[1], r[0]])                        # (row, col) で返す


# ── hom_mat3d(4x4)─────────────────────────────────────────────────────────── #
def hom_mat3d_identity() -> np.ndarray:
    return np.eye(4)


def hom_mat3d_translate(H, tx=0.0, ty=0.0, tz=0.0):
    T = np.eye(4)
    T[:3, 3] = [tx, ty, tz]
    return T @ _m(H)


def hom_mat3d_scale(H, sx=1.0, sy=1.0, sz=1.0):
    return np.diag([sx, sy, sz, 1.0]) @ _m(H)


def hom_mat3d_invert(H):
    return np.linalg.inv(_m(H))


def hom_mat3d_transpose(H):
    return _m(H).T


def hom_mat3d_determinant(H) -> float:
    return float(np.linalg.det(_m(H)))


def hom_mat3d_compose(H1, H2):
    return _m(H1) @ _m(H2)


def hom_mat3d_rotate(H, phi=0.0, axis=2):
    """軸周りの右手系回転を左乗算(axis 0=x,1=y,2=z、標準の符号規約)。"""
    c, s = np.cos(phi), np.sin(phi)
    if axis == 0:
        R3 = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    elif axis == 1:
        R3 = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])   # y は符号が逆(右手系)
    else:
        R3 = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    R = np.eye(4)
    R[:3, :3] = R3
    return R @ _m(H)


def hom_mat3d_to_pose(H):
    """4x4 変換行列を pose [rx,ry,rz(ZYX euler), tx,ty,tz] に分解。"""
    H = _m(H)
    R, t = H[:3, :3], H[:3, 3]
    ry = np.arcsin(-np.clip(R[2, 0], -1, 1))
    rx = np.arctan2(R[2, 1], R[2, 2])
    rz = np.arctan2(R[1, 0], R[0, 0])
    return np.array([rx, ry, rz, t[0], t[1], t[2]])


def pose_to_hom_mat3d(pose):
    """pose [rx,ry,rz(rad), tx,ty,tz] を 4x4 変換行列に(hom_mat3d_to_pose の逆)。"""
    rx, ry, rz, tx, ty, tz = (float(x) for x in pose)
    Rx = hom_mat3d_rotate(np.eye(4), rx, 0)
    Ry = hom_mat3d_rotate(np.eye(4), ry, 1)
    Rz = hom_mat3d_rotate(np.eye(4), rz, 2)
    H = Rz @ Ry @ Rx
    H[:3, 3] = [tx, ty, tz]
    return H


def projective_trans_point_3d(H, px, py, pz):
    r = _m(H) @ np.array([px, py, pz, 1.0])
    w = r[3] if abs(r[3]) > 1e-12 else 1.0
    return r[:3] / w
