# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lidarsim の門: 閉形式(平面 / slab)・力ずくの第 2 実装・spherical_proj との往復・剛体不変・速度。"""
from __future__ import annotations

import time

import numpy as np
import pytest

import lidarsim
import spherical_proj
from lidarsim import (lidar_points_sensor_frame, lidar_range_image_to_points, lidar_scan,
                      lidar_spec, ray_box_ranges, ray_plane_range)

GROUND_Z = -1.7


# ---- 部品 --------------------------------------------------------------------------------------------
def ground_mesh(half: float = 1.0e4, z: float = GROUND_Z):
    """巨大な地面(2 三角形)。"""
    V = np.array([[-half, -half, z], [half, -half, z], [half, half, z], [-half, half, z]])
    F = np.array([[0, 1, 2], [0, 2, 3]])
    return V, F


def box_mesh(box):
    """軸平行箱 (xmin, ymin, zmin, xmax, ymax, zmax) → 8 頂点・12 三角形。"""
    x0, y0, z0, x1, y1, z1 = box
    V = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    F = np.array([[0, 2, 1], [0, 3, 2],        # bottom
                  [4, 5, 6], [4, 6, 7],        # top
                  [0, 1, 5], [0, 5, 4],        # y = y0
                  [2, 3, 7], [2, 7, 6],        # y = y1
                  [1, 2, 6], [1, 6, 5],        # x = x1
                  [3, 0, 4], [3, 4, 7]])       # x = x0
    return V, F


def merge(*meshes):
    Vs, Fs, off = [], [], 0
    for V, F in meshes:
        Vs.append(np.asarray(V, float)); Fs.append(np.asarray(F) + off); off += len(V)
    return np.vstack(Vs), np.vstack(Fs)


def tessellated_ground(size: float = 60.0, nx: int = 40, ny: int = 25, z: float = GROUND_Z):
    """size × size の地面を nx × ny の格子で三角形化(2·nx·ny 三角形)。"""
    xs = np.linspace(-size / 2, size / 2, nx + 1)
    ys = np.linspace(-size / 2, size / 2, ny + 1)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    V = np.stack([X.ravel(), Y.ravel(), np.full(X.size, z)], axis=1)
    i, j = np.meshgrid(np.arange(nx), np.arange(ny), indexing="ij")
    a = (i * (ny + 1) + j).ravel()
    b = a + (ny + 1)
    F = np.vstack([np.stack([a, b, b + 1], axis=1), np.stack([a, b + 1, a + 1], axis=1)])
    return V, F


def random_boxes(n: int, rng, size: float = 60.0):
    meshes = []
    for _ in range(n):
        cx, cy = rng.uniform(-size / 2 + 3, size / 2 - 3, size=2)
        if np.hypot(cx, cy) < 2.0:
            cx += 4.0
        w, d, h = rng.uniform(0.5, 3.0, size=3)
        meshes.append(box_mesh((cx - w / 2, cy - d / 2, GROUND_Z, cx + w / 2, cy + d / 2, GROUND_Z + h)))
    return merge(*meshes)


def dirs_sensor(spec):
    e = spec["elevations"][:, None]
    a = spec["azimuths"][None, :]
    return np.stack([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a),
                     np.broadcast_to(np.sin(e), (len(spec["elevations"]), len(spec["azimuths"])))], axis=2)


