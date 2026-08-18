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


# ── local 変種(右乗算)+ 追加 ─────────────────────────────────────────────── #
def hom_mat2d_slant_local(H, theta=0.0):
    S = np.array([[1, np.tan(theta), 0], [0, 1, 0], [0, 0, 1.0]])
    return _m(H) @ S


def hom_mat2d_reflect_local(H, axis=0):
    R = np.diag([-1.0 if axis == 0 else 1.0, -1.0 if axis == 1 else 1.0, 1.0])
    return _m(H) @ R


def hom_mat3d_rotate_local(H, phi=0.0, axis=2):
    return _m(H) @ hom_mat3d_rotate(np.eye(4), phi, axis)


def hom_mat3d_translate_local(H, tx=0.0, ty=0.0, tz=0.0):
    T = np.eye(4)
    T[:3, 3] = [tx, ty, tz]
    return _m(H) @ T


def hom_mat3d_scale_local(H, sx=1.0, sy=1.0, sz=1.0):
    return _m(H) @ np.diag([sx, sy, sz, 1.0])


def hom_mat3d_transpose_(H):
    return _m(H).T


def hom_mat3d_project(H, px, py, pz):
    """4x4 の透視投影行列で 3D 点を 2D 画像点へ(hom_mat3d_project)。"""
    r = _m(H) @ np.array([px, py, pz, 1.0])
    w = r[2] if abs(r[2]) > 1e-12 else 1.0
    return np.array([r[0] / w, r[1] / w])


def projective_trans_pixel(H, row, col):
    """画素 (row,col) に射影変換を適用(HALCON (row,col) 順)。"""
    r = _m(H) @ np.array([col, row, 1.0])
    w = r[2] if abs(r[2]) > 1e-12 else 1.0
    return np.array([r[1] / w, r[0] / w])


def dual_quat_to_hom_mat3d(dq):
    """単位二重四元数 [qr(4), qd(4)] を 4x4 剛体変換に(dual_quat_to_hom_mat3d)。"""
    dq = np.asarray(dq, dtype=np.float64)
    qr, qd = dq[:4], dq[4:8]
    w, x, y, z = qr
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                  [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                  [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])
    t = 2 * np.array([
        -qd[0] * qr[1] + qd[1] * qr[0] - qd[2] * qr[3] + qd[3] * qr[2],
        -qd[0] * qr[2] + qd[1] * qr[3] + qd[2] * qr[0] - qd[3] * qr[1],
        -qd[0] * qr[3] - qd[1] * qr[2] + qd[2] * qr[1] + qd[3] * qr[0]])
    H = np.eye(4)
    H[:3, :3] = R
    H[:3, 3] = t
    return H


# ── 点対応からの変換推定・分解・pose 変換 ────────────────────────────────────── #
def vector_to_hom_mat3d(src_points, dst_points):
    """3D 点対応から剛体/相似変換(4x4)を Umeyama 推定(vector_to_hom_mat3d)。"""
    P = _m(src_points).reshape(-1, 3); Q = _m(dst_points).reshape(-1, 3)
    mp = P.mean(0); mq = Q.mean(0)
    Pc = P - mp; Qc = Q - mq
    H = Pc.T @ Qc / len(P)
    U, S, Vt = np.linalg.svd(H)
    D = np.eye(3)
    if np.linalg.det(U @ Vt) < 0:
        D[2, 2] = -1
    R = Vt.T @ D @ U.T
    t = mq - R @ mp
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = t
    return T


def vector_to_proj_hom_mat2d(src_points, dst_points):
    """2D 点対応から射影変換(ホモグラフィ 3x3)を DLT 推定(vector_to_proj_hom_mat2d)。"""
    src = _m(src_points).reshape(-1, 2); dst = _m(dst_points).reshape(-1, 2)
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        A.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, Vt = np.linalg.svd(_m(A))
    H = Vt[-1].reshape(3, 3)
    return H / H[2, 2]


def vector_to_aniso(src_points, dst_points):
    """2D 点対応から異方性(非等方スケール)アフィン変換を推定(vector_to_aniso)。"""
    src = _m(src_points).reshape(-1, 2); dst = _m(dst_points).reshape(-1, 2)
    A = np.column_stack([src, np.ones(len(src))])
    coef, *_ = np.linalg.lstsq(A, dst, rcond=None)
    H = np.eye(3); H[0, :] = coef[:, 0]; H[1, :] = coef[:, 1]
    return H


def point_line_to_hom_mat2d(p_src, dir_src, p_dst, dir_dst):
    """点+方向の対応から 2D 剛体変換を推定(point_line_to_hom_mat2d)。"""
    ds = _m(dir_src); dd = _m(dir_dst)
    a = np.arctan2(dd[0], dd[1]) - np.arctan2(ds[0], ds[1])
    c, s = np.cos(a), np.sin(a)
    R = np.array([[c, -s], [s, c]])
    t = _m(p_dst) - R @ _m(p_src)
    H = np.eye(3); H[:2, :2] = R; H[:2, 2] = t
    return H


