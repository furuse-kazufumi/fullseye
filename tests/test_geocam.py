# -*- coding: utf-8 -*-
"""geocam 族の門(2026-09-21): 太陽位置の既知値・姿勢の往復・描いて→抜いて→当てる・台帳と公開経路。"""
from __future__ import annotations

import calendar
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import geocam as G  # noqa: E402

K = (280.0, 280.0, 160.0, 120.0)
SHAPE = (240, 320)


def _utc(*ymdhms):
    return float(calendar.timegm(ymdhms))


def _synthetic_dem(seed=0, n=300):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n]
    dem = np.zeros((n, n))
    for _ in range(25):
        cy, cx = rng.uniform(0, n), rng.uniform(0, n)
        a, sg = rng.uniform(150, 900), rng.uniform(12, 40)
        dem += a * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * sg ** 2))
    return dem


# --------------------------------------------------------------------------- #
# 1. 太陽位置(閉形式の既知値)                                                    #
# --------------------------------------------------------------------------- #
def test_sun_position_matches_the_almanac():
    s = G.sun_position(35.0, 0.0, [_utc(2024, 3, 20, 12, 7, 0)])            # 春分・均時差 −7 分 → 太陽正午
    assert abs(s["declination_deg"][0]) < 0.3
    assert abs(s["elevation_true_deg"][0] - 55.0) < 0.3                       # 90 − 緯度
    assert abs(s["azimuth_deg"][0] - 180.0) < 1.0
    s2 = G.sun_position(0.0, 0.0, [_utc(2024, 6, 20, 12, 0, 0)])             # 夏至・赤道
    assert abs(s2["declination_deg"][0] - 23.44) < 0.05
    assert abs(s2["elevation_true_deg"][0] - (90.0 - 23.44)) < 0.3
    assert s2["azimuth_deg"][0] < 5.0 or s2["azimuth_deg"][0] > 355.0        # 太陽は北側


def test_sun_azimuth_is_monotone_through_the_day_and_declination_is_bounded():
    ts = _utc(2024, 6, 21, 3, 0, 0) + np.arange(0, 16 * 3600, 1800.0)
    s = G.sun_position(60.17, 24.94, ts)                                       # ヘルシンキ
    assert np.all(np.diff(s["azimuth_deg"]) > 0)
    assert 52.0 < s["elevation_deg"].max() < 54.0                             # 90 − 60.17 + 23.44 = 53.27
    days = _utc(2024, 1, 1, 12, 0, 0) + np.arange(0, 366) * 86400.0
    d = G.sun_position(0.0, 0.0, days)["declination_deg"]
    assert d.max() < 23.5 and d.min() > -23.5 and d.max() > 23.3 and d.min() < -23.3
    assert s["n"] == len(ts)


def test_sun_position_rejects_bad_place_and_time():
    with pytest.raises(ValueError, match="latitude"):
        G.sun_position(95.0, 0.0, [0.0])
    with pytest.raises(ValueError, match="unix_times"):
        G.sun_position(0.0, 0.0, [np.nan])
    with pytest.raises(ValueError, match="unix_times"):
        G.sun_position(0.0, 0.0, [])


# --------------------------------------------------------------------------- #
# 2. 姿勢の規約                                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("pose", [(0, 0, 0), (137, -3, 2), (300, 10, -7), (90, 0, 0), (359.5, -14, 9)])
def test_pose_round_trip(pose):
    got = G._pose_from_rotation(G._rotation(*pose))
    assert abs((got[0] - pose[0] + 180.0) % 360.0 - 180.0) < 1e-9
    assert abs(got[1] - pose[1]) < 1e-9 and abs(got[2] - pose[2]) < 1e-9


def test_pixels_map_to_the_declared_directions():
    R = G._rotation(90.0, 0.0, 0.0)
    d = G._pixel_rays([[160, 120], [160, 20], [260, 120]], K) @ R.T
    az, el = G._az_el(d)
    assert abs(az[0] - 90.0) < 1e-9 and abs(el[0]) < 1e-9                    # 光軸は東・水平
    assert el[1] > 10.0 and abs(az[1] - 90.0) < 1e-9                          # 画面の上 = 高い仰角
    assert az[2] > 90.0 and abs(el[2]) < 1e-9                                 # 画面の右 = 時計回り


