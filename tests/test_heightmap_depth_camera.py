# -*- coding: utf-8 -*-
"""heightmap_depth_camera(terrain、2026-11-15)の真値の門。

1. 平面(傾いた面も)を撮った深度が、光線と平面の交点の閉形式に 1e-12 で一致する(刻みに依らない)。
2. 別の算法で撮った深度と一致する: 同じ高さ図を三角形に分けて world_camera(render3d のラスタ化、OpenGL の軸)で
   撮ると、平面では 1e-9、曲面でも画素の中央値で 1e-4 m。当たる画素の集合も同じ。
3. 往復: 深度 → camera.depth_to_points → 世界 → elevation_map が、見える範囲の元の高さに戻る
   (平面では誤差 ≤ (|a| + |b|)·cell/2 = セルの中の点の平均の位置のずれだけ)。
4. 交点の補間の誤差は刻みの 2 乗で縮む(曲面、刻みを半分にすると誤差の中央値が 3〜6 分の 1)。
5. 雑音: 平面を 40 回撮った深度の標準偏差が σ_z = z²·σ_d/(f·b)(acceptance_scan の triangulation と同じ則)に
   一致する(比の中央値 1 ± 0.05。40 回の標本の標準偏差の偏りは 1/(4·40) ≈ 0.6 %)。
6. 隠れ: 高い壁の向こうには当たらない。当たったセルは dem_viewshed(独立した op)が見えると言うセルに含まれる。
7. 細い突起: 1 セル幅の壁を水平に横切る光線は、既定の刻み(cell/2)なら位相に依らず当たる。刻みを cell に
   すると壁の上の方(弦が刻みより短い所)を飛び越す光線が出る(限界を数で示す)。cell より粗い刻みは断る。
8. 直す前で落ちる: 交点を一次で補間しない写し(刻みの点をそのまま使う)は平面の閉形式を cell/2 の桁で外す。
"""
from __future__ import annotations

import numpy as np
import pytest

import camera as CAM
import terrain as TR

K = np.array([[120.0, 0.0, 63.5], [0.0, 120.0, 47.5], [0.0, 0.0, 1.0]])
CELL = 0.05
NY, NX = 160, 200
XS = (np.arange(NX) + 0.5) * CELL
YS = (np.arange(NY) + 0.5) * CELL
X, Y = np.meshgrid(XS, YS)


def look(C, target, up=(0.0, 0.0, 1.0)):
    """world→camera の (R, t)(OpenCV の軸: z 前・y 下)。"""
    C = np.asarray(C, float)
    zc = np.asarray(target, float) - C
    zc /= np.linalg.norm(zc)
    xc = np.cross(zc, up)
    xc /= np.linalg.norm(xc)
    yc = np.cross(zc, xc)
    R = np.stack([xc, yc, zc])
    return R, -R @ C


def plane_depth(R, t, a, b, c0, shape=(96, 128)):
    """光線と平面 z = c0 + a·x + b·y の交点の閉形式の深度(光軸方向)。"""
    Cw = -R.T @ t
    v, u = np.mgrid[0:shape[0], 0:shape[1]].astype(float)
    dc = np.stack([(u - K[0, 2]) / K[0, 0], (v - K[1, 2]) / K[1, 1], np.ones_like(u)], -1)
    dw = dc @ R
    z = (c0 + a * Cw[0] + b * Cw[1] - Cw[2]) / (dw[..., 2] - a * dw[..., 0] - b * dw[..., 1])
    P = Cw + z[..., None] * dw
    inside = (P[..., 0] > XS[0]) & (P[..., 0] < XS[-1]) & (P[..., 1] > YS[0]) & (P[..., 1] < YS[-1]) & (z > 0)
    return z, inside


@pytest.mark.parametrize("a,b,c0", [(0.0, 0.0, 0.0), (0.08, -0.03, 0.2), (-0.15, 0.1, 0.9)])
def test_plane_matches_the_ray_plane_closed_form(a, b, c0):
    Hp = c0 + a * X + b * Y
    R, t = look([1.0, 4.0, 1.8], [5.0, 4.0, 0.0])
    d = TR.heightmap_depth_camera(Hp, (R, t), K, CELL)
    z, inside = plane_depth(R, t, a, b, c0)
    fin = np.isfinite(d)
    assert np.array_equal(fin, inside & (z <= 10.0) & (z >= 0.1))
    assert np.abs(d - z)[fin].max() < 1e-12
    d2 = TR.heightmap_depth_camera(Hp, (R, t), K, CELL, step=CELL / 7)
    assert np.abs(d2 - z)[fin].max() < 1e-12                          # 平面では刻みに依らない


