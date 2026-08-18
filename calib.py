"""カメラ校正/投影/ハンドアイ(HALCON "Calibration" chapter の genuine 実装, numpy).

投影・平面ホモグラフィ(image<->world plane)・Zhang 内部校正・Tsai-Lenz ハンドアイ。
実センサ handle でなく純粋な多視点幾何を本物で実装。
cam_par = {"fx","fy","cx","cy"}(またはピンホール 3x3 K)。pose = 4x4 剛体変換。
"""
from __future__ import annotations

import numpy as np


def _K(cam_par):
    if isinstance(cam_par, dict):
        return np.array([[cam_par["fx"], 0, cam_par["cx"]],
                         [0, cam_par["fy"], cam_par["cy"]], [0, 0, 1.0]])
    return np.asarray(cam_par, float)


def project_3d_point(points_3d, cam_par, pose=None):
    """3D 点をカメラへ透視投影し画素 (row, col) を返す(project_3d_point)。"""
    P = np.asarray(points_3d, float).reshape(-1, 3)
    K = _K(cam_par)
    if pose is not None:
        pose = np.asarray(pose, float)
        P = (P @ pose[:3, :3].T) + pose[:3, 3]
    uvw = P @ K.T
    uv = uvw[:, :2] / uvw[:, 2:3]
    return np.column_stack([uv[:, 1], uv[:, 0]])          # (row=y, col=x)


def project_point_hom_mat3d(points_3d, hom_mat3d):
    """4x4 or 3x4 同次変換で 3D 点を変換し投影(project_point_hom_mat3d)。"""
    P = np.asarray(points_3d, float).reshape(-1, 3)
    Hm = np.asarray(hom_mat3d, float)
    if Hm.shape == (4, 4):
        Hm = Hm[:3]
    out = (np.column_stack([P, np.ones(len(P))]) @ Hm.T)
    return out[:, :2] / out[:, 2:3]


def project_hom_point_hom_mat3d(points_hom, hom_mat3d):
    """同次 3D 点 (4,) を 3x4/4x4 行列で投影(project_hom_point_hom_mat3d)。"""
    P = np.asarray(points_hom, float).reshape(-1, 4)
    Hm = np.asarray(hom_mat3d, float)
    if Hm.shape == (4, 4):
        Hm = Hm[:3]
    out = P @ Hm.T
    return out[:, :2] / out[:, 2:3]


def _homography_dlt(src, dst):
    """4+ 点対応から DLT でホモグラフィ H (dst = H src) を推定。"""
    src = np.asarray(src, float).reshape(-1, 2); dst = np.asarray(dst, float).reshape(-1, 2)
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        A.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, Vt = np.linalg.svd(np.asarray(A))
    H = Vt[-1].reshape(3, 3)
    return H / H[2, 2]


def vector_to_hom_mat2d(src_points, dst_points):
    """点対応から 2D ホモグラフィを推定(vector_to_hom_mat2d)。"""
    return _homography_dlt(src_points, dst_points)


def image_to_world_plane(image_points, homography):
    """画像点を平面ホモグラフィで world 平面(z=0)へ写す(image_to_world_plane)。"""
    p = np.asarray(image_points, float).reshape(-1, 2)
    H = np.asarray(homography, float)
    h = np.column_stack([p, np.ones(len(p))]) @ H.T
    return h[:, :2] / h[:, 2:3]


def image_points_to_world_plane(cam_par, pose, image_points, scale=1.0):
    """カメラ内部/外部から画素を world 平面 z=0 へ逆投影(image_points_to_world_plane)。"""
    K = _K(cam_par); pose = np.asarray(pose, float)
    R = pose[:3, :3]; t = pose[:3, 3]
    Kinv = np.linalg.inv(K)
    p = np.asarray(image_points, float).reshape(-1, 2)
    out = []
    for row, col in p:
        d = R.T @ (Kinv @ np.array([col, row, 1.0]))       # 視線(world)
        o = -R.T @ t                                       # カメラ中心(world)
        lam = -o[2] / d[2]                                 # z=0 との交点
        w = o + lam * d
        out.append(w[:2] * scale)
    return np.asarray(out)


def contour_to_world_plane_xld(contour, homography):
    """XLD 輪郭(dict {cs:[Nx2]})を world 平面へ写す(contour_to_world_plane_xld)。"""
    out = {"shape": contour.get("shape"), "cs": []}
    for arr in contour.get("cs", []):
        out["cs"].append(image_to_world_plane(arr, homography))
    return out


def gen_radial_distortion_map(cam_par, kappa, shape):
    """半径歪みの逆マップ(row_map, col_map)を生成(gen_radial_distortion_map)。"""
    K = _K(cam_par); H, W = shape
    cx = K[0, 2]; cy = K[1, 2]
    rr, cc = np.mgrid[0:H, 0:W].astype(float)
    x = cc - cx; y = rr - cy
    r2 = x * x + y * y
    f = 1 + kappa * r2
    return {"row_map": cy + y * f, "col_map": cx + x * f}