def test_pixel_rays_reject_bad_intrinsics():
    with pytest.raises(ValueError, match="fx, fy"):
        G._pixel_rays([[0, 0]], (0.0, 1.0, 0.0, 0.0))


# --------------------------------------------------------------------------- #
# 3. 描いて → 抜いて → 当てる                                                    #
# --------------------------------------------------------------------------- #
def test_skyline_round_trip_recovers_the_pose():
    dem = _synthetic_dem()
    sky = G.dem_skyline(dem, 30.0, (150, 150), eye_height=5.0, az_step_deg=0.5)
    assert sky["azimuth_deg"].shape == (720,) and np.all(np.diff(sky["azimuth_deg"]) > 0)
    assert sky["elevation_deg"].max() > 10.0                                  # 山がある
    true = (137.0, -3.0, 2.0)
    mask = G.render_skyline_view(sky, K, SHAPE, *true)
    assert set(np.unique(mask).tolist()) == {0.0, 1.0} and 0.2 < mask.mean() < 0.8
    rng = np.random.default_rng(1)
    img = mask * 0.85 + (1 - mask) * 0.25 + rng.normal(0, 0.03, SHAPE)
    rows = G.skyline_extract(img)
    truth_rows = np.array([np.argmax(mask[:, u] < 0.5) for u in range(SHAPE[1])])
    assert np.abs(rows - truth_rows).max() <= 1.5
    est = G.camera_orientation_from_skyline(rows, K, sky)
    assert abs(est["yaw_deg"] - true[0]) < 0.15 and abs(est["pitch_deg"] - true[1]) < 0.15 and abs(est["roll_deg"] - true[2]) < 0.15
    assert est["residual_deg"] < 0.3 and not est["ambiguous"] and est["margin_deg"] > 0.3
    assert est["yaw_profile_deg"].shape == est["yaw_profile_residual_deg"].shape


def test_flat_terrain_is_reported_as_ambiguous():
    flat = np.full((60, 60), 100.0)
    sky = G.dem_skyline(flat, 30.0, (30, 30))
    assert np.ptp(sky["elevation_deg"]) < 0.05                                # 全方位で同じ(丸みで僅かに負)
    mask = G.render_skyline_view(sky, K, SHAPE, 200.0, -2.0, 0.0)
    rows = G.skyline_extract(mask * 0.8 + 0.1)
    est = G.camera_orientation_from_skyline(rows, K, sky, yaw_step_deg=5.0)
    assert est["ambiguous"] and est["margin_deg"] < 0.1


def test_skyline_extract_rejects_images_without_a_boundary():
    with pytest.raises(ValueError, match="no vertical intensity change"):
        G.skyline_extract(np.full((20, 30), 0.5))
    with pytest.raises(ValueError, match="2-D"):
        G.skyline_extract(np.zeros((3, 3, 3)))
    with pytest.raises(ValueError, match="skyline table"):
        G.render_skyline_view({"azimuth_deg": [0.0], "elevation_deg": [0.0]}, K, SHAPE, 0, 0, 0)
    with pytest.raises(ValueError, match="outside"):
        G.dem_skyline(np.zeros((10, 10)), 1.0, (20, 0))


# --------------------------------------------------------------------------- #
# 4. 太陽から                                                                   #
# --------------------------------------------------------------------------- #
def test_sun_route_recovers_the_pose_and_refuses_collinear_observations():
    lat, lon = 60.17, 24.94
    ts = _utc(2024, 6, 21, 3, 0, 0) + np.arange(0, 16 * 3600, 1800.0)
    s = G.sun_position(lat, lon, ts)
    sel = s["elevation_deg"] > 5.0
    true = (137.0, -3.0, 2.0)
    Rt = G._rotation(*true)
    dc = G._dir_from_az_el(s["azimuth_deg"][sel], s["elevation_deg"][sel]) @ Rt   # 世界 → カメラ
    vis = dc[:, 2] > 0.2
    uv = np.column_stack([K[2] + K[0] * dc[vis, 0] / dc[vis, 2], K[3] + K[1] * dc[vis, 1] / dc[vis, 2]])
    uv += np.random.default_rng(2).normal(0, 0.5, uv.shape)
    est = G.camera_orientation_from_sun(uv, ts[sel][vis], lat, lon, K)
    assert abs(est["yaw_deg"] - true[0]) < 0.1 and abs(est["pitch_deg"] - true[1]) < 0.1 and abs(est["roll_deg"] - true[2]) < 0.1
    assert est["residual_deg"] < 0.3 and est["n"] == int(vis.sum())
    with pytest.raises(ValueError, match="at least 2"):
        G.camera_orientation_from_sun(uv[:1], ts[sel][vis][:1], lat, lon, K)
    with pytest.raises(ValueError, match="collinear"):
        G.camera_orientation_from_sun(np.vstack([uv[:1], uv[:1]]), [ts[sel][vis][0]] * 2, lat, lon, K)
    with pytest.raises(ValueError, match="below the horizon"):
        G.camera_orientation_from_sun(uv[:2], [_utc(2024, 6, 21, 0, 0, 0) - 3600.0 * 2] * 2, lat, lon, K)


