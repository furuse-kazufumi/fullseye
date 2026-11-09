"""敵対的点検(2026-11-09, g1_geom3d)で見つかった「黙って間違う」箇所の回帰テスト。

各テストは点検の探針と同じ場面をこのファイルの中に書いて使い、
直す前は落ち、直した後は通ることを確かめてある。
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy import ndimage

import camera
import measure
import pointcloud

# --------------------------------------------------------------------------- #
# camera.normals_from_depth: 無効画素は NaN(docstring の約束)
# --------------------------------------------------------------------------- #
_K = np.array([[300.0, 0.0, 159.5], [0.0, 300.0, 119.5], [0.0, 0.0, 1.0]])


def _tilted_plane():
    v, u = np.mgrid[0:240, 0:320].astype(float)
    return 1.0 + 0.3 * (u - 160) / 300.0


@pytest.mark.parametrize("fill", [np.nan, 0.0])
def test_normals_from_depth_invalid_pixels_are_nan(fill):
    Z = _tilted_plane()
    holes = np.random.default_rng(2).random(Z.shape) < 0.01
    n = camera.normals_from_depth(np.where(holes, fill, Z), _K)
    # 直す前: 穴 735 画素中 696 画素が有限の法線を持ち、696 画素すべてがカメラと逆向き
    assert np.isnan(n[holes]).all()
    X = camera.depth_to_points(Z, _K, organized=True)
    fin = np.isfinite(n[..., 0])
    assert fin.sum() > 0.9 * Z.size * 0.95
    assert (np.einsum("...i,...i->...", n, X)[fin] <= 0).all()


def _box_scene():
    Z = np.full((240, 320), 1.0)
    v, u = np.mgrid[0:240, 0:320].astype(float)
    box = (abs(u - 159.5) < 50) & (abs(v - 119.5) < 40)
    Z[box] = 0.8
    return Z, box


def test_normals_from_depth_edgeaware_step_band():
    Z, box = _box_scene()
    band = (box ^ ndimage.binary_erosion(box)) | (ndimage.binary_dilation(box) & ~box)
    # 既存 op: 縁の 716 画素で誤差中央値 80 度(契約 op は変えない)
    n0 = camera.normals_from_depth(Z, _K)
    a0 = np.degrees(np.arccos(np.clip(-n0[..., 2], -1, 1)))
    assert np.nanmedian(a0[band]) > 30
    n = camera.normals_from_depth_edgeaware(Z, _K)
    a = np.degrees(np.arccos(np.clip(-n[..., 2], -1, 1)))
    ok = np.isnan(a) | (a < 2.0)
    assert ok[band].all()
    # 縁の帯を捨てすぎていない(片側差分で埋まる)
    assert np.isfinite(a[band]).mean() > 0.95
    # 段差の無い所はどこでも正しい
    inner = np.isfinite(a)
    assert (a[inner] < 2.0).all()


def test_normals_from_depth_edgeaware_matches_op_without_steps():
    Z = _tilted_plane()
    n0 = camera.normals_from_depth(Z, _K)
    n1 = camera.normals_from_depth_edgeaware(Z, _K)
    both = np.isfinite(n0[..., 0])
    assert both.sum() > 0.95 * Z.size
    assert np.abs(n0[both] - n1[both]).max() < 1e-12
    # 画像の縁は片側差分で埋まる(既存 op は NaN)
    assert np.isfinite(n1[0, 1:-1]).all()


def test_normals_from_depth_edgeaware_invalid_and_args():
    Z = _tilted_plane()
    Z[10, 10] = np.nan
    Z[20, 20] = 0.0
    n = camera.normals_from_depth_edgeaware(Z, _K)
    assert np.isnan(n[10, 10]).all() and np.isnan(n[20, 20]).all()
    assert np.isfinite(n[10, 11]).all()          # 隣は片側差分で生きる
    with pytest.raises(ValueError):
        camera.normals_from_depth_edgeaware(Z, _K, max_jump_rel=0.0)
    with pytest.raises(ValueError):
        camera.normals_from_depth_edgeaware(Z[0], _K)


# --------------------------------------------------------------------------- #
# pointcloud.voxel_downsample: NaN 1 点で出力が NaN 1 点になっていた
# --------------------------------------------------------------------------- #
def _pb():
    """poc_registration_basin の場面(当て金・回転・誤差の定義)を借りる。"""
    import os
    import sys
    ex = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
    if ex not in sys.path:
        sys.path.insert(0, ex)
    import poc_registration_basin as pb
    return pb


def _bracket(n, rng):
    return _pb().bracket(n, rng)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_voxel_downsample_rejects_non_finite(bad):
    P = _bracket(20000, np.random.default_rng(3))
    ref = pointcloud.voxel_downsample(P[1:], 0.05)
    assert ref.shape[0] > 100 and np.isfinite(ref).all()
    P[0, 1] = bad
    # 直す前: 出力 shape (1, 3)、その 1 点が NaN(例外も警告も無し)
    with pytest.raises(ValueError, match="non-finite"):
        pointcloud.voxel_downsample(P, 0.05)


@pytest.mark.parametrize("voxel", [np.nan, np.inf])
def test_voxel_downsample_rejects_non_finite_voxel(voxel):
    P = np.random.default_rng(0).random((50, 3))
    with pytest.raises(ValueError):
        pointcloud.voxel_downsample(P, voxel)


# --------------------------------------------------------------------------- #
# ppf.surface_match / find_surface_pose: 場面側の法線をモデル側と同じ向き付きに
# --------------------------------------------------------------------------- #
def _ppf_trials(n, rng_seed=7):
    """当て金 325 点 x 2(片方を最遠点 250 点でモデル)、回転 30-180 度の場面を n 個。"""
    from registration import apply_transform
    from pcseg import farthest_point_sampling
    pb = _pb()
    rng = np.random.default_rng(rng_seed)
    for _ in range(n):
        m = pb.bracket(325, rng)
        s = pb.bracket(325, rng)
        m = m[farthest_point_sampling(m, 250)]
        Rt = pb.random_rot(float(rng.uniform(30, 180)), rng)
        tt = rng.normal(size=3)
        yield pb, m, apply_transform(s, Rt, tt), Rt, tt


def _ppf_success(pb, out, m, Rt, tt):
    rd = pb.rot_error_deg(out["R"], Rt)
    cd = pb.cen_error(out["R"], out["t"], Rt, tt, m.mean(0))
    return rd < 5.0 and cd < 0.03 * pb.diameter(m)


def test_find_surface_pose_default_success_rate():
    """公開の挙動だけで見る: 既定の呼び出し find_surface_pose(model, scene) の成功率。

    直す前(master、場面だけ符号任意の PCA 法線): 種 7 の 48 試行で 54 %。
    ★2 回目の独立レビュー: 種 1 本(48 試行)では 0.75 ちょうどの種があり境目だった。
    種 4 本(1〜4、計 192 試行)をまとめて見る。実測は種ごとに 0.75 / 0.94 / 0.85 / 0.79、
    まとめて 0.83(閾値は下げていない)。"""
    import ppf
    succ = [_ppf_success(pb, ppf.find_surface_pose(m, S, angle_bins=24, ref_fraction=0.25, topk=3),
                         m, Rt, tt)
            for seed in (1, 2, 3, 4)
            for pb, m, S, Rt, tt in _ppf_trials(48, rng_seed=seed)]
    assert len(succ) == 192
    assert np.mean(succ) >= 0.75, np.mean(succ)


def test_find_surface_pose_default_survives_a_globally_flipped_scene_orientation(monkeypatch):
    """場面の向き付けが物体ごと裏返った場合(床や他物体を含む場面で起きる)を、向き付けの
    関数(公開モジュール normals_orient)の出力を裏返して再現し、公開の find_surface_pose で見る。

    両符号で投票する前(片方の符号だけ)は、この場面で成功率が大きく落ちる。"""
    import ppf
    import normals_orient
    real = normals_orient.estimate_oriented_normals
    succ = []
    for pb, m, S, Rt, tt in _ppf_trials(24):
        model = ppf.ppf_model(m, angle_bins=24)          # モデル側は通常の向き
        with monkeypatch.context() as mp:                # 場面側の向き付けだけ物体ごと裏返す
            mp.setattr(normals_orient, "estimate_oriented_normals",
                       lambda P, *a, **k: -real(P, *a, **k))
            out = ppf.surface_match(model, S, ref_fraction=0.25, topk=3)
        succ.append(_ppf_success(pb, out, m, Rt, tt))
    # 片方の符号だけで投票すると、裏返った場面では 48 試行で 29 % まで落ちる
    assert np.mean(succ) >= 0.7, np.mean(succ)


# --------------------------------------------------------------------------- #
# measure.fit_rectangle2: 角度の境界 ±90 / 最小二乗の当てはめは別関数
# --------------------------------------------------------------------------- #
def _rect_outline(rng, cx, cy, l1, l2, phi_deg, n, s):
    t = rng.uniform(0, 4, n)
    k = np.floor(t).astype(int)
    f = t - k
    loc = np.empty((n, 2))
    for i in range(n):
        loc[i] = [(-l1 + 2 * l1 * f[i], -l2), (l1, -l2 + 2 * l2 * f[i]),
                  (l1 - 2 * l1 * f[i], l2), (-l1, l2 - 2 * l2 * f[i])][k[i]]
    loc = loc + rng.normal(scale=s, size=(n, 2)) if s > 0 else loc
    ph = np.radians(phi_deg)
    Rm = np.array([[np.cos(ph), -np.sin(ph)], [np.sin(ph), np.cos(ph)]])
    xy = loc @ Rm.T + [cx, cy]
    return np.c_[xy[:, 1], xy[:, 0]]                 # (row, col)


@pytest.mark.parametrize("phi", [90.0, -90.0, 270.0])
def test_fit_rectangle2_vertical_long_side_is_plus_90(phi):
    r = measure.fit_rectangle2(_rect_outline(np.random.default_rng(1), 0, 0, 40, 20, phi, 400, 0.0))
    # 直す前: 入力 -90 度で -90.0 が返った(docstring は (-90, 90])
    assert r["angle_deg"] == 90.0


def test_fit_rectangle2_angle_range_is_half_open():
    rng = np.random.default_rng(4)
    for phi in np.linspace(-180, 180, 73):
        a = measure.fit_rectangle2(_rect_outline(rng, 5, 7, 30, 12, phi, 300, 0.0))["angle_deg"]
        assert -90.0 < a <= 90.0


def test_fit_rectangle2_lsq_unbiased_on_noisy_outline():
    pr = _rect_outline(np.random.default_rng(9), 100, 80, 40, 20, 25, 2000, 1.0)
    mar = measure.fit_rectangle2(pr)
    assert mar["l1"] > 42.0                          # 最小面積の外接矩形は外へ偏る(既存の性質)
    r = measure.fit_rectangle2_lsq(pr)
    assert abs(r["l1"] - 40) < 0.1 and abs(r["l2"] - 20) < 0.1, r
    assert abs(r["angle_deg"] - 25) < 0.1, r
    assert abs(r["cx"] - 100) < 0.1 and abs(r["cy"] - 80) < 0.1, r
    assert 0.8 < r["rms"] < 1.2                      # 雑音 σ=1 px


def test_fit_rectangle2_lsq_ignores_a_far_outlier():
    rng = np.random.default_rng(11)
    pr = np.r_[_rect_outline(rng, 100, 80, 40, 20, 25, 2000, 0.3), [[300.0, 300.0]]]
    assert measure.fit_rectangle2(pr)["l1"] > 100        # 外れ値 1 点で辺長 40 -> 170
    r = measure.fit_rectangle2_lsq(pr)
    assert abs(r["l1"] - 40) < 0.2 and abs(r["l2"] - 20) < 0.2, r
    assert abs(r["angle_deg"] - 25) < 0.2, r


def test_fit_rectangle2_lsq_exact_and_args():
    pr = _rect_outline(np.random.default_rng(2), -3, 4, 15, 15 * 0.6, -60, 500, 0.0)
    r = measure.fit_rectangle2_lsq(pr)
    assert abs(r["l1"] - 15) < 1e-6 and abs(r["l2"] - 9) < 1e-6
    assert abs(r["angle_deg"] - (-60)) < 1e-6 and r["rms"] < 1e-6
    with pytest.raises(ValueError):
        measure.fit_rectangle2_lsq(pr[:2])
    with pytest.raises(ValueError):
        measure.fit_rectangle2_lsq(np.r_[pr, [[np.nan, 0.0]]])


# --------------------------------------------------------------------------- #
# registration.icp / point_to_plane_icp: 対応距離の上限(Open3D の
# max_correspondence_distance)を持つ別関数 icp_gated / point_to_plane_icp_gated
# --------------------------------------------------------------------------- #
def _outlier_trials(n_trials=20):
    """探針 probe_icp.py の outlier20 の場面(当て金 500/700 点 + 一様外れ値 100 点、初期 20 度)。"""
    import pointcloud as pcl
    from registration import apply_transform
    pb = _pb()
    rng = np.random.default_rng(0)
    for _ in range(n_trials):
        src = pb.bracket(500, rng)
        dstb = pb.bracket(700, rng)
        dn_b = pcl.estimate_normals(dstb, k=16)
        diam = pb.diameter(dstb)
        src = np.vstack([src, rng.uniform(-0.8, 0.8, (100, 3))])
        Rt = pb.random_rot(20.0, rng)
        dst = apply_transform(dstb, Rt, np.zeros(3))
        yield src, dst, dn_b @ Rt.T, Rt, diam


def test_point_to_plane_icp_gated_rejects_outliers():
    import registration as reg
    pb = _pb()
    e_old, e_new, fit = [], [], []
    for src, dst, dn, Rt, diam in _outlier_trials():
        e_old.append(pb.rot_error_deg(reg.point_to_plane_icp(src, dst, dst_normals=dn, max_iter=60)[0], Rt))
        R, t, al, rmse, fitness = reg.point_to_plane_icp_gated(src, dst, 0.05 * diam,
                                                                dst_normals=dn, max_iter=60)
        e_new.append(pb.rot_error_deg(R, Rt))
        fit.append(fitness)
    # 契約 op(上限なし)は外れ値 17 % で中央値 27.7 度(Open3D の上限 無限大と同じ)
    assert np.median(e_old) > 10.0
    assert np.median(e_new) < 1.0, np.median(e_new)
    # 外れ値 100/600 点は上限の外 = fitness は 500/600 前後
    assert 0.75 < np.median(fit) < 0.9, np.median(fit)


def test_icp_gated_rejects_outliers():
    import registration as reg
    pb = _pb()
    e_old, e_new = [], []
    for src, dst, dn, Rt, diam in _outlier_trials():
        e_old.append(pb.rot_error_deg(reg.icp(src, dst, max_iter=60)[0], Rt))
        e_new.append(pb.rot_error_deg(reg.icp_gated(src, dst, 0.05 * diam, max_iter=60)[0], Rt))
    assert np.median(e_old) > 3.0                       # 探針: 中央値 4.15 度
    assert np.median(e_new) < 1.5, np.median(e_new)


def test_gated_icp_with_huge_gate_equals_contract_op():
    import registration as reg
    for k, (src, dst, dn, Rt, diam) in enumerate(_outlier_trials(4)):
        for trim in (None, 0.2):
            R0 = reg.icp(src, dst, max_iter=60, trim=trim)[0]
            R1 = reg.icp_gated(src, dst, 1e9, max_iter=60, trim=trim)[0]
            assert np.abs(R0 - R1).max() < 1e-12      # 測地角は arccos で 1e-6 度の床がある
            P0 = reg.point_to_plane_icp(src, dst, dst_normals=dn, max_iter=60, trim=trim)[0]
            P1 = reg.point_to_plane_icp_gated(src, dst, 1e9, dst_normals=dn, max_iter=60,
                                              trim=trim)[0]
            assert np.abs(P0 - P1).max() < 1e-12


def test_gated_icp_fails_closed():
    import registration as reg
    rng = np.random.default_rng(5)
    src = rng.random((50, 3))
    dst = src + 10.0                                       # どの対応も上限 0.1 の外
    for fn in (reg.icp_gated, reg.point_to_plane_icp_gated):
        with pytest.raises(ValueError, match="correspondence"):
            fn(src, dst, 0.1)
        for bad in (0.0, -1.0, np.nan):
            with pytest.raises(ValueError):
                fn(src, src, bad)


# --------------------------------------------------------------------------- #
# 2026-11-09 独立レビュー: trim の範囲と、残す点が少なすぎるとき
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("trim", [1.5, 1.0, -0.5, float("nan")])
def test_icp_family_rejects_trim_out_of_range(trim):
    from registration import icp, point_to_plane_icp, icp_gated, point_to_plane_icp_gated
    rng = np.random.default_rng(0)
    P = rng.random((60, 3))
    Q = P + 0.01
    for call in (lambda: icp(P, Q, trim=trim), lambda: point_to_plane_icp(P, Q, trim=trim),
                 lambda: icp_gated(P, Q, 0.5, trim=trim),
                 lambda: point_to_plane_icp_gated(P, Q, 0.5, trim=trim)):
        with pytest.raises(ValueError, match="trim"):
            call()


def test_gated_icp_stops_when_trim_keeps_too_few_points():
    from registration import icp_gated, point_to_plane_icp_gated
    rng = np.random.default_rng(0)
    P = rng.random((60, 3))
    for f in (icp_gated, point_to_plane_icp_gated):
        with pytest.raises(ValueError, match="at least 3"):
            f(P, P + 0.01, 0.5, trim=0.97)            # 60 点の 3 % = 2 点
    assert np.isfinite(icp_gated(P, P + 0.01, 0.5, trim=0.2)[3])