def test_agrees_with_world_camera_on_the_triangulated_map():
    import driveworld as DW
    R, t = look([1.0, 4.0, 1.8], [5.0, 4.0, 0.0])
    S = np.diag([1.0, -1.0, -1.0])                                    # OpenCV → OpenGL の軸
    pose = np.eye(4)
    pose[:3, :3], pose[:3, 3] = S @ R, S @ t
    idx = np.arange(NY * NX).reshape(NY, NX)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel()
    F = np.r_[np.stack([a, b, d], 1), np.stack([a, d, c], 1)]
    for Hm, med_tol, max_tol in ((0.2 + 0.08 * X - 0.03 * Y, 1e-9, 1e-9),
                                 (0.6 * np.exp(-((X - 5) ** 2 + (Y - 4) ** 2) / (2 * 0.8 ** 2)) + 0.05 * X, 1e-4, 1e-2)):
        world = {"V": np.stack([X.ravel(), Y.ravel(), Hm.ravel()], 1), "F": F,
                 "face_color": np.full((len(F), 3), 0.5), "face_label": np.zeros(len(F), np.int64)}
        wc = DW.world_camera(world, pose, K, 128, 96)
        ours = TR.heightmap_depth_camera(Hm, (R, t), K, CELL)
        hit_wc = wc["face"] >= 0
        assert np.array_equal(np.isfinite(ours), hit_wc)
        diff = np.abs(ours - wc["depth"])[hit_wc]
        assert np.median(diff) < med_tol and diff.max() < max_tol


def test_round_trip_through_depth_to_points_and_elevation_map():
    a, b = 0.08, -0.03
    Hp = 0.2 + a * X + b * Y
    R, t = look([1.0, 4.0, 1.8], [5.0, 4.0, 0.0])
    d = TR.heightmap_depth_camera(Hp, (R, t), K, CELL)
    pts_w = (CAM.depth_to_points(d, K) - t) @ R                       # X_world = Rᵀ (X_cam − t)
    grid, _ext = TR.elevation_map(pts_w, cell=CELL, agg="mean", bounds=(0.0, NX * CELL, 0.0, NY * CELL))
    seen = np.isfinite(grid)
    assert seen.sum() > 3000
    assert np.abs(grid - Hp)[seen].max() <= (abs(a) + abs(b)) * CELL / 2 + 1e-12
    on_plane = pts_w[:, 2] - (0.2 + a * pts_w[:, 0] + b * pts_w[:, 1])
    assert np.abs(on_plane).max() < 1e-9                              # 戻した点は平面の上


def test_crossing_error_shrinks_with_the_square_of_the_step():
    Hh = 0.6 * np.exp(-((X - 5) ** 2 + (Y - 4) ** 2) / (2 * 0.8 ** 2)) + 0.05 * X
    R, t = look([1.0, 4.0, 1.8], [5.0, 4.0, 0.0])
    ref = TR.heightmap_depth_camera(Hh, (R, t), K, CELL, step=CELL / 64, max_range=6.0)
    med = []
    for st in (CELL, CELL / 2, CELL / 4, CELL / 8):
        d = TR.heightmap_depth_camera(Hh, (R, t), K, CELL, step=st, max_range=6.0)
        both = np.isfinite(d) & np.isfinite(ref)
        med.append(float(np.median(np.abs(d - ref)[both])))
    ratios = [med[i] / med[i + 1] for i in range(3)]
    assert all(3.0 < q < 6.5 for q in ratios), ratios


def test_noise_follows_the_stereo_law():
    Hp = 0.2 + 0.08 * X - 0.03 * Y
    R, t = look([1.0, 4.0, 1.8], [5.0, 4.0, 0.0])
    clean = TR.heightmap_depth_camera(Hp, (R, t), K, CELL, max_range=6.0)
    shots = np.array([TR.heightmap_depth_camera(Hp, (R, t), K, CELL, disparity_sigma=0.1, baseline=0.05, seed=k,
                                                max_range=6.0) for k in range(40)])
    fin = np.isfinite(clean)
    std = shots[:, fin].std(0)
    pred = clean[fin] ** 2 * 0.1 / (K[0, 0] * 0.05)
    q = std / pred
    assert abs(np.median(q) - 1.0) < 0.05
    again = TR.heightmap_depth_camera(Hp, (R, t), K, CELL, disparity_sigma=0.1, baseline=0.05, seed=3, max_range=6.0)
    assert np.array_equal(again, shots[3], equal_nan=True)            # seed で決定的
    assert np.abs(shots.mean(0)[fin] - clean[fin]).max() < 6 * pred.max() / np.sqrt(40)


def test_nothing_is_hit_behind_a_tall_wall_and_the_hits_are_visible_by_dem_viewshed():
    import demops
    Hw = np.zeros((NY, NX))
    Hw[:, 120] = 3.0
    R, t = look([1.0, 4.0, 1.8], [5.0, 4.0, 0.0])
    d = TR.heightmap_depth_camera(Hw, (R, t), K, CELL)
    pts = (CAM.depth_to_points(d, K) - t) @ R
    hit, _ = TR.elevation_map(pts, cell=CELL, agg="mean", bounds=(0.0, NX * CELL, 0.0, NY * CELL))
    hit = np.isfinite(hit)
    Cw = -R.T @ t
    vis = np.asarray(demops.dem_viewshed(Hw, CELL, (int(Cw[1] / CELL), int(Cw[0] / CELL)),
                                         observer_height_m=float(Cw[2]))) > 0.5
    assert hit.sum() > 2000
    assert not (hit & ~vis).any()                                     # 当たったセルは全部見える
    assert not hit[:, 121:].any() and not vis[:, 122:].any()          # 壁の向こうは両方とも見えない