def brute_force_ranges(V, F, spec, T):
    """加速なしの第 2 実装: 全レイ × 全三角形を Möller–Trumbore(numpy、三角形ごとにループ)。"""
    R, t = T[:3, :3], T[:3, 3]
    Vs = (np.asarray(V, float) - t) @ R
    D = dirs_sensor(spec).reshape(-1, 3)
    best = np.full(D.shape[0], np.inf)
    face = np.full(D.shape[0], -1)
    for fi, (i0, i1, i2) in enumerate(F):
        v0, v1, v2 = Vs[i0], Vs[i1], Vs[i2]
        e1, e2 = v1 - v0, v2 - v0
        pvec = np.cross(D, e2)
        det = pvec @ e1
        ok = np.abs(det) > 1e-12
        inv = 1.0 / np.where(ok, det, 1.0)
        u = (pvec @ (-v0)) * inv
        qvec = np.cross(-v0, e1)
        v = (D @ qvec) * inv
        tt = (qvec @ e2) * inv
        ok &= (u >= -1e-9) & (u <= 1 + 1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (tt > 0)
        better = ok & (tt < best)
        best[better] = tt[better]
        face[better] = fi
    keep = np.isfinite(best) & (best >= spec["range_min"]) & (best <= spec["range_max"])
    out = np.where(keep, best, 0.0)
    return out.reshape(spec["n_beams"], spec["n_az"]), np.where(keep, face, -1).reshape(spec["n_beams"], spec["n_az"])


def rot_z(yaw):
    c, s = np.cos(yaw), np.sin(yaw)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def random_rotation(rng):
    q = rng.normal(size=4)
    q /= np.linalg.norm(q)
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def pose(R=None, t=(0.0, 0.0, 0.0)):
    T = np.eye(4)
    if R is not None:
        T[:3, :3] = R
    T[:3, 3] = t
    return T


# ---- 仕様と並び --------------------------------------------------------------------------------------
def test_spec_layout_matches_spherical_proj_bins():
    spec = lidar_spec()
    assert spec["n_beams"] == 32 and spec["n_az"] == 1800
    v_min, v_max = np.radians(-25.0), np.radians(15.0)
    de = (v_max - v_min) / 32
    np.testing.assert_allclose(spec["elevations"], v_max - (np.arange(32) + 0.5) * de, atol=1e-15)
    assert spec["elevations"][0] > spec["elevations"][-1]          # 行 0 = 上端
    # 列の中心 = spherical_proj.unproject_spherical が使う (c + 0.5)/h_res · 2π − π
    img = np.zeros((32, 1800)); img[0, :] = 1.0
    pts = spherical_proj.unproject_spherical(img, v_fov=(-25.0, 15.0))
    az = np.arctan2(pts[:, 1], pts[:, 0])
    np.testing.assert_allclose(az, spec["azimuths"], atol=1e-12)
    el = np.arctan2(pts[:, 2], np.hypot(pts[:, 0], pts[:, 1]))
    np.testing.assert_allclose(el, spec["elevations"][0], atol=1e-12)
    assert abs(spec["azimuths"][900] - np.pi / 1800) < 1e-15    # 中央列は前方 (+x) の直近
    assert spec["azimuths"][0] < 0 and abs(spec["azimuths"][0] + np.pi) < 2 * np.pi / 1800


@pytest.mark.parametrize("bad", [
    dict(n_beams=0), dict(azimuth_res_deg=0.0), dict(azimuth_res_deg=-1.0), dict(azimuth_res_deg=0.7),
    dict(range_max=0.5, range_min=0.5), dict(range_max=0.2, range_min=0.5), dict(range_min=-1.0),
    dict(v_fov_deg=(15.0, -25.0)), dict(v_fov_deg=(-100.0, 10.0)), dict(noise_std=-0.1),
    dict(range_max=np.inf),
])
def test_spec_bad_inputs(bad):
    with pytest.raises(ValueError):
        lidar_spec(**bad)


# ---- 地面(平面の閉形式) -----------------------------------------------------------------------------
def test_ground_plane_matches_closed_form():
    spec = lidar_spec(range_max=1.0e4, range_min=0.1)
    V, F = ground_mesh()
    T = np.eye(4)
    scan = lidar_scan(V, F, spec, T)
    D = dirs_sensor(spec)
    e = spec["elevations"]
    ranges = scan["ranges"]
    neg = e < 0
    # 閉形式 1: 1.7 / (−sin e)
    expect = -GROUND_Z / (-np.sin(e[neg]))
    np.testing.assert_allclose(ranges[neg], np.repeat(expect[:, None], spec["n_az"], axis=1), rtol=0, atol=1e-9)
    # 閉形式 2: ray_plane_range
    plane_r = ray_plane_range(T[:3, 3], D, (0.0, 0.0, 1.0, -GROUND_Z))
    np.testing.assert_allclose(ranges[neg], plane_r[neg], rtol=0, atol=1e-9)
    assert np.all(ranges[~neg] == 0.0) and np.all(np.isinf(plane_r[~neg]))
    assert scan["n_hits"] == int(neg.sum()) * spec["n_az"]
    assert np.all(scan["hit_face"][neg] >= 0) and np.all(scan["hit_face"][~neg] == -1)
    # points は世界座標で z = −1.7
    np.testing.assert_allclose(scan["points"][:, 2], GROUND_Z, atol=1e-9)
    assert scan["beam"].shape == (scan["n_hits"],) and scan["col"].shape == (scan["n_hits"],)
    assert np.all(scan["ranges"][scan["beam"], scan["col"]] > 0)


# ---- 箱(slab 法) ------------------------------------------------------------------------------------
@pytest.mark.parametrize("box", [
    (5.0, -1.0, -1.7, 7.0, 1.0, 0.3),          # 前方
    (-7.0, -1.5, -1.7, -5.0, 1.5, 0.5),        # 後方(方位 ±π を跨ぐ)
    (-0.6, 3.0, -1.0, 0.6, 5.0, 1.0),          # 左(方位 +π/2 付近)
    (2.0, -0.5, 0.2, 3.0, 0.5, 0.5),           # 上方の小箱
])
def test_box_matches_slab(box):
    spec = lidar_spec(range_min=0.1)
    V, F = box_mesh(box)
    T = np.eye(4)
    scan = lidar_scan(V, F, spec, T)
    slab = ray_box_ranges(T[:3, 3], dirs_sensor(spec), box)
    hit_scan = scan["ranges"] > 0
    hit_slab = np.isfinite(slab)
    assert hit_slab.sum() > 20, "the box must be visible to enough rays for the test to mean anything"
    assert np.array_equal(hit_scan, hit_slab), "hit cell sets differ: %d vs %d" % (hit_scan.sum(), hit_slab.sum())
    np.testing.assert_allclose(scan["ranges"][hit_scan], slab[hit_slab], rtol=0, atol=1e-9)


def test_occlusion_box_shadows_ground():
    spec = lidar_spec(range_max=200.0, range_min=0.1)
    box = (5.0, -1.0, GROUND_Z, 7.0, 1.0, GROUND_Z + 2.0)
    Vg, Fg = ground_mesh(half=200.0)
    Vb, Fb = box_mesh(box)
    V, F = merge((Vg, Fg), (Vb, Fb))
    T = np.eye(4)
    D = dirs_sensor(spec)
    both = lidar_scan(V, F, spec, T, labels=np.array([0] * 2 + [6] * 12))
    ground_only = lidar_scan(Vg, Fg, spec, T)
    slab = ray_box_ranges(T[:3, 3], D, box)
    plane = ray_plane_range(T[:3, 3], D, (0.0, 0.0, 1.0, -GROUND_Z))
    in_box = np.isfinite(slab)
    shadow = in_box & np.isfinite(plane) & (plane > slab)      # 箱の後ろに地面があるセル
    assert shadow.sum() > 50
    np.testing.assert_allclose(both["ranges"][shadow], slab[shadow], atol=1e-9)
    assert np.all(both["ranges"][shadow] < ground_only["ranges"][shadow])     # 箱の方が近い
    assert np.all(both["labels"][shadow] == 6) and np.all(both["hit_face"][shadow] >= 2)
    # 箱に当たらないセルは地面だけのスキャンと同じ
    np.testing.assert_allclose(both["ranges"][~in_box], ground_only["ranges"][~in_box], atol=1e-12)
    assert np.all(both["labels"][~in_box & (ground_only["ranges"] > 0)] == 0)
    # 箱の輪郭で range が不連続に飛ぶ(影の穴)
    row = int(np.flatnonzero(shadow.any(axis=1))[len(np.flatnonzero(shadow.any(axis=1))) // 2])
    jumps = np.abs(np.diff(both["ranges"][row]))
    assert jumps.max() > 1.0


# ---- 力ずくの第 2 実装との一致(加速の門) --------------------------------------------------------------
def test_matches_brute_force_random_scene():
    rng = np.random.default_rng(7)
    spec = lidar_spec(range_min=0.3, range_max=40.0)
    tris = rng.uniform(-8, 8, size=(40, 3, 3))
    tris[:, :, 2] *= 0.4
    V = tris.reshape(-1, 3)
    F = np.arange(120).reshape(40, 3)
    T = pose(random_rotation(rng), rng.uniform(-1, 1, size=3))
    scan = lidar_scan(V, F, spec, T)
    ref, ref_face = brute_force_ranges(V, F, spec, T)
    assert (ref > 0).sum() > 500
    assert np.array_equal(scan["ranges"] > 0, ref > 0)
    np.testing.assert_allclose(scan["ranges"], ref, atol=1e-9)
    assert np.array_equal(scan["hit_face"], ref_face)


def test_matches_brute_force_edge_over_sensor():
    """辺がセンサの真上近くを通る三角形: 頂点の仰角(5.7°)より高い行(〜15°)にも当たる。"""
    spec = lidar_spec(range_min=0.1)
    # 3 頂点とも仰角 ±5.7°(第 3 頂点 (0, 3, 0.3) も同じ 5.71°)だが、長辺は (0, 0.2, 1) を通り 78.7°。
    V = np.array([[10.0, 0.2, 1.0], [-10.0, 0.2, 1.0], [0.0, 3.0, 0.3],
                  [10.0, -0.2, -1.0], [-10.0, -0.2, -1.0], [0.0, -3.0, -0.3]])
    F = np.array([[0, 1, 2], [3, 4, 5]])
    T = np.eye(4)
    scan = lidar_scan(V, F, spec, T)
    ref, ref_face = brute_force_ranges(V, F, spec, T)
    el_v = np.degrees(np.arcsin(V[:, 2] / np.linalg.norm(V, axis=1)))
    assert np.all(np.abs(np.abs(el_v) - 5.71) < 0.05), "probe premise: every vertex sits at |el| = 5.7 deg"
    top_rows = np.degrees(spec["elevations"]) > 5.71 + 1.0
    bot_rows = np.degrees(spec["elevations"]) < -5.71 - 1.0
    assert (ref[top_rows] > 0).sum() > 0, "the reference must hit above the vertex elevation"
    assert (ref[bot_rows] > 0).sum() > 0, "the reference must hit below the vertex elevation"
    assert np.array_equal(scan["ranges"] > 0, ref > 0)
    np.testing.assert_allclose(scan["ranges"], ref, atol=1e-9)
    assert np.array_equal(scan["hit_face"], ref_face)


def test_matches_brute_force_boxes_and_ground():
    rng = np.random.default_rng(3)
    spec = lidar_spec(n_beams=16, azimuth_res_deg=1.0, range_min=0.5, range_max=60.0)
    V, F = merge(tessellated_ground(nx=8, ny=8), random_boxes(15, rng))
    T = pose(rot_z(0.3), (1.0, -2.0, 0.0))
    scan = lidar_scan(V, F, spec, T)
    ref, ref_face = brute_force_ranges(V, F, spec, T)
    assert np.array_equal(scan["ranges"] > 0, ref > 0)
    np.testing.assert_allclose(scan["ranges"], ref, atol=1e-9)
    assert np.array_equal(scan["hit_face"], ref_face)


# ---- 剛体不変 ----------------------------------------------------------------------------------------
def test_rigid_motion_invariance():
    rng = np.random.default_rng(11)
    spec = lidar_spec(range_min=0.3)
    V, F = merge(tessellated_ground(nx=6, ny=6), random_boxes(30, rng))
    T0 = pose(rot_z(-0.4), (0.5, 0.2, 0.3))
    base = lidar_scan(V, F, spec, T0)
    assert base["n_hits"] > 1000
    for _ in range(3):
        Rg, tg = random_rotation(rng), rng.uniform(-50, 50, size=3)
        Tg = pose(Rg, tg)
        moved = lidar_scan(V @ Rg.T + tg, F, spec, Tg @ T0)
        assert moved["n_hits"] == base["n_hits"]
        np.testing.assert_allclose(moved["ranges"], base["ranges"], rtol=0, atol=1e-9)
        assert np.array_equal(moved["hit_face"], base["hit_face"])
        np.testing.assert_allclose(lidar_points_sensor_frame(moved, Tg @ T0),
                                   lidar_points_sensor_frame(base, T0), atol=1e-8)


# ---- spherical_proj との往復 --------------------------------------------------------------------------
def test_round_trip_through_spherical_proj():
    rng = np.random.default_rng(5)
    spec = lidar_spec(range_min=0.3)
    V, F = merge(tessellated_ground(nx=10, ny=10), random_boxes(40, rng))
    T = pose(rot_z(0.7), (2.0, 1.0, 0.1))
    scan = lidar_scan(V, F, spec, T)
    pts_s = lidar_points_sensor_frame(scan, T)
    img = spherical_proj.project_spherical(pts_s, h_res=spec["n_az"], v_res=spec["n_beams"],
                                           v_fov=spec["v_fov_deg"])
    hit = scan["ranges"] > 0
    mismatch = np.count_nonzero((img > 0) != hit)
    frac = mismatch / hit.size
    assert frac <= 0.01, "round-trip cell mismatch %.5f (%d cells)" % (frac, mismatch)
    print("\nround-trip mismatch vs spherical_proj: %d / %d cells = %.6f" % (mismatch, hit.size, frac))
    same = (img > 0) & hit
    np.testing.assert_allclose(img[same], scan["ranges"][same], atol=1e-9)
    # 逆投影(spherical_proj に委譲)はセンサ座標の反射点そのもの
    back = lidar_range_image_to_points(scan["ranges"], spec)
    np.testing.assert_allclose(back, pts_s, atol=1e-9)
    with pytest.raises(ValueError):
        lidar_range_image_to_points(scan["ranges"][:, :10], spec)


# ---- 測距範囲・ノイズ・ラベル ---------------------------------------------------------------------------
def test_range_clip():
    V, F = ground_mesh()
    T = np.eye(4)
    full = lidar_scan(V, F, lidar_spec(range_max=1.0e4, range_min=0.1), T)
    spec = lidar_spec(range_max=20.0, range_min=3.0)
    clipped = lidar_scan(V, F, spec, T)
    r = full["ranges"]
    keep = (r >= 3.0) & (r <= 20.0)
    assert keep.any() and (~keep & (r > 0)).any()
    np.testing.assert_allclose(clipped["ranges"][keep], r[keep], atol=1e-12)
    assert np.all(clipped["ranges"][~keep] == 0.0)
    assert np.all(clipped["hit_face"][~keep] == -1) and np.all(clipped["labels"][~keep] == -1)
    assert clipped["n_hits"] == int(keep.sum())
    # 近すぎる最近接面は奥へ抜けない(箱の直前にある小面が地面を塞ぐ)
    Vb, Fb = box_mesh((0.3, -0.05, -0.05, 0.4, 0.05, 0.05))
    spec2 = lidar_spec(range_max=100.0, range_min=1.0)
    s2 = lidar_scan(*merge((V, F), (Vb, Fb)), spec2, T)
    cell = (15, 900)     # 正面やや下(仰角 −4.4°)、箱の面が 0.3 m にある
    assert np.isfinite(ray_box_ranges(np.zeros(3), dirs_sensor(spec2)[cell], (0.3, -0.05, -0.05, 0.4, 0.05, 0.05)))
    assert s2["ranges"][cell] == 0.0


def test_noise_seeded_and_zero_is_bit_exact():
    rng = np.random.default_rng(1)
    V, F = merge(tessellated_ground(nx=5, ny=5), random_boxes(10, rng))
    T = pose(rot_z(0.2), (0.0, 0.0, 0.5))
    clean = lidar_spec()
    a = lidar_scan(V, F, clean, T, seed=0)
    b = lidar_scan(V, F, clean, T, seed=99)
    assert np.array_equal(a["ranges"], b["ranges"]) and np.array_equal(a["points"], b["points"])
    noisy = lidar_spec(noise_std=0.02)
    n1 = lidar_scan(V, F, noisy, T, seed=4)
    n2 = lidar_scan(V, F, noisy, T, seed=4)
    n3 = lidar_scan(V, F, noisy, T, seed=5)
    assert np.array_equal(n1["ranges"], n2["ranges"]) and np.array_equal(n1["points"], n2["points"])
    assert not np.array_equal(n1["ranges"], n3["ranges"])
    hit = a["ranges"] > 0
    assert np.array_equal(n1["ranges"] > 0, hit) and np.array_equal(n1["hit_face"], a["hit_face"])
    d = (n1["ranges"] - a["ranges"])[hit]
    assert abs(d.std() - 0.02) < 0.003 and abs(d.mean()) < 0.003
    # ノイズ込みの points も同じレイ上(方向は変わらず距離だけ変わる)
    ps = lidar_points_sensor_frame(n1, T)
    np.testing.assert_allclose(np.linalg.norm(ps, axis=1), n1["ranges"][hit], atol=1e-9)


def test_labels():
    rng = np.random.default_rng(2)
    Vg, Fg = tessellated_ground(nx=4, ny=4)
    Vb, Fb = random_boxes(6, rng)
    V, F = merge((Vg, Fg), (Vb, Fb))
    labels = np.concatenate([np.zeros(len(Fg), int), np.repeat(np.arange(6) + 2, 12)])
    spec = lidar_spec()
    T = np.eye(4)
    scan = lidar_scan(V, F, spec, T, labels=labels)
    hit = scan["ranges"] > 0
    assert np.array_equal(scan["labels"][hit], labels[scan["hit_face"][hit]])
    assert np.all(scan["labels"][~hit] == -1)
    assert (scan["labels"][hit] >= 2).any() and (scan["labels"][hit] == 0).any()
    no = lidar_scan(V, F, spec, T)
    assert np.all(no["labels"][hit] == 0) and np.all(no["labels"][~hit] == -1)
    with pytest.raises(ValueError):
        lidar_scan(V, F, spec, T, labels=labels[:-1])
    with pytest.raises(ValueError):
        lidar_scan(V, F, spec, T, labels=labels[None, :])


# ---- 悪い入力 ----------------------------------------------------------------------------------------
def test_bad_inputs():
    spec = lidar_spec()
    V, F = box_mesh((5.0, -1.0, -1.0, 7.0, 1.0, 1.0))
    T = np.eye(4)
    with pytest.raises(ValueError):
        lidar_scan(V, np.zeros((0, 3), int), spec, T)
    with pytest.raises(ValueError):
        lidar_scan(V[:, :2], F, spec, T)
    with pytest.raises(ValueError):
        lidar_scan(V.ravel(), F, spec, T)
    Vn = V.copy(); Vn[3, 1] = np.nan
    with pytest.raises(ValueError):
        lidar_scan(Vn, F, spec, T)
    Vi = V.copy(); Vi[0, 0] = np.inf
    with pytest.raises(ValueError):
        lidar_scan(Vi, F, spec, T)
    with pytest.raises(ValueError):
        lidar_scan(V, F[:, :2], spec, T)
    with pytest.raises(ValueError):
        lidar_scan(V, F + 5, spec, T)
    with pytest.raises(ValueError):
        lidar_scan(V, F, spec, np.eye(3))
    Tb = np.eye(4); Tb[0, 0] = 2.0
    with pytest.raises(ValueError):
        lidar_scan(V, F, spec, Tb)
    Tn = np.eye(4); Tn[0, 3] = np.nan
    with pytest.raises(ValueError):
        lidar_scan(V, F, spec, Tn)
    with pytest.raises(ValueError):
        lidar_scan(V, F, {"n_beams": 32}, T)
    with pytest.raises(ValueError):
        lidar_points_sensor_frame({"points": np.zeros((3, 3))}, np.eye(3))
    with pytest.raises(ValueError):
        ray_plane_range(np.zeros(3), np.eye(3), (0.0, 0.0, 0.0, 1.0))
    with pytest.raises(ValueError):
        ray_box_ranges(np.zeros(3), np.eye(3), (1.0, 0.0, 0.0, 0.0, 1.0, 1.0))
    with pytest.raises(ValueError):
        ray_box_ranges(np.zeros(3), np.array([np.nan, 0.0, 0.0]), (0.0, 0.0, 0.0, 1.0, 1.0, 1.0))


def test_closed_forms_basic():
    O = np.array([0.0, 0.0, 0.0])
    D = np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0]])
    r = ray_plane_range(O, D, (1.0, 0.0, 0.0, -5.0))      # x = 5
    np.testing.assert_allclose(r, [5.0, np.inf, np.inf, np.inf])
    r = ray_plane_range(O, 2.0 * D, (1.0, 0.0, 0.0, -5.0))  # 距離は ‖D‖ に比例しない(ユークリッド距離)
    np.testing.assert_allclose(r, [5.0, np.inf, np.inf, np.inf])
    b = ray_box_ranges(O, D, (2.0, -1.0, -1.0, 4.0, 1.0, 1.0))
    np.testing.assert_allclose(b, [2.0, np.inf, np.inf, np.inf])
    inside = ray_box_ranges(np.array([3.0, 0.0, 0.0]), D, (2.0, -1.0, -1.0, 4.0, 1.0, 1.0))
    np.testing.assert_allclose(inside, [1.0, 1.0, 1.0, 1.0])
    # 軸に平行なレイ(D_k = 0)が slab の外なら外れ
    b2 = ray_box_ranges(np.array([0.0, 5.0, 0.0]), D[:1], (2.0, -1.0, -1.0, 4.0, 1.0, 1.0))
    assert np.isinf(b2[0])
    assert ray_plane_range(O, D[:1], (1.0, 0.0, 0.0, -5.0)).shape == (1,)
    assert ray_plane_range(O, D.reshape(2, 2, 3), (1.0, 0.0, 0.0, -5.0)).shape == (2, 2)


