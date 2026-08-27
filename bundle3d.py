"""bundle3d — N 視点バンドル調整(全カメラ姿勢 + 3D 構造を再投影誤差最小で同時最適化)。

twoview が 2 視点の相対姿勢初期化なら、bundle3d はその N 視点版 = SfM/VO の仕上げ。
各カメラを回転ベクトル rvec(3) + 並進 t(3) の 6 パラメータで表し、観測(どのカメラがどの 3D 点を
どの画素で見たか)全体の再投影残差を Levenberg-Marquardt(scipy.optimize.least_squares)で最小化する。
gauge 自由度(相似変換 7-DOF)は **先頭カメラを [I|0] に固定**して回転+並進を除く(scale は弱く残るが
微小摂動からの回復では問題にならない)。

規約: 射影 u = K (R X + t) の透視除算(match3d.project_points と一致)。K は全カメラ共有(単純化)。
GT 検証 = 合成 N カメラ+点群で観測生成 → 姿勢と点に摂動 → BA で再投影 RMSE ~0・回転誤差<0.5°に回復。

用途: 単眼/多眼 SfM の後段最適化、hand-eye 較正の精緻化、マルチカメラ計測の一括調整(Physical AI)。
"""
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


def rvec_to_R(rvec):
    """回転ベクトル(3,) → 回転行列(3,3)。"""
    return Rotation.from_rotvec(np.asarray(rvec, float)).as_matrix()


def R_to_rvec(R):
    """回転行列(3,3) → 回転ベクトル(3,)。"""
    return Rotation.from_matrix(np.asarray(R, float)).as_rotvec()


def project(points, rvec, t, K):
    """3D 点 (n,3) をカメラ (rvec,t,K) で 2D (n,2) に射影(透視除算)。"""
    R = rvec_to_R(rvec)
    Xc = (R @ np.asarray(points, float).T).T + np.asarray(t, float)
    x = (np.asarray(K, float) @ Xc.T).T
    return x[:, :2] / x[:, 2:3]


def _pack(cameras, points, fix_first):
    """(cameras (nc,6), points (m,3)) → 最適化パラメータベクトル(fix_first なら cam0 除外)。"""
    cams = cameras[1:] if fix_first else cameras
    return np.concatenate([cams.ravel(), points.ravel()])


def _unpack(params, nc, m, cam0, fix_first):
    """パラメータベクトル → (cameras (nc,6), points (m,3))。"""
    if fix_first:
        cam_rest = params[: (nc - 1) * 6].reshape(nc - 1, 6)
        cameras = np.vstack([cam0[None, :], cam_rest])
        pts = params[(nc - 1) * 6:].reshape(m, 3)
    else:
        cameras = params[: nc * 6].reshape(nc, 6)
        pts = params[nc * 6:].reshape(m, 3)
    return cameras, pts


def reprojection_residuals(cameras, points, obs_cam, obs_pt, obs_uv, K):
    """全観測の再投影残差(2*K,)。cameras (nc,6)=[rvec|t]、obs_* は観測配列。"""
    cameras = np.asarray(cameras, float)
    points = np.asarray(points, float)
    obs_cam = np.asarray(obs_cam, int)
    obs_pt = np.asarray(obs_pt, int)
    obs_uv = np.asarray(obs_uv, float)
    res = np.empty((len(obs_cam), 2))
    for c in np.unique(obs_cam):
        m = obs_cam == c
        proj = project(points[obs_pt[m]], cameras[c, :3], cameras[c, 3:], K)
        res[m] = proj - obs_uv[m]
    return res.ravel()


def mean_reprojection_error(cameras, points, obs_cam, obs_pt, obs_uv, K):
    """再投影 RMS 誤差(ピクセル)。"""
    r = reprojection_residuals(cameras, points, obs_cam, obs_pt, obs_uv, K)
    return float(np.sqrt(np.mean(r.reshape(-1, 2) ** 2 * 2)))


def bundle_adjust(cameras, points, obs_cam, obs_pt, obs_uv, K,
                  fix_first=True, max_iter=200):
    """再投影誤差最小でカメラ姿勢と 3D 点を同時最適化。→ dict{cameras, points, rmse, cost}。

    cameras (nc,6)=[rvec(3)|t(3)] の初期値、points (m,3) の初期値、観測 obs_cam/obs_pt/obs_uv。
    fix_first=True で先頭カメラを [I|0] 相当(初期値のまま)に固定し gauge を除く。
    """
    cameras = np.asarray(cameras, float)
    points = np.asarray(points, float)
    obs_cam = np.asarray(obs_cam, int)
    obs_pt = np.asarray(obs_pt, int)
    obs_uv = np.asarray(obs_uv, float)
    nc, m = len(cameras), len(points)
    if nc < 2:
        raise ValueError("バンドル調整は 2 カメラ以上必要")
    if len(obs_cam) == 0:
        raise ValueError("観測が空(バンドル調整は再投影観測が必要)")
    if not (len(obs_cam) == len(obs_pt) == len(obs_uv)):
        raise ValueError("観測配列の長さが不一致")
    cam0 = cameras[0].copy()

    def fun(p):
        cams, pts = _unpack(p, nc, m, cam0, fix_first)
        return reprojection_residuals(cams, pts, obs_cam, obs_pt, obs_uv, K)

    p0 = _pack(cameras, points, fix_first)
    sol = least_squares(fun, p0, method="lm", max_nfev=max_iter * len(p0))
    cams, pts = _unpack(sol.x, nc, m, cam0, fix_first)
    rmse = mean_reprojection_error(cams, pts, obs_cam, obs_pt, obs_uv, K)
    return {"cameras": cams, "points": pts, "rmse": rmse, "cost": float(sol.cost)}