def test_thin_wall_is_hit_at_the_default_step_and_the_limit_is_measured():
    """1 セル幅の壁(双一次で底辺 2 セルの山)を水平の光線で横切る。弦の長さは高さの割合 f で 2·cell·(1 − f)。"""
    Hw = np.zeros((40, 400))
    Hw[:, 200] = 1.0
    xs = (np.arange(400) + 0.5) * CELL
    R = np.array([[0.0, -1.0, 0.0], [0.0, 0.0, -1.0], [1.0, 0.0, 0.0]])   # +x を向く(y 下 = 世界の −z)
    Kh = np.array([[50.0, 0.0, 0.0], [0.0, 50.0, 0.0], [0.0, 0.0, 1.0]])
    miss = {}
    for f, st in ((0.5, None), (0.75, CELL)):
        n_miss = 0
        for k in range(40):                                           # 刻みの位相を 40 通りにずらす
            C = np.array([2.0 + k * CELL / 40, 1.0, f * 1.0])
            d = TR.heightmap_depth_camera(Hw, (R, -R @ C), Kh, CELL, width=1, height=1, step=st, max_range=20.0)
            if not np.isfinite(d[0, 0]):
                n_miss += 1
            else:                                                     # 山の斜面の上の交点(刻みが山の裾の
                assert abs(d[0, 0] - (xs[200] - CELL * (1 - f) - C[0])) < CELL / 2   # 折れ目をまたぐと一次の誤差)
        miss[f] = n_miss
    assert miss[0.5] == 0                                             # 弦 cell ≥ 刻み cell/2: 必ず当たる
    assert miss[0.75] > 0                                             # 弦 cell/2 < 刻み cell: 飛び越す光線がある
    with pytest.raises(ValueError, match="step"):
        TR.heightmap_depth_camera(Hw, (R, -R @ np.array([2.0, 1.0, 0.5])), Kh, CELL, width=1, height=1, step=2 * CELL)


def test_the_gate_fails_on_a_copy_without_the_crossing_interpolation(monkeypatch):
    """直す前で落ちる: 刻みの点をそのまま当たりにする写し(交点を一次で補間しない)は、平面の閉形式を外す。"""
    Hp = 0.2 + 0.08 * X - 0.03 * Y
    R, t = look([1.0, 4.0, 1.8], [5.0, 4.0, 0.0])
    z, _inside = plane_depth(R, t, 0.08, -0.03, 0.2)
    real = TR.heightmap_depth_camera(Hp, (R, t), K, CELL, step=CELL)
    fin = np.isfinite(real)
    assert np.abs(real - z)[fin].max() < 1e-12                        # 本物は刻み cell でも平面は厳密
    monkeypatch.setattr(TR, "_crossing_fraction", lambda a0, a1: np.ones_like(a0))
    broken = TR.heightmap_depth_camera(Hp, (R, t), K, CELL, step=CELL)
    both = fin & np.isfinite(broken)
    assert np.abs(broken - z)[both].max() > 1e-3                      # 刻みの桁で外れる


def test_refusals_and_conventions():
    R, t = look([1.0, 4.0, 1.8], [5.0, 4.0, 0.0])
    Hp = np.zeros((NY, NX))
    with pytest.raises(ValueError, match="empty"):
        TR.heightmap_depth_camera(np.zeros((0, 4)), (R, t), K)
    with pytest.raises(ValueError, match="rotation"):
        TR.heightmap_depth_camera(Hp, (2 * R, t), K)
    with pytest.raises(ValueError, match="near"):
        TR.heightmap_depth_camera(Hp, (R, t), K, near=5.0, max_range=1.0)
    with pytest.raises(ValueError, match="image size"):
        TR.heightmap_depth_camera(Hp, (R, t), np.array([[120.0, 0, 63.2], [0, 120.0, 47.5], [0, 0, 1]]))
    four = np.eye(4)
    four[:3, :3], four[:3, 3] = R, t
    assert np.array_equal(TR.heightmap_depth_camera(Hp, four, K, CELL),
                          TR.heightmap_depth_camera(Hp, (R, t), K, CELL), equal_nan=True)
    under = TR.heightmap_depth_camera(np.full((NY, NX), 5.0), (R, t), K, CELL)     # カメラが地面の中
    assert np.isnan(under).all()


def test_docstring_call_example_runs():
    import textwrap
    code = TR.heightmap_depth_camera.__doc__.split("呼び出し例::")[1]
    exec(compile(textwrap.dedent(code), "<heightmap_depth_camera example>", "exec"), {})