def test_empty_scene_returns_no_hits():
    spec = lidar_spec()
    V, F = box_mesh((100.0, 100.0, 100.0, 101.0, 101.0, 101.0))   # range_max の外
    scan = lidar_scan(V, F, spec, np.eye(4))
    assert scan["n_hits"] == 0 and scan["points"].shape == (0, 3)
    assert np.all(scan["ranges"] == 0) and np.all(scan["hit_face"] == -1) and np.all(scan["labels"] == -1)
    assert lidar_points_sensor_frame(scan, np.eye(4)).shape == (0, 3)
    assert lidar_range_image_to_points(scan["ranges"], spec).shape == (0, 3)


# ---- 速度 --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("n_boxes,label", [(200, "2,400 box tris + 2,000 ground tris"),
                                           (1500, "18,000 box tris + 2,000 ground tris")])
def test_scan_speed(n_boxes, label):
    rng = np.random.default_rng(42)
    V, F = merge(tessellated_ground(), random_boxes(n_boxes, rng))
    assert F.shape[0] == 2000 + 12 * n_boxes
    spec = lidar_spec()
    assert spec["n_beams"] * spec["n_az"] == 57600
    T = pose(rot_z(0.1), (0.0, 0.0, 0.0))
    lidar_scan(V, F, spec, T)      # warm-up(import / cache)
    t0 = time.perf_counter()
    scan = lidar_scan(V, F, spec, T)
    dt = time.perf_counter() - t0
    print("\nlidar_scan %s (%d tris) x 57,600 rays: %.2f s, %d hits" % (label, F.shape[0], dt, scan["n_hits"]))
    assert scan["n_hits"] > 10000
    assert dt < 10.0, "scan took %.2f s (limit 10 s)" % dt