def test_sun_pixel_position_finds_the_disc_and_refuses_no_sun():
    img = np.full((60, 80), 0.3)
    yy, xx = np.mgrid[0:60, 0:80]
    img[(yy - 20) ** 2 + (xx - 50) ** 2 <= 9] = 1.0
    uv = G.sun_pixel_position(img)
    assert uv.shape == (1, 2) and abs(uv[0, 0] - 50) < 0.2 and abs(uv[0, 1] - 20) < 0.2
    with pytest.raises(ValueError, match="constant"):
        G.sun_pixel_position(np.full((10, 10), 0.5))
    with pytest.raises(ValueError, match="min_area"):
        one = np.full((10, 10), 0.2)
        one[3, 3] = 1.0
        G.sun_pixel_position(one)


# --------------------------------------------------------------------------- #
# 4b. 実写が要求した 2 本(2026-09-21、Fintraffic 天候カメラ)                        #
# --------------------------------------------------------------------------- #
def test_sun_bloom_fit_recovers_the_centre_of_a_clipped_bloom():
    img = np.full((200, 300), 0.3)
    yy, xx = np.mgrid[0:200, 0:300]
    img[(yy - 30) ** 2 + (xx - 120) ** 2 <= 40 ** 2] = 1.0                    # 中心 (120, 30)、上 20 行は文字の帯で隠れる
    b = G.sun_bloom_fit(img, ignore_top_rows=20)
    assert abs(b["u"] - 120.0) < 0.5 and abs(b["v"] - 30.0) < 0.5 and abs(b["r"] - 40.0) < 1.0
    assert b["clipped"] == 1.0 and 0.6 < b["rim_fraction"] < 0.9
    assert b["centroid_v"] - 30.0 > 8.0                                        # 重心は切れた側の反対へ偏る
    full = np.full((200, 300), 0.3)
    full[(yy - 100) ** 2 + (xx - 150) ** 2 <= 30 ** 2] = 1.0
    b2 = G.sun_bloom_fit(full)
    assert b2["clipped"] == 0.0 and abs(b2["u"] - 150.0) < 0.5 and abs(b2["v"] - 100.0) < 0.5
    with pytest.raises(ValueError, match="no saturated"):
        G.sun_bloom_fit(np.full((20, 20), 0.5))
    with pytest.raises(ValueError, match="blown out"):
        G.sun_bloom_fit(np.ones((20, 20)))
    with pytest.raises(ValueError, match="rim"):
        cut = np.full((60, 300), 0.3)
        cut[:8, 100:200] = 1.0                                                # 上端に張り付いた帯
        G.sun_bloom_fit(cut)


def _sun_track_with_decoys(true, f_true, seed=3, n_static=2, n_random=3):
    lat, lon, W, H = 60.2, 24.9, 1280, 720
    K = (f_true, f_true, W / 2, H / 2)
    ts = _utc(2026, 9, 20, 12, 0, 0) + np.arange(0, 5 * 3600, 600.0)
    s = G.sun_position(lat, lon, ts)
    c = G._dir_from_az_el(s["azimuth_deg"], s["elevation_deg"]) @ G._rotation(*true)
    rng = np.random.default_rng(seed)
    C, FI, n_true = [], [], 0
    for k in range(len(ts)):
        for p in [[300.0, 60.0], [900.0, 40.0]][:n_static] + [[rng.uniform(0, W), rng.uniform(0, H * 0.7)] for _ in range(n_random)]:
            C.append(p)
            FI.append(k)
        if c[k, 2] > 0.05 and s["elevation_true_deg"][k] > 0:
            u, v = K[2] + K[0] * c[k, 0] / c[k, 2], K[3] + K[1] * c[k, 1] / c[k, 2]
            if 0 <= u < W and 0 <= v < H and rng.uniform() < 0.8:
                C.append([u + rng.normal(0, 1.5), v + rng.normal(0, 1.5)])
                FI.append(k)
                n_true += 1
    return np.array(C), np.array(FI, float), ts, lat, lon, (H, W), K, n_true