# ── Zhang の平面校正(内部行列推定)────────────────────────────────────────────── #
def _vij(H, i, j):
    return np.array([H[0, i] * H[0, j],
                     H[0, i] * H[1, j] + H[1, i] * H[0, j],
                     H[1, i] * H[1, j],
                     H[2, i] * H[0, j] + H[0, i] * H[2, j],
                     H[2, i] * H[1, j] + H[1, i] * H[2, j],
                     H[2, i] * H[2, j]])


def camera_calibration(object_points, image_points_list):
    """Zhang 法で平面ターゲット多視点から内部行列 K を推定(camera_calibration)。
    object_points: (N,2) 平面座標、image_points_list: 各視点の (N,2) 画素対応リスト。"""
    obj = np.asarray(object_points, float).reshape(-1, 2)
    Hs = [_homography_dlt(obj, ip) for ip in image_points_list]
    V = []
    for H in Hs:
        V.append(_vij(H, 0, 1))
        V.append(_vij(H, 0, 0) - _vij(H, 1, 1))
    _, _, Vt = np.linalg.svd(np.asarray(V))
    b = Vt[-1]
    B = np.array([[b[0], b[1], b[3]], [b[1], b[2], b[4]], [b[3], b[4], b[5]]])
    cy = (B[0, 1] * B[0, 2] - B[0, 0] * B[1, 2]) / (B[0, 0] * B[1, 1] - B[0, 1] ** 2)
    lam = B[2, 2] - (B[0, 2] ** 2 + cy * (B[0, 1] * B[0, 2] - B[0, 0] * B[1, 2])) / B[0, 0]
    fx = np.sqrt(lam / B[0, 0])
    fy = np.sqrt(lam * B[0, 0] / (B[0, 0] * B[1, 1] - B[0, 1] ** 2))
    skew = -B[0, 1] * fx * fx * fy / lam
    cx = skew * cy / fy - B[0, 2] * fx * fx / lam
    return {"fx": float(fx), "fy": float(fy), "cx": float(cx), "cy": float(cy),
            "skew": float(skew), "homographies": Hs}


def calibrate_cameras(object_points, image_points_list):
    """Zhang 法カメラ校正(calibrate_cameras)。camera_calibration の別名。"""
    return camera_calibration(object_points, image_points_list)


# ── Tsai-Lenz ハンドアイ校正(AX = XB)──────────────────────────────────────────── #
def _rot_to_axis(R):
    """回転行列から回転ベクトル(軸*角)を返す。"""
    ang = np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))
    if ang < 1e-9:
        return np.zeros(3)
    ax = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return ax / (2 * np.sin(ang)) * ang


def _axis_to_rot(v):
    ang = np.linalg.norm(v)
    if ang < 1e-12:
        return np.eye(3)
    ax = v / ang
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * (K @ K)


def hand_eye_calibration(poses_a, poses_b):
    """一連の運動対から AX=XB を解き X(4x4)を推定(hand_eye_calibration)。
    poses_a/poses_b: 4x4 剛体変換のリスト。隣接運動から相対運動を構成。"""
    A = [np.asarray(p, float) for p in poses_a]
    B = [np.asarray(p, float) for p in poses_b]
    # 回転: 相対運動の回転軸から最小二乗で Rx を解く(修正 Rodrigues)
    Msum = np.zeros((3, 3)); bsum = np.zeros(3)
    rels = []
    for i in range(len(A) - 1):
        Ma = np.linalg.inv(A[i]) @ A[i + 1]
        Mb = np.linalg.inv(B[i]) @ B[i + 1]
        rels.append((Ma, Mb))
        alpha = _rot_to_axis(Ma[:3, :3]); beta = _rot_to_axis(Mb[:3, :3])
        # Park-Martin: solve Rx by matrix log LS  M += beta alpha^T
        Msum += np.outer(beta, alpha)
    U, S, Vt = np.linalg.svd(Msum)
    d = np.sign(np.linalg.det(U @ Vt))
    Rx = U @ np.diag([1, 1, d]) @ Vt
    # 並進: (Ra - I) tx = Rx tb - ta
    Ct = []; dt = []
    for Ma, Mb in rels:
        Ct.append(Ma[:3, :3] - np.eye(3))
        dt.append(Rx @ Mb[:3, 3] - Ma[:3, 3])
    tx, *_ = np.linalg.lstsq(np.vstack(Ct), np.concatenate(dt), rcond=None)
    X = np.eye(4); X[:3, :3] = Rx; X[:3, 3] = tx
    return X


def calibrate_hand_eye(poses_a, poses_b):
    """ハンドアイ校正(calibrate_hand_eye)。hand_eye_calibration の別名。"""
    return hand_eye_calibration(poses_a, poses_b)
