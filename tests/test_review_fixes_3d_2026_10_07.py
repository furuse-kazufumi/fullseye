# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""2026-10-07 レビューで再現した 3-D op の欠陥 13 件の回帰テスト。

多くは「原点から遠い座標で壊れる」型(UTM・LiDAR の絶対座標)。真値はどれも op と別の
経路から取る: 合成した姿勢・球・円筒の既知パラメータ、scipy の回転、閉形式の角度。
各修正について、原点の近くで結果が変わらないことも確かめる。
"""
import numpy as np
import pytest

import gicp
import match3d
import measure3d
import metrics3d
import pnp3d
import pose_quat as pq
import ransac_fit
import registration_eval
import sdf_ops
import shapestats

from conftest import requires_backend

Rot = pytest.importorskip("scipy.spatial.transform").Rotation


# --- 共通: 波打つ面(点-面 ICP / GICP 用) -----------------------------------------------------
def _wavy(n=25):
    g = np.linspace(-1, 1, n)
    X, Y = np.meshgrid(g, g)
    Z = 0.2 * np.sin(3 * X) * np.cos(2 * Y)
    pts = np.c_[X.ravel(), Y.ravel(), Z.ravel()]
    dzdx = 0.6 * np.cos(3 * X) * np.cos(2 * Y)
    dzdy = -0.4 * np.sin(3 * X) * np.sin(2 * Y)
    nrm = np.c_[-dzdx.ravel(), -dzdy.ravel(), np.ones(dzdx.size)]
    return pts, nrm / np.linalg.norm(nrm, axis=1, keepdims=True)


def _pair(offset):
    """dst = wavy + offset、src は dst を重心まわりに (3,-2,4)° 回して少し動かした逆像。"""
    dst0, nrm = _wavy()
    dst = dst0 + offset
    Rg = Rot.from_euler("xyz", [3, -2, 4], degrees=True).as_matrix()
    c = dst.mean(0)
    t_true = c - Rg @ c + np.array([0.03, -0.02, 0.04])
    src = (dst - t_true) @ Rg                  # dst = Rg·src + t_true
    return src, dst, nrm, Rg, t_true


# --- 1. 点-面 ICP / GICP の小角線形化が世界原点まわりだった -------------------------------------
@pytest.mark.parametrize("offset", [np.zeros(3), np.array([1e3, 1e3, 0.0]), np.array([5e5, 4e6, 50.0])])
def test_icp_point2plane_is_translation_invariant(offset):
    src, dst, nrm, Rg, tt = _pair(offset)
    R, t, aligned, rmse, _ = match3d.icp_point2plane(src, dst, nrm, iters=30)
    rot, tr = metrics3d.pose_error(R, t, Rg, tt)
    assert rot < 1e-4                          # 旧: offset 1e3 で 23.6°
    assert tr < 1e-6 * max(1.0, float(np.abs(offset).max()))
    assert np.allclose(aligned, src @ R.T + t, atol=1e-6 * max(1.0, float(np.abs(offset).max())))


@pytest.mark.parametrize("offset", [np.zeros(3), np.array([1e3, 1e3, 0.0]), np.array([1e4, 1e4, 0.0])])
def test_gicp_is_translation_invariant(offset):
    src, dst, _, Rg, tt = _pair(offset)
    out = gicp.gicp(src, dst)
    rot, _ = metrics3d.pose_error(out["R"], out["t"], Rg, tt)
    assert rot < 1e-3                          # 旧: offset 1e3 で 20.3°
    assert out["rmse"] < 1e-6


def test_icp_point2plane_init_is_world_frame():
    """init=(R0,t0) は世界座標の姿勢のまま受け取る(中心化は内部だけ)。"""
    src, dst, nrm, Rg, tt = _pair(np.array([1e3, -2e3, 5.0]))
    R, t, *_ = match3d.icp_point2plane(src, dst, nrm, iters=30, init=(Rg, tt))
    rot, tr = metrics3d.pose_error(R, t, Rg, tt)
    assert rot < 1e-6 and tr < 1e-6


# --- 2. 球・円筒の代数フィットが未中心化で桁落ち -----------------------------------------------
def _sphere_pts(c, r, n=400, seed=1):
    d = np.random.default_rng(seed).normal(size=(n, 3))
    return c + r * d / np.linalg.norm(d, axis=1, keepdims=True)


@pytest.mark.parametrize("off", [0.0, 1e6])
def test_sphere_fits_far_from_origin(off):
    c = np.array([off, -off, 0.5 * off])
    P = _sphere_pts(c, 0.05)
    cm, rm = match3d.fit_sphere_3d(P)
    m3 = measure3d.fit_sphere3(P)
    rs = ransac_fit.ransac_sphere(P, 0.001)
    assert abs(rm - 0.05) < 1e-9               # 旧: offset 1e6 で 7.5e5 ずれた
    assert abs(m3["r"] - 0.05) < 1e-9 and m3["rms"] < 1e-9
    assert abs(rs[0]["radius"] - 0.05) < 1e-9 and rs[2]["n_inliers"] == 400
    assert np.allclose(cm, c, atol=1e-8 * max(1.0, off))
    assert np.allclose(rs[0]["center"], c, atol=1e-8 * max(1.0, off))


@pytest.mark.parametrize("off", [0.0, 1e6])
def test_ransac_cylinder_far_from_origin(off):
    rng = np.random.default_rng(2)
    th = rng.uniform(0, 2 * np.pi, 300)
    z = rng.uniform(-1, 1, 300)
    P = np.c_[0.05 * np.cos(th), 0.05 * np.sin(th), z] + [off, off, 0.0]
    N = np.c_[np.cos(th), np.sin(th), 0 * z]
    p, mask, info = ransac_fit.ransac_cylinder(P, N, 0.001)
    assert abs(p["radius"] - 0.05) < 1e-9      # 旧: offset 1e6 で 7e5 ずれた
    assert info["n_inliers"] == 300


# --- 3. PnP の DLT 脱正規化が原点から遠いと破綻 ----------------------------------------------
@pytest.mark.parametrize("off", [0.0, 1e4, 1e6])
def test_pnp_far_from_origin(off):
    rng = np.random.default_rng(0)
    K = np.array([[800, 0, 320], [0, 800, 240], [0, 0, 1.0]])
    X = np.c_[rng.uniform(-2, 2, 60), rng.uniform(-1.5, 1.5, 60), rng.uniform(4, 9, 60)]
    x = (X @ K.T)[:, :2] / X[:, 2:] + rng.normal(0, 0.5, (60, 2))
    Xw = X + off
    t_true = -np.full(3, off)
    R, t, rms = pnp3d.pnp_pose(Xw, x, K)
    rot, _ = metrics3d.pose_error(R, t, np.eye(3), t_true)
    assert rot < 0.2                           # 旧: offset 1e4 で 174.7°
    assert rms < 1.0
    R2, t2 = pnp3d.dlt_pose(Xw, x, K)
    assert metrics3d.pose_error(R2, t2, np.eye(3), t_true)[0] < 0.2


# --- 4. 正中面: 中点がほぼ一直線だと 90° ずれた面 -------------------------------------------
def test_mirror_plane_near_collinear_midpoints():
    L = np.array([[-1, 0, 0.0], [-2, 0, 1.0], [-1.5, 0, 2.0]])
    R = L * [-1, 1, 1]
    R[0, 0] += 0.3                             # 右の 0 番が外へ 0.3 張り出す
    P = np.vstack([L, R])
    P[:, 1] += np.array([0, 1e-9, 0, 0, 0, 0])
    n = shapestats.mirror_plane_from_pairs(P)[1]
    assert abs(n[0]) > np.cos(np.radians(10))  # 旧: (0, 1, 0)
    assert n[0] > 0                            # 左→右の向き


def test_mirror_plane_regular_case_unchanged():
    rng = np.random.default_rng(0)
    L = np.c_[-rng.uniform(1, 2, 6), rng.uniform(-1, 1, 6), rng.uniform(-1, 1, 6)]
    R = L * [-1, 1, 1]
    pl = shapestats.mirror_plane_from_pairs(np.vstack([L, R]))
    assert np.allclose(pl[1], [1, 0, 0], atol=1e-12)
    assert abs(pl[0][0]) < 1e-12


def test_mirror_plane_undetermined_is_rejected():
    # 中点が z 軸上に一直線、左→右も z 方向 —— 面は決まらない
    L = np.array([[0, 0, 0.0], [0, 0, 1.0], [0, 0, 2.0]])
    R = L + [0, 0, 0.5]
    with pytest.raises(ValueError):
        shapestats.mirror_plane_from_pairs(np.vstack([L, R]))


# --- 5. ジンバルロックでのオイラー角 -----------------------------------------------------------
@pytest.mark.parametrize("ry", [90.0, -90.0, 89.9999, 45.0, 0.0])
def test_euler_roundtrip_including_gimbal_lock(ry):
    R = Rot.from_euler("ZYX", [30, ry, 10], degrees=True).as_matrix()
    H = np.eye(4)
    H[:3, :3] = R
    p = pq.hom_mat3d_to_pose_local(H)
    assert np.abs(pq.pose_to_hom_mat3d_local(p)[:3, :3] - R).max() < 1e-9   # 旧: 90° で 0.16
    p2 = pq.quat_to_pose(pq._mat_to_quat(R))
    assert np.abs(pq.pose_to_hom_mat3d_local(p2)[:3, :3] - R).max() < 1e-9


def test_euler_regular_angles_unchanged():
    p = pq.hom_mat3d_to_pose_local(pq.pose_to_hom_mat3d_local([1, 2, 3, 0.1, -0.4, 2.5]))
    assert np.allclose(p, [1, 2, 3, 0.1, -0.4, 2.5], atol=1e-14)


# --- 6. pose_average の符号揃えが w 基準 --------------------------------------------------------
def test_pose_average_across_yaw_180():
    pa = pq.pose_average([[0, 0, 0, 0, 0, np.radians(179)], [0, 0, 0, 0, 0, np.radians(-179)]])
    assert abs(abs(np.degrees(pa[5])) - 180.0) < 1e-9      # 旧: 0°
    assert abs(pa[3]) < 1e-9 and abs(pa[4]) < 1e-9


def test_pose_average_small_angles_unchanged():
    pa = pq.pose_average([[1, 0, 0, 0, 0, 0.1], [3, 0, 0, 0, 0, 0.3]])
    assert np.allclose(pa, [2, 0, 0, 0, 0, 0.2], atol=1e-12)


# --- 7. m3c2_distance(max_depth=None) が球で切っていた --------------------------------------------
def test_m3c2_unlimited_depth_is_a_cylinder():
    rng = np.random.default_rng(0)
    xy = rng.uniform(-5, 5, (3000, 2))
    a = np.c_[xy, np.zeros(len(xy))]
    b = np.c_[xy, np.full(len(xy), 2.0)]
    cores = np.array([[0, 0, 0.0], [1, 1, 0]])
    nrm = np.array([[0, 0, 1.0], [0, 0, 1]])
    d, lod = metrics3d.m3c2_distance(a, b, cores, nrm, radius=0.5)
    assert np.allclose(d, 2.0) and np.allclose(lod, 0.0)   # 旧: nan
    d5, _ = metrics3d.m3c2_distance(a, b, cores, nrm, radius=0.5, max_depth=5)
    assert np.allclose(d5, 2.0)
    d1, _ = metrics3d.m3c2_distance(a, b, cores, nrm, radius=0.5, max_depth=1)
    assert np.isnan(d1).all()                  # 有限の深さでは従来どおり切る


# --- 8. fit_zernike の隠れた瞳半径 --------------------------------------------------------------
def test_fit_zernike_explicit_pupil():
    requires_backend("torch")
    H = W = 129
    y, x = np.mgrid[0:H, 0:W].astype(float)
    c = (H - 1) / 2
    rad = (H - 1) / 2
    rho = np.hypot(y - c, x - c) / rad
    Z = 2 * rho ** 2 - 1
    old = match3d.fit_zernike(Z, n_max=4)
    assert abs(old[(2, 0)] - 0.984) < 2e-3     # 既定は従来どおり(瞳半径 min/2-1)
    new = match3d.fit_zernike(Z, n_max=4, radius=rad)
    assert abs(new[(2, 0)] - 1.0) < 1e-4
    assert abs(new[(0, 0)]) < 1e-3
    new2 = match3d.fit_zernike(Z, n_max=4, center=(c, c), radius=rad)
    assert new2 == new
    with pytest.raises(ValueError):
        match3d.fit_zernike(Z, n_max=4, radius=H)          # 瞳が画像からはみ出す
    with pytest.raises(ValueError):
        match3d.fit_zernike(Z, n_max=4, radius=-1.0)


def test_fit_zernike_default_pupil_unchanged():
    requires_backend("torch")
    H = W = 129
    y, x = np.mgrid[0:H, 0:W].astype(float)
    c = (H - 1) / 2
    rho = np.hypot(y - c, x - c) / (min(H, W) / 2 - 1)
    th = np.arctan2(y - c, x - c)
    coef = match3d.fit_zernike(rho ** 2 * np.cos(2 * th), n_max=4)
    assert abs(coef[(2, 2)] - 1.0) < 1e-4


# --- 9. Hough 球・平面の半 voxel の偏り -----------------------------------------------------------
def test_hough_sphere_radius_unbiased():
    requires_backend("torch")
    z, y, x = np.mgrid[0:40, 0:40, 0:40].astype(float)
    d = np.sqrt((z - 19.7) ** 2 + (y - 20.2) ** 2 + (x - 19.4) ** 2)
    vol = np.clip(10.0 + 0.5 - d, 0, 1)          # iso 0.5 の面が半径 10
    _, r, _ = match3d.hough_sphere_3d(vol, radii=range(4, 16))
    assert abs(r - 10.0) < 0.3                  # 旧: 9.27
    _, r2, _ = match3d.hough_sphere_3d(1.0 - vol, radii=range(4, 16))
    assert abs(r2 - 10.0) < 0.3                 # 暗球(穴)も同じ式で


def test_hough_plane_axis_aligned_is_exact():
    requires_backend("torch")
    z, y, x = np.mgrid[0:32, 0:32, 0:32].astype(float)
    vol = np.clip(x - 20.5 + 0.5, 0, 1)          # iso 面は x = 20.5
    n, d, _, _ = match3d.hough_plane_3d(vol)
    assert np.allclose(np.abs(n), [0, 0, 1], atol=1e-6)
    assert abs(d - 20.5) < 0.05                 # 旧: 21.0


# --- 10. ransac_sphere が同一平面の点を受け入れていた ---------------------------------------------
def test_ransac_sphere_rejects_coplanar_points():
    rng = np.random.default_rng(1)
    P = np.c_[rng.uniform(-1, 1, (200, 2)), np.zeros(200)]
    with pytest.raises(ValueError):
        ransac_fit.ransac_sphere(P, 0.01)


# --- 11. dual_quat_to_screw が純並進を失う ------------------------------------------------------
def test_dual_quat_to_screw_pure_translation():
    s = pq.dual_quat_to_screw(pq.pose_to_dual_quat([5, 0, 0, 0, 0, 0]))
    assert s["theta"] == 0.0 and abs(s["d"] - 5.0) < 1e-12   # 旧: d = 0, axis = 0
    assert np.allclose(s["axis"], [1, 0, 0])
    s2 = pq.dual_quat_to_screw(pq.screw_to_dual_quat(0, 3, 4, 0, 0, 0, theta=0.0, d=2.0))
    assert abs(s2["d"] - 2.0) < 1e-12 and np.allclose(s2["axis"], [0, 0.6, 0.8])
    s0 = pq.dual_quat_to_screw(pq.pose_to_dual_quat([0, 0, 0, 0, 0, 0]))
    assert s0["d"] == 0.0 and np.allclose(s0["axis"], 0.0)


def test_dual_quat_to_screw_with_rotation_unchanged():
    s = pq.dual_quat_to_screw(pq.screw_to_dual_quat(0, 0, 1, 0, 0, 0, theta=0.7, d=2.0))
    assert abs(s["theta"] - 0.7) < 1e-12 and abs(s["d"] - 2.0) < 1e-9
    assert np.allclose(s["axis"], [0, 0, 1], atol=1e-9)


# --- 12. pose_error / rotation_translation_error の arccos の床 -----------------------------------
@pytest.mark.parametrize("deg", [1e-7, 1e-5, 1.0, 90.0, 179.9, 180.0])
def test_rotation_angle_has_no_acos_floor(deg):
    R = Rot.from_rotvec([0, 0, np.radians(deg)]).as_matrix()
    rot, _ = metrics3d.pose_error(R, np.zeros(3), np.eye(3), np.zeros(3))
    assert abs(rot - deg) <= 1e-9 * max(1.0, deg) + 1e-12  # 旧: 1e-7° を 0 と答えた
    T = np.eye(4)
    T[:3, :3] = R
    rre, rte = registration_eval.rotation_translation_error(np.eye(4), T)
    assert abs(rre - deg) <= 1e-9 * max(1.0, deg) + 1e-12
    assert rte == 0.0


# --- 13. torus_sdf: スピンドルトーラスの内側は厳密でない(下界) ------------------------------------
def test_torus_sdf_spindle_interior_is_a_lower_bound():
    f = float(sdf_ops.torus_sdf(np.zeros((1, 3)), (0, 0, 0), (0, 0, 1), 1.0, 2.0).ravel()[0])
    assert f == -1.0
    # 真値: 原点から境界(芯線までの距離 = 2 の面のうち、他の管に覆われない部分)までの最短距離
    th = np.linspace(0, 2 * np.pi, 4001)
    r = 1.0 + 2.0 * np.cos(th)
    zz = 2.0 * np.sin(th)
    keep = r >= 0
    true = -float(np.min(np.hypot(r[keep], zz[keep])))
    assert abs(true + np.sqrt(3.0)) < 1e-3
    assert true < f < 0.0                      # 符号は正しく、絶対値は真の距離の下界
    assert "厳密なのは" in sdf_ops.torus_sdf.__doc__
    # 通常のトーラス(minor < major)では厳密: 中心から管の内面まで
    g = sdf_ops.torus_sdf(np.array([[0.0, 0, 0], [2.0, 0, 0]]), (0, 0, 0), (0, 0, 1), 2.0, 0.5)
    assert np.allclose(g, [1.5, -0.5])