def test_sun_candidates_pick_the_moving_track_among_decoys_and_find_the_focal_length():
    true, f_true = (255.0, -8.0, 1.5), 950.0
    C, FI, ts, lat, lon, shape, K, n_true = _sun_track_with_decoys(true, f_true)
    r = G.camera_orientation_from_sun_candidates(C, FI, ts, lat, lon, shape)
    assert abs(r["yaw_deg"] - true[0]) < 0.3 and abs(r["pitch_deg"] - true[1]) < 0.3 and abs(r["roll_deg"] - true[2]) < 1.0   # roll は短い弧の弱い自由度
    assert abs(r["f_px"] - f_true) / f_true < 0.03 and r["n_inliers"] >= n_true - 1 and r["residual_deg"] < 0.3
    assert r["inlier"].shape == (len(C),) and r["inlier"].sum() == r["n_inliers"] and r["loo_px"] < 5.0 and r["at_prior_bound"] == 0.0
    r2 = G.camera_orientation_from_sun_candidates(C, FI, ts, lat, lon, shape, K=K)
    assert abs(r2["yaw_deg"] - true[0]) < 0.3 and abs(r2["pitch_deg"] - true[1]) < 0.3 and r2["f_px"] == f_true   # 1.5 px の雑音 ≈ 0.1°


def test_sun_candidates_refuse_static_blobs_and_too_few_frames():
    C, FI, ts, lat, lon, shape, K, _ = _sun_track_with_decoys((255.0, -8.0, 1.5), 950.0)
    with pytest.raises(ValueError, match="only 1 frame"):
        G.camera_orientation_from_sun_candidates(C[:5], np.zeros(5), ts, lat, lon, shape)
    static = np.array([[300.0, 60.0]] * len(ts))
    with pytest.raises(ValueError):
        G.camera_orientation_from_sun_candidates(static, np.arange(len(ts), dtype=float), ts, lat, lon, shape)
    with pytest.raises(ValueError, match="frame_index"):
        G.camera_orientation_from_sun_candidates(C, FI + 0.5, ts, lat, lon, shape)
    with pytest.raises(ValueError, match="shape"):
        G.camera_orientation_from_sun_candidates(C, FI, ts, lat, lon, (1,))


def test_sun_candidates_do_not_let_night_frames_vote():
    """地平線下の時刻に候補があっても投票しない(投票させると最終の再当てはめが「太陽が地平線下」で落ちる)。"""
    true, f_true = (255.0, -8.0, 1.5), 950.0
    C, FI, ts, lat, lon, shape, K, _ = _sun_track_with_decoys(true, f_true)
    night = ts[-1] + 6 * 3600.0                                                # 夜
    ts2 = np.append(ts, night)
    C2 = np.vstack([C, [[640.0, 300.0], [700.0, 310.0]]])
    FI2 = np.append(FI, [len(ts), len(ts)])
    r = G.camera_orientation_from_sun_candidates(C2, FI2, ts2, lat, lon, shape)
    assert abs(r["yaw_deg"] - true[0]) < 0.3 and r["inlier"][-2:].sum() == 0


# --------------------------------------------------------------------------- #
# 5. 台帳と公開経路                                                              #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    import opsgeocam

    assert opsgeocam.missing() == []
    assert set(opsgeocam.OPSGEOCAM) == set(G.__all__)


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs
    import opsgeocam

    for name in opsgeocam.OPSGEOCAM:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = [r for r in tc.catalog() if r[1] == "geocam"]
    assert len(rows) == 9
    assert {r[3] for r in rows} == {"table", "keypoints", "signal", "image2d"}


def test_the_fuzzer_knows_every_input_type_of_the_family():
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    import opsgeocam

    for m in opsgeocam.OPSGEOCAM.values():
        for t in m["in"]:
            assert t in cf.TYPE_CHECKS, t
