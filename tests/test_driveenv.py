# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""driveenv(太陽・霧・まぶしさ・見えてから止まれる速さ・描画)の門。

真値: 国立天文台 暦計算室の公表値(東京 2026 年)、天体暦の簡略式(第 2 実装)、Koschmieder の閉形式、変曲点の閉形式、
drivelong の停止距離、色度の距離の定義。"""
import math
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

import driveenv as EV
import drivelong as DL

JST = timezone(timedelta(hours=9))
TOKYO = (35.6581, 139.7414)


def _almanac_sun(jd, lat, lon):
    """第 2 実装: 天体暦(The Astronomical Almanac)の太陽の簡略式(1950〜2050 年で 0.01°)→ (幾何の高度, 方位)。"""
    n = jd - 2451545.0
    L = (280.460 + 0.9856474 * n) % 360.0
    g = math.radians((357.528 + 0.9856003 * n) % 360.0)
    lam = math.radians(L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    eps = math.radians(23.439 - 0.0000004 * n)
    ra = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))
    dec = math.asin(math.sin(eps) * math.sin(lam))
    gmst = (18.697374558 + 24.06570982441908 * n) % 24.0
    ha = math.radians(gmst * 15.0 + lon) - ra
    phi = math.radians(lat)
    el = math.asin(math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(ha))
    az = math.atan2(-math.sin(ha), math.tan(dec) * math.cos(phi) - math.sin(phi) * math.cos(ha))
    return math.degrees(el), math.degrees(az) % 360.0


def test_sun_at_matches_almanac_second_implementation():
    rng = np.random.default_rng(3)
    worst_el = worst_az = 0.0
    for _ in range(300):
        jd = 2451545.0 + rng.uniform(-9000, 9000)
        lat, lon = rng.uniform(-60, 60), rng.uniform(-180, 180)
        sp = EV.sun_at(jd, lat, lon, refraction=False)
        el, az = _almanac_sun(jd, lat, lon)
        worst_el = max(worst_el, abs(sp["elevation_geometric"] - el))
        if abs(el) < 85:
            d = abs((sp["azimuth"] - az + 180) % 360 - 180)
            worst_az = max(worst_az, d * math.cos(math.radians(el)))
    assert worst_el < 0.02 and worst_az < 0.02, (worst_el, worst_az)


@pytest.mark.parametrize("m,d,rise,tr,sett,az_r,alt,az_s", [
    (3, 20, "5:45", "11:49", "17:52", 89.8, 54.2, 270.5),
    (6, 21, "4:25", "11:43", "19:00", 60.0, 77.8, 300.0),
    (9, 23, "5:29", "11:34", "17:37", 89.3, 54.3, 270.4),
    (12, 22, "6:47", "11:39", "16:32", 118.6, 30.9, 241.4),
])
def test_sun_events_match_naoj_tokyo_2026(m, d, rise, tr, sett, az_r, alt, az_s):
    ev = EV.sun_events(2026, m, d, *TOKYO, 9.0, h0="naoj")
    for ours, ref in ((ev["sunrise"], rise), (ev["transit"], tr), (ev["sunset"], sett)):
        hh, mm = (int(x) for x in ref.split(":"))
        o = ours.hour * 60 + ours.minute + ours.second / 60.0
        assert math.floor(o + 0.5) == hh * 60 + mm
    for ours, ref in ((ev["sunrise_azimuth"], az_r), (ev["transit_altitude_apparent"], alt), (ev["sunset_azimuth"], az_s)):
        assert abs(ours - ref) <= 0.1


def test_sun_events_polar_night_has_no_sunrise():
    ev = EV.sun_events(2026, 12, 22, 80.0, 0.0, 0.0)
    assert ev["sunrise"] is None and ev["sunset"] is None


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError, match="naive"):
        EV.sun_at(datetime(2026, 3, 20, 12, 0), *TOKYO)


def test_julian_day_epoch_and_timezone():
    assert EV.julian_day(datetime(2000, 1, 1, 12, tzinfo=timezone.utc)) == 2451545.0
    assert EV.julian_day(datetime(2000, 1, 1, 21, tzinfo=JST)) == 2451545.0


def test_sun_vector_convention():
    np.testing.assert_allclose(EV.sun_vector(0.0, 90.0), [1, 0, 0], atol=1e-12)      # 東 = +x
    np.testing.assert_allclose(EV.sun_vector(0.0, 0.0), [0, 1, 0], atol=1e-12)       # 北 = +y
    np.testing.assert_allclose(EV.sun_vector(90.0, 123.0), [0, 0, 1], atol=1e-12)


def test_sun_illuminance_monotone_and_night():
    vals = [EV.sun_illuminance(h)["direct_normal"] for h in (1, 5, 15, 40, 80)]
    assert all(a < b for a, b in zip(vals, vals[1:]))
    diffs = [EV.sun_illuminance(h)["diffuse"] for h in (-18, -12, -6, 0, 10)]
    assert all(a < b for a, b in zip(diffs, diffs[1:]))
    assert EV.sun_illuminance(-5)["direct_normal"] == 0.0
    with pytest.raises(ValueError):
        EV.sun_illuminance(10, cloud=1.5)


def test_koschmieder_and_visibility():
    b = EV.beta_from_mor(100.0)
    assert abs(EV.mor_from_beta(b) - 100.0) < 1e-12
    assert abs(EV.mor_from_beta(b, 0.02) - 100.0 * math.log(50) / math.log(20)) < 1e-9
    # 視程の距離で黒い物(L0 = 0)の見かけのコントラストは 5 %
    L = EV.koschmieder(0.0, 1.0, b, 100.0)
    assert abs((1.0 - L) - 0.05) < 1e-12
    np.testing.assert_allclose(EV.koschmieder(3.0, 1.0, 0.0, [0, 50]), [3.0, 3.0])
    with pytest.raises(ValueError):
        EV.koschmieder(1, 1, 0.01, -1.0)


def test_road_row_distance_is_exact_for_pitched_camera():
    f, Hc, a = 554.0, 1.35, math.radians(1.5)
    cy = 200.0
    d = np.array([3.0, 10.0, 40.0, 150.0])
    rows = cy + f * np.tan(np.arctan(Hc / d) - a)
    vh = cy - f * math.tan(a)
    np.testing.assert_allclose(EV.road_row_distance(rows, vh, f, Hc, a), d, rtol=1e-12)
    assert np.isinf(EV.road_row_distance([vh - 1.0], vh, f, Hc, a)[0])


@pytest.mark.parametrize("mor", [30.0, 80.0, 250.0])
def test_fog_beta_from_profile_recovers_beta(mor):
    f, Hc, a, cy = 554.0, 1.35, math.radians(1.3), 200.0
    vh = cy - f * math.tan(a)
    rows = np.arange(int(vh) + 3, 400)
    d = EV.road_row_distance(rows, vh, f, Hc, a)
    r = np.sqrt(d * d + Hc * Hc)
    b = EV.beta_from_mor(mor)
    L = EV.koschmieder(1200.0, 5000.0, b, r)
    fit = EV.fog_beta_from_profile(rows, L, vh, f, Hc, a)
    assert abs(fit["beta_fit"] - b) / b < 1e-6
    assert abs(fit["L_h"] - 5000.0) < 1e-3 and abs(fit["L0"] - 1200.0) < 1e-3


def test_fog_inflection_closed_form():
    # 距離を λ/u とした模型(Hautière の形)では変曲点の β = 2 u_i / λ が厳密
    f, Hc = 554.0, 1.35
    lam = f * Hc
    vh = 150.0
    rows = np.linspace(vh + 1, vh + 300, 3000)
    b = 0.05
    L = 5000.0 + (1000.0 - 5000.0) * np.exp(-b * lam / (rows - vh))
    fit = EV.fog_beta_from_profile(rows, L, vh, f, Hc, 0.0, method="inflection", slant=False)
    assert abs(fit["beta"] - b) / b < 2e-3


def test_fog_profile_rejects_bad_input():
    with pytest.raises(ValueError):
        EV.fog_beta_from_profile([1, 2, 3], [1, 2], 0.0, 500.0, 1.3)
    with pytest.raises(ValueError):
        EV.fog_beta_from_profile(np.arange(10), np.ones(10), 100.0, 500.0, 1.3)       # 地平線の上だけ


def test_veiling_luminance_models():
    assert EV.veiling_luminance(1000.0, 10.0) == pytest.approx(100.0)
    # CIE の一般式は小角度で Stiles–Holladay より大きい(10/θ³ の項)、30° 付近で同じ桁
    assert EV.veiling_luminance(1.0, 1.0, model="cie") > EV.veiling_luminance(1.0, 1.0)
    r = EV.veiling_luminance(1.0, 30.0, model="cie", age=25) / EV.veiling_luminance(1.0, 30.0)
    assert 0.3 < r < 3.0
    with pytest.raises(ValueError):
        EV.veiling_luminance(1.0, 0.0)


def test_veil_chroma_limit_hits_tolerance():
    c = np.array([1.0, 0.12, 0.08])
    W = EV.veil_chroma_limit(c, 10000.0, 0.15)
    v = c * 10000.0 + W
    d = np.linalg.norm(v / np.linalg.norm(v) - c / np.linalg.norm(c))
    assert abs(d - 0.15) < 1e-9
    # 灰色に近い色は、どれだけ白を足しても許容を割らない
    assert math.isinf(EV.veil_chroma_limit([1.0, 0.98, 0.97], 100.0, 0.15))
    # 輝度に比例(色度の距離は c L + W の比だけで決まる)
    assert abs(EV.veil_chroma_limit(c, 20000.0) / W - 2.0) < 1e-9


@pytest.mark.parametrize("theta", [0.0, 0.08, -0.05])
@pytest.mark.parametrize("k", [0.0, 3e-4])
def test_sight_stop_speed_inverts_stopping_distance(theta, k):
    for D in (5.0, 25.0, 80.0):
        v = EV.sight_stop_speed(D, 0.75, 5.0, theta, 0.012, k)
        assert abs(DL.stopping_distance_grade(v, 0.75, 5.0, theta, 0.012, k) - D) < 1e-7


def test_sight_stop_speed_edge_cases():
    assert EV.sight_stop_speed(0.0, 0.75, 5.0) == 0.0
    assert EV.sight_stop_speed(30.0, 0.0, 5.0) == pytest.approx(math.sqrt(2 * 5.0 * 30.0))
    assert EV.sight_stop_speed(30.0, 0.75, 0.1, theta=-0.2) == 0.0                     # 下りで制動が負ける


def test_tone_map_preserves_chromaticity_and_bounds():
    rng = np.random.default_rng(0)
    r = rng.uniform(0, 1e5, (50, 3))
    out = EV.tone_map(r, 1e-3)
    assert out.max() <= 1.0 + 1e-12 and out.min() >= 0.0
    n0 = r / np.linalg.norm(r, axis=1, keepdims=True)
    n1 = out / np.linalg.norm(out, axis=1, keepdims=True)
    np.testing.assert_allclose(n0, n1, atol=1e-12)
    # 暗い所は線形
    np.testing.assert_allclose(EV.tone_map(np.array([1e-3, 2e-3, 3e-3]), 1.0), [1e-3, 2e-3, 3e-3], rtol=3e-3)


def _tiny_world():
    import driveworld as DW
    W = DW._empty_world()
    Vg, Fg = DW._grid_plane(-30, 30, -30, 30, step=4.0)
    DW.world_add(W, Vg, Fg, 0, DW._ROAD_COLOR, name="ground")
    bx = np.array([[x, y, z] for z in (0.0, 3.0) for y in (-0.2, 0.2) for x in (-0.2, 0.2)]) + np.array([5.0, 0.0, 0.0])
    bf = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4],
                   [1, 5, 7], [1, 7, 3]])
    DW.world_add(W, bx, bf, 6, (0.8, 0.8, 0.8), name="pole")
    return W


def test_env_render_fog_follows_koschmieder_and_night_is_dark():
    import driveworld as DW
    W = _tiny_world()
    K = DW.camera_intrinsics(60.0, 160, 100)
    P = DW.camera_pose((-5.0, 0.0, 1.35), (10.0, 0.0, 0.9))
    env = EV.env_params(sun=(30.0, 180.0), cloud=1.0, fog_mor=40.0)
    clear = EV.env_render(W, P, K, 160, 100, dict(env, beta=0.0), shadows=False)
    fog = EV.env_render(W, P, K, 160, 100, env, shadows=False)
    hit = clear["label"] >= 0
    t = np.exp(-env["beta"] * clear["range"][hit])
    L_h = 2.0 * env["diffuse"] / math.pi
    np.testing.assert_allclose(fog["radiance"][hit], clear["radiance"][hit] * t[:, None] + L_h * (1 - t)[:, None], rtol=1e-9)
    night = EV.env_render(W, P, K, 160, 100, EV.env_params(sun=(-30.0, 0.0)), shadows=False)
    assert night["radiance"].max() < 0.01


def test_env_render_ground_fill_below_camera():
    import driveworld as DW
    W = _tiny_world()
    K = DW.camera_intrinsics(60.0, 160, 100)
    P = DW.camera_pose((-5.0, 0.0, 1.35), (10.0, 0.0, 0.9))
    out = EV.env_render(W, P, K, 160, 100, EV.env_params(sun=(40.0, 180.0)), shadows=False)
    assert (out["label"][60:] >= 0).all()                                               # 足元の地面が空にならない


def test_env_render_shadow_points_away_from_sun():
    import driveworld as DW
    W = _tiny_world()
    K = DW.camera_intrinsics(50.0, 200, 200)
    P = DW.camera_pose((5.0, 0.0, 40.0), (5.0, 0.0, 0.0), up=(0.0, 1.0, 0.0))
    out = EV.env_render(W, P, K, 200, 200, EV.env_params(sun=(30.0, 90.0)), shadow_res=1024)       # 太陽は東 → 影は西(−x)
    rr, cc = np.nonzero(out["shadow"])
    assert len(rr) > 20
    assert cc.mean() < 100                                                                # 画像の左 = −x
    tip = (100 - cc.min()) / K[0, 0] * 40.0
    assert abs(tip - (3.0 / math.tan(math.radians(30.0)) + 0.2)) < 0.4


def test_env_params_rejects_bad_input():
    with pytest.raises(ValueError):
        EV.env_params()
    with pytest.raises(ValueError):
        EV.env_params(sun=(10, 90), headlamps="fog")
    with pytest.raises(ValueError):
        EV.env_params(sun=(10, 90), rain=2.0)
    with pytest.raises(ValueError):
        EV.env_render({}, np.eye(4), np.eye(3), 10, 10, None)