def proj_hom_mat2d_to_pose(H, K):
    """ホモグラフィと内部行列から平面の姿勢(R,t)を分解(proj_hom_mat2d_to_pose)。"""
    H = _m(H); K = _m(K); Kinv = np.linalg.inv(K)
    L = Kinv @ H
    lam = 1.0 / (np.linalg.norm(L[:, 0]) + 1e-12)
    r1 = L[:, 0] * lam; r2 = L[:, 1] * lam; t = L[:, 2] * lam
    r3 = np.cross(r1, r2)
    R = np.column_stack([r1, r2, r3])
    U, _, Vt = np.linalg.svd(R)
    R = U @ Vt
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = t
    return T


def projective_trans_hom_point_3d(points_hom, hom_mat):
    """同次 3D 点に 4x4 射影変換を適用(projective_trans_hom_point_3d)。"""
    P = _m(points_hom).reshape(-1, 4)
    out = P @ _m(hom_mat).T
    return out / out[:, 3:4]


def set_origin_pose(pose, dx, dy, dz):
    """姿勢の原点を局所オフセットだけ移動(set_origin_pose)。"""
    T = _m(pose).copy()
    T[:3, 3] = T[:3, 3] + T[:3, :3] @ np.array([dx, dy, dz], float)
    return T


def vector_field_to_hom_mat2d(vfield_row, vfield_col):
    """ベクトル場全体に最も合うアフィン変換(2x3)を最小二乗推定(vector_field_to_hom_mat2d)。"""
    vr = _m(vfield_row); vc = _m(vfield_col)
    H, W = vr.shape
    rr, cc = np.mgrid[0:H, 0:W]
    src = np.column_stack([cc.ravel(), rr.ravel(), np.ones(H * W)])
    dst_c = (cc + vc).ravel(); dst_r = (rr + vr).ravel()
    cx, *_ = np.linalg.lstsq(src, dst_c, rcond=None)
    cy, *_ = np.linalg.lstsq(src, dst_r, rcond=None)
    M = np.eye(3); M[0] = cx; M[1] = cy
    return M


def get_rectangle_pose(row, col, phi, l1, l2, K):
    """画像上の矩形から平面姿勢を推定(4 角対応 → homography → pose)(get_rectangle_pose)。"""
    corners_img = np.array([[row - l2, col - l1], [row - l2, col + l1],
                            [row + l2, col + l1], [row + l2, col - l1]], float)
    ca, sa = np.cos(phi), np.sin(phi)
    R2 = np.array([[ca, -sa], [sa, ca]])
    rel = corners_img - [row, col]
    corners_img = (rel @ R2.T) + [row, col]
    world = np.array([[-l1, -l2], [l1, -l2], [l1, l2], [-l1, l2]], float)
    H = vector_to_proj_hom_mat2d(world, corners_img[:, ::-1])
    return proj_hom_mat2d_to_pose(H, K)


def gen_image_warp_map(hom_mat2d, shape):
    """2D ホモグラフィから画素ワープマップ(逆写像)を生成(gen_image_warp_map)。"""
    H = np.linalg.inv(_m(hom_mat2d))
    Hh, Ww = shape
    rr, cc = np.mgrid[0:Hh, 0:Ww]
    hom = np.column_stack([cc.ravel(), rr.ravel(), np.ones(Hh * Ww)]) @ H.T
    xy = hom[:, :2] / hom[:, 2:3]
    return {"row_map": xy[:, 1].reshape(Hh, Ww), "col_map": xy[:, 0].reshape(Hh, Ww)}


def vector_to_proj_hom_mat2d_distortion(src_points, dst_points):
    """歪み込みで射影変換を推定(歪みは小と仮定し DLT)(vector_to_proj_hom_mat2d_distortion)。"""
    H = vector_to_proj_hom_mat2d(src_points, dst_points)
    return {"H": H, "kappa": 0.0}


def point_pluecker_line_to_hom_mat3d(point, pluecker, target_point, target_dir):
    """点+Plücker 直線の対応から 3D 剛体変換を推定(point_pluecker_line_to_hom_mat3d)。"""
    d1 = _m(pluecker["direction"]); d1 = d1 / (np.linalg.norm(d1) + 1e-12)
    d2 = _m(target_dir); d2 = d2 / (np.linalg.norm(d2) + 1e-12)
    v = np.cross(d1, d2); s = np.linalg.norm(v); c = d1 @ d2
    if s < 1e-9:
        R = np.eye(3)
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        R = np.eye(3) + vx + vx @ vx * ((1 - c) / (s ** 2))
    t = _m(target_point) - R @ _m(point)
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = t
    return T


def dual_quat_trans_line_3d(dual_quat, line_point, line_dir):
    """双四元数で 3D 直線を変換(点と方向を剛体変換)(dual_quat_trans_line_3d)。"""
    from pose_quat import dual_quat_to_hom_mat3d
    T = dual_quat_to_hom_mat3d(dual_quat)
    p = T[:3, :3] @ _m(line_point) + T[:3, 3]
    d = T[:3, :3] @ _m(line_dir)
    return {"point": p, "direction": d / (np.linalg.norm(d) + 1e-12)}
