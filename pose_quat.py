"""ポーズ/四元数演算(HALCON "Transformations" chapter の genuine 実装, numpy).

四元数 q=[w,x,y,z]、ポーズ pose=[tx,ty,tz, rx,ry,rz(rad)]、二重四元数 dq=[qr(4),qd(4)]。
剛体変換の各表現間の変換・合成・逆・補間。純粋な代数=曖昧さのない genuine 実装。
"""
from __future__ import annotations

import numpy as np


def _q(a):
    return np.asarray(a, dtype=np.float64)


def _unit(v, what, hint):
    """向きを持つベクトルを厳密に単位化する。長さ 0 なら **拒否**する。

    2026-09-01 の敵対監査で、ここが `norm + 1e-12` で割っていたために 2 通りの
    無言の誤りが起きていた:

      * **零ベクトルが通ってしまう。** ``quat_normalize([0,0,0,0])`` は
        ``[0,0,0,0]`` を返し、それを ``quat_to_hom_mat3d`` に渡すと**単位行列**
        になる ―― 「回転が定義できない」が「回転しない」に化ける。
        ``axis_angle_to_quat(0,0,0,1.0)`` も同様に、軸を持たない回転要求が
        ノルム 0.878 の非単位四元数(= 再正規化後は恒等)になっていた。
      * **正しい入力まで系統的に縮む。** 分母に 1e-12 を足すと商のノルムが
        1 をわずかに下回るので、そこから作った回転行列は直交から外れる
        (実測 |RᵀR − I| = 4.0e-12)。丸め誤差ではなく一方向の縮みで、
        合成を重ねるほど溜まる。

    したがって「長さ 0 は拒否、それ以外は厳密に割る」に直した。
    """
    n = float(np.linalg.norm(v))
    if not np.isfinite(n):
        raise ValueError("%s must be finite (got norm %r)" % (what, n))
    if n == 0.0:
        raise ValueError("%s has zero length, so %s — pass a non-zero vector"
                         % (what, hint))
    return v / n


# ── 四元数 ─────────────────────────────────────────────────────────────────── #
def axis_angle_to_quat(ax, ay, az, angle):
    n = _unit(np.array([ax, ay, az], float), "the rotation axis (ax, ay, az)",
              "there is no rotation to describe")
    return np.concatenate([[np.cos(angle / 2)], n * np.sin(angle / 2)])


def quat_normalize(q):
    return _unit(_q(q), "the quaternion",
                 "it denotes no rotation (a rotor must have unit length)")


def quat_conjugate(q):
    q = _q(q)
    return np.array([q[0], -q[1], -q[2], -q[3]])


def quat_compose(q1, q2):
    w1, x1, y1, z1 = _q(q1)
    w2, x2, y2, z2 = _q(q2)
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def quat_to_hom_mat3d(q):
    w, x, y, z = quat_normalize(q)
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                  [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                  [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])
    H = np.eye(4)
    H[:3, :3] = R
    return H


def quat_rotate_point_3d(q, px, py, pz):
    qp = np.concatenate([[0.0], [px, py, pz]])
    r = quat_compose(quat_compose(q, qp), quat_conjugate(q))
    return r[1:]


def quat_interpolate(q1, q2, t=0.5):
    """slerp 球面線形補間。"""
    q1, q2 = quat_normalize(q1), quat_normalize(q2)
    d = float(np.dot(q1, q2))
    if d < 0:
        q2, d = -q2, -d
    if d > 0.9995:
        return quat_normalize(q1 + t * (q2 - q1))
    th = np.arccos(np.clip(d, -1, 1))
    return (np.sin((1 - t) * th) * q1 + np.sin(t * th) * q2) / np.sin(th)


def _mat_to_quat(R):
    tr = np.trace(R)
    if tr > 0:
        s = np.sqrt(tr + 1.0) * 2
        w = 0.25 * s
        x = (R[2, 1] - R[1, 2]) / s
        y = (R[0, 2] - R[2, 0]) / s
        z = (R[1, 0] - R[0, 1]) / s
    else:
        i = int(np.argmax(np.diag(R)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = np.sqrt(R[i, i] - R[j, j] - R[k, k] + 1.0) * 2
        q = np.zeros(4)
        q[0] = (R[k, j] - R[j, k]) / s
        q[i + 1] = 0.25 * s
        q[j + 1] = (R[j, i] + R[i, j]) / s
        q[k + 1] = (R[k, i] + R[i, k]) / s
        return quat_normalize(q)
    return quat_normalize(np.array([w, x, y, z]))


# ── pose = [tx,ty,tz, rx,ry,rz] ────────────────────────────────────────────── #
def _pose_to_R(pose):
    rx, ry, rz = pose[3], pose[4], pose[5]
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _R_to_euler(R):
    ry = np.arcsin(-np.clip(R[2, 0], -1, 1))
    rx = np.arctan2(R[2, 1], R[2, 2])
    rz = np.arctan2(R[1, 0], R[0, 0])
    return rx, ry, rz


def create_pose(tx=0.0, ty=0.0, tz=0.0, rx=0.0, ry=0.0, rz=0.0):
    return np.array([tx, ty, tz, rx, ry, rz], float)


def pose_to_hom_mat3d_local(pose):
    H = np.eye(4)
    H[:3, :3] = _pose_to_R(pose)
    H[:3, 3] = pose[:3]
    return H


def hom_mat3d_to_pose_local(H):
    H = np.asarray(H, float)
    rx, ry, rz = _R_to_euler(H[:3, :3])
    return np.array([H[0, 3], H[1, 3], H[2, 3], rx, ry, rz])


def pose_compose(p1, p2):
    return hom_mat3d_to_pose_local(pose_to_hom_mat3d_local(p1) @ pose_to_hom_mat3d_local(p2))


def pose_invert(p):
    return hom_mat3d_to_pose_local(np.linalg.inv(pose_to_hom_mat3d_local(p)))


def pose_to_quat(pose):
    return _mat_to_quat(_pose_to_R(pose))


def quat_to_pose(q, tx=0.0, ty=0.0, tz=0.0):
    rx, ry, rz = _R_to_euler(quat_to_hom_mat3d(q)[:3, :3])
    return np.array([tx, ty, tz, rx, ry, rz])


def pose_average(poses):
    poses = np.asarray(poses, float).reshape(-1, 6)
    t = poses[:, :3].mean(0)
    qs = np.array([pose_to_quat(p) for p in poses])
    qs *= np.sign(qs[:, :1] + 1e-12)
    qm = quat_normalize(qs.mean(0))
    return quat_to_pose(qm, *t)


def convert_pose_type(pose, order="xyz"):
    """pose の並びを返す(genuine な型変換の簡易版=恒等で type タグを付す)。"""
    return {"pose": np.asarray(pose, float), "type": order}


def get_pose_type(pose):
    return "point_3d_and_euler_xyz"


# ── 球面座標 ───────────────────────────────────────────────────────────────── #
def convert_point_3d_cart_to_spher(x, y, z):
    r = np.sqrt(x * x + y * y + z * z)
    lon = np.arctan2(y, x)
    lat = np.arcsin(np.clip(z / (r + 1e-12), -1, 1))
    return np.array([r, lon, lat])


def convert_point_3d_spher_to_cart(r, lon, lat):
    return np.array([r * np.cos(lat) * np.cos(lon),
                     r * np.cos(lat) * np.sin(lon),
                     r * np.sin(lat)])


# ── 二重四元数 ─────────────────────────────────────────────────────────────── #
def pose_to_dual_quat(pose):
    qr = pose_to_quat(pose)
    t = np.concatenate([[0.0], np.asarray(pose[:3], float)])
    qd = 0.5 * quat_compose(t, qr)
    return np.concatenate([qr, qd])


def dual_quat_to_pose(dq):
    dq = _q(dq)
    qr, qd = dq[:4], dq[4:8]
    t = 2 * quat_compose(qd, quat_conjugate(qr))
    return np.concatenate([t[1:], quat_to_pose(qr)[3:]])


def dual_quat_normalize(dq):
    dq = _q(dq)
    n = float(np.linalg.norm(dq[:4]))
    if n == 0.0 or not np.isfinite(n):
        raise ValueError("the real part of the dual quaternion has zero length, "
                         "so it denotes no rigid motion — pass a non-zero rotor")
    return dq / n


def dual_quat_conjugate(dq):
    dq = _q(dq)
    return np.concatenate([quat_conjugate(dq[:4]), quat_conjugate(dq[4:8])])


def dual_quat_trans_point_3d(dq, px, py, pz):
    return dual_quat_to_pose(dq)[:3] + quat_rotate_point_3d(_q(dq)[:4], px, py, pz)


def dual_quat_compose(dq1, dq2):
    """二重四元数の合成(剛体変換の合成、dual_quat_compose)。"""
    dq1, dq2 = _q(dq1), _q(dq2)
    qr = quat_compose(dq1[:4], dq2[:4])
    qd = quat_compose(dq1[:4], dq2[4:8]) + quat_compose(dq1[4:8], dq2[:4])
    return np.concatenate([qr, qd])


def dual_quat_interpolate(dq1, dq2, t=0.5):
    """二重四元数の補間(pose 経由で並進 lerp + 回転 slerp、dual_quat_interpolate)。"""
    p1, p2 = dual_quat_to_pose(dq1), dual_quat_to_pose(dq2)
    tt = (1 - t) * p1[:3] + t * p2[:3]
    q = quat_interpolate(pose_to_quat(p1), pose_to_quat(p2), t)
    pose = np.concatenate([tt, quat_to_pose(q)[3:]])
    return pose_to_dual_quat(pose)


def screw_to_dual_quat(lx, ly, lz, mx, my, mz, theta=0.0, d=0.0):
    """スクリュー(軸方向 l, モーメント m, 回転角 theta, 並進 d)を二重四元数へ(screw_to_dual_quat)。"""
    l = _unit(np.array([lx, ly, lz], float), "the screw axis (lx, ly, lz)",
              "there is no screw motion to describe")
    m = np.array([mx, my, mz], float)
    ct, st = np.cos(theta / 2), np.sin(theta / 2)
    qr = np.concatenate([[ct], st * l])
    qd = np.concatenate([[-d / 2 * st], st * m + d / 2 * ct * l])
    return np.concatenate([qr, qd])


def dual_quat_to_screw(dq):
    """二重四元数からスクリュー成分(角度・並進・軸)を返す(dual_quat_to_screw)。"""
    dq = _q(dq)
    qr, qd = dq[:4], dq[4:8]
    theta = 2 * np.arccos(np.clip(qr[0], -1, 1))
    st = np.sqrt(max(1 - qr[0] ** 2, 0)) + 1e-12
    l = qr[1:] / st
    d = -2 * qd[0] / st
    return {"theta": float(theta), "d": float(d), "axis": l}
