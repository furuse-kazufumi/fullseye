# -*- coding: utf-8 -*-
"""DEM 解析の検査 —— **解析解と突き合わせる**。

地形解析はそれらしい絵が出てしまうので、目視では検証になりません。閉形式の
答えを持つ曲面(平面・円錐・ガウス丘・平坦面)を基準にします。

★2026-09-06 の実話: 最初に書いた検算スクリプトのほうが間違っていて、平面を作る
式で北成分の符号を落としていました。方位が 5 通りすべて **きれいに 180-A** に
なったので気づけた(でたらめなら気づけない)。**規約を持つ量は、規約を含めて
テストに書く**のが要点です。
"""
from __future__ import annotations

import math
import os

import numpy as np
import pytest

import demops as D


def plane(h, w, c, slope_deg, aspect_deg):
    """既知の傾斜・方位を持つ平面。行 0 が北、方位は北 0 度・東回り。

    下り方向の単位ベクトルは (東, 北) = (sin A, cos A)。東 = +col、北 = -row。
    """
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    g = math.tan(math.radians(slope_deg))
    ar = math.radians(aspect_deg)
    return -g * ((xx * c) * math.sin(ar) + (-yy * c) * math.cos(ar))


def cone(n, c, slope_deg, top=100.0):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    r = np.hypot(yy - n // 2, xx - n // 2) * c
    return top - math.tan(math.radians(slope_deg)) * r


# =========================================================================
# 1. 傾斜・方位 —— 平面と円錐
# =========================================================================

@pytest.mark.parametrize("slope_deg", [1.0, 5.0, 12.0, 30.0, 45.0, 60.0])
@pytest.mark.parametrize("method", D.SLOPE_METHODS)
def test_slope_on_a_plane_matches_the_closed_form(slope_deg, method):
    c = 5.0
    z = plane(31, 31, c, slope_deg, 37.0)
    s = D.dem_slope(z, c, method=method)[2:-2, 2:-2]
    assert np.max(np.abs(s - slope_deg)) < 1e-10


@pytest.mark.parametrize("aspect_deg", [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 310.0])
def test_aspect_on_a_plane_matches_the_closed_form(aspect_deg):
    """方位の規約(北 0 度・東回り、行 0 が北)を丸ごと固定する。"""
    c = 5.0
    z = plane(31, 31, c, 15.0, aspect_deg)
    a = D.dem_aspect(z, c)[2:-2, 2:-2]
    err = np.abs((a - aspect_deg + 180.0) % 360.0 - 180.0)
    assert np.max(err) < 1e-9, f"方位が {np.mean(a):.2f} 度(期待 {aspect_deg})"


def test_aspect_is_not_mirrored_north_south():
    """南北反転は**例外を出さない**種類の誤り。北向き斜面で名指しで固定する。"""
    c = 2.0
    yy = np.mgrid[0:21, 0:21][0].astype(np.float64)
    north_facing = yy * c * 0.3          # 行が増える(南へ行く)ほど高い = 北向き斜面
    a = D.dem_aspect(north_facing, c)[2:-2, 2:-2]
    assert np.allclose(a, 0.0, atol=1e-9), f"北向き斜面の方位が {np.mean(a):.1f} 度"


def test_slope_is_constant_on_a_cone_and_aspect_is_radial():
    n, c = 61, 2.0
    z = cone(n, c, 20.0)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    r = np.hypot(yy - n // 2, xx - n // 2) * c
    m = (r > 8 * c) & (r < 25 * c)
    assert abs(np.mean(D.dem_slope(z, c)[m]) - 20.0) < 0.05
    want = np.degrees(np.arctan2(xx - n // 2, -(yy - n // 2))) % 360.0
    err = np.abs((D.dem_aspect(z, c) - want + 180) % 360 - 180)[m]
    assert np.max(err) < 0.2


def test_flat_ground_reports_no_aspect_rather_than_north():
    """平坦を 0 度(= 北)で返すと、北向き斜面と区別できない。"""
    a = D.dem_aspect(np.zeros((9, 9)), 1.0)
    assert np.all(a == D.ASPECT_FLAT)


@pytest.mark.parametrize("units,expect", [
    ("degrees", 45.0), ("radians", math.pi / 4), ("percent", 100.0)])
def test_slope_units(units, expect):
    z = plane(21, 21, 1.0, 45.0, 90.0)
    got = D.dem_slope(z, 1.0, units=units)[2:-2, 2:-2]
    assert np.max(np.abs(got - expect)) < 1e-9


# =========================================================================
# 2. 曲率 —— ガウス丘、離散化は 2 次で縮む
# =========================================================================

def _gauss_hill(cell, half_extent=120.0, amp=50.0, sigma=40.0):
    n = int(2 * half_extent / cell) | 1
    yy, xx = (np.mgrid[0:n, 0:n] - n // 2) * cell
    return amp * np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma ** 2)), n


def test_curvature_at_the_summit_matches_the_closed_form():
    amp, sigma = 50.0, 40.0
    z, n = _gauss_hill(1.0, amp=amp, sigma=sigma)
    k = D.dem_curvature(z, 1.0, kind="total")[n // 2, n // 2]
    truth = 2.0 * amp / sigma ** 2
    assert abs(k - truth) / truth < 1e-3


def test_the_curvature_error_is_discretisation_not_a_wrong_formula():
    """格子を半分にすると誤差が 4 分の 1 になる(2 次収束)。

    手法の誤りなら細かくしても縮まない。**両者を区別する**ための検査。
    """
    amp, sigma = 50.0, 40.0
    truth = 2.0 * amp / sigma ** 2
    errs = []
    for cell in (4.0, 2.0, 1.0):
        z, n = _gauss_hill(cell, amp=amp, sigma=sigma)
        errs.append(abs(D.dem_curvature(z, cell, kind="total")[n // 2, n // 2] - truth))
    for a, b in zip(errs, errs[1:]):
        assert 3.0 < a / b < 5.0, f"収束次数がおかしい: {errs}"


def test_a_plane_has_no_curvature():
    z = plane(31, 31, 2.0, 20.0, 70.0)
    for kind in ("profile", "planform", "total"):
        assert np.max(np.abs(D.dem_curvature(z, 2.0, kind=kind)[3:-3, 3:-3])) < 1e-10


# =========================================================================
# 3. 陰影・天空率
# =========================================================================

@pytest.mark.parametrize("alt", [15.0, 30.0, 45.0, 75.0, 90.0])
def test_hillshade_on_flat_ground_is_the_sine_of_the_solar_altitude(alt):
    hs = D.dem_hillshade(np.zeros((17, 17)), 5.0, altitude_deg=alt)
    assert np.max(np.abs(hs - math.sin(math.radians(alt)))) < 1e-12


def test_hillshade_is_brighter_on_the_slope_facing_the_sun():
    c = 5.0
    east = plane(21, 21, c, 25.0, 90.0)          # 東向き斜面
    lit = D.dem_hillshade(east, c, azimuth_deg=90.0, altitude_deg=30.0)[5:-5, 5:-5]
    dark = D.dem_hillshade(east, c, azimuth_deg=270.0, altitude_deg=30.0)[5:-5, 5:-5]
    assert np.mean(lit) > np.mean(dark) + 0.2


def test_sky_view_factor_on_flat_ground_is_exactly_one():
    svf = D.dem_sky_view_factor(np.zeros((21, 21)), 5.0, n_azimuth=8)
    assert np.max(np.abs(svf - 1.0)) < 1e-12


def test_a_valley_sees_less_sky_than_a_ridge():
    n = 41
    xx = np.mgrid[0:n, 0:n][1].astype(np.float64)
    valley = np.abs(xx - n // 2) * 4.0            # V 字谷
    svf = D.dem_sky_view_factor(valley, 5.0, n_azimuth=8)
    assert svf[n // 2, n // 2] < svf[n // 2, 2] - 0.05


# =========================================================================
# 4. 水の流れ
# =========================================================================

def test_filled_is_never_below_the_input():
    rng = np.random.default_rng(0)
    z = rng.random((30, 30)) * 5 + np.linspace(20, 0, 30)[:, None]
    assert np.min(D.dem_fill_sinks(z, 1e-6) - z) >= 0.0


def test_a_pit_gets_filled_to_its_rim():
    z = np.full((15, 15), 10.0)
    z[7, 7] = 2.0
    filled = D.dem_fill_sinks(z)
    assert filled[7, 7] == pytest.approx(10.0)


def test_accumulation_grows_downstream_on_a_ramp():
    ramp = np.tile(np.linspace(50.0, 0.0, 20)[:, None], (1, 12))
    col = D.dem_flow_accumulation(ramp, 10.0)[:, 6]
    assert np.all(np.diff(col) >= 0) and col[0] == 1.0


def test_total_accumulation_cannot_exceed_the_cell_count():
    rng = np.random.default_rng(1)
    z = rng.random((25, 25)) * 3 + np.linspace(15, 0, 25)[:, None]
    acc = D.dem_flow_accumulation(z, 5.0)
    assert np.nanmax(acc) <= z.size


# =========================================================================
# 5. 欠測(水域)—— 黙って埋めない
# =========================================================================

def _with_water(n=24):
    z = np.tile(np.linspace(30.0, 0.0, n)[:, None], (1, n))
    z[-4:, :] = np.nan                    # 下端が水域
    return z


def test_missing_cells_are_refused_by_default():
    """既定で拒否する。何が正しいかは対象次第なので、黙って決めない。"""
    with pytest.raises(ValueError, match="nodata='error'"):
        D.dem_flow_accumulation(_with_water(), 5.0)
    with pytest.raises(ValueError, match="nodata='error'"):
        D.dem_fill_sinks(_with_water())


@pytest.mark.parametrize("policy", ["outlet", "barrier"])
def test_a_policy_lets_it_through_and_keeps_missing_cells_missing(policy):
    z = _with_water()
    acc = D.dem_flow_accumulation(z, 5.0, nodata=policy)
    assert np.all(np.isnan(acc[np.isnan(z)])), "欠測セルに値をでっち上げている"
    assert np.all(np.isfinite(acc[~np.isnan(z)]))


def test_an_unknown_policy_fails_closed():
    with pytest.raises(ValueError, match="nodata must be one of"):
        D.dem_flow_accumulation(_with_water(), 5.0, nodata="fill")


def test_a_sentinel_value_is_refused_rather_than_treated_as_an_elevation():
    """-9999 を標高として扱うと、傾斜が巨大な嘘になって例外も出ない。"""
    z = np.zeros((10, 10))
    z[5, 5] = -9999.0
    with pytest.raises(ValueError, match="Sentinel"):
        D.dem_slope(z, 5.0)


# =========================================================================
# 6. 可視領域
# =========================================================================

def test_everything_is_visible_on_flat_ground():
    assert np.all(D.dem_viewshed(np.zeros((21, 21)), 5.0, (10, 10)) == 1.0)


def test_a_wall_hides_what_is_behind_it():
    wall = np.zeros((21, 21))
    wall[:, 14] = 40.0
    v = D.dem_viewshed(wall, 5.0, (10, 3))
    assert np.all(v[:, 18] == 0.0), "壁の向こうが見えている"
    assert v[10, 3] == 1.0


def test_the_observer_cell_is_always_visible():
    rng = np.random.default_rng(2)
    z = rng.random((17, 17)) * 20
    assert D.dem_viewshed(z, 5.0, (8, 8))[8, 8] == 1.0


# =========================================================================
# 7. 入力の検証(fail-closed)
# =========================================================================

@pytest.mark.parametrize("bad,match", [
    (np.zeros((2, 5)), "at least 3x3"),
    (np.zeros(9), "2-D"),
    (np.full((5, 5), np.inf), "inf"),
])
def test_bad_grids_are_refused(bad, match):
    with pytest.raises(ValueError, match=match):
        D.dem_slope(bad, 1.0)


@pytest.mark.parametrize("bad", ["5", True, 0.0, -1.0, float("nan")])
def test_a_bad_cell_size_is_refused(bad):
    """文字列の '5' は float() が通してしまう。未パースの設定値を止める。"""
    with pytest.raises(ValueError):
        D.dem_slope(np.zeros((9, 9)), bad)


@pytest.mark.parametrize("bad", ["45", True, -5.0, 400.0])
def test_a_bad_angle_is_refused(bad):
    with pytest.raises(ValueError):
        D.dem_hillshade(np.zeros((9, 9)), 1.0, azimuth_deg=bad)


def test_too_few_azimuths_for_a_sky_view_factor_is_refused():
    with pytest.raises(ValueError, match="n_azimuth must be >= 4"):
        D.dem_sky_view_factor(np.zeros((9, 9)), 1.0, n_azimuth=2)


def test_an_observer_outside_the_grid_is_refused():
    with pytest.raises(ValueError, match="outside"):
        D.dem_viewshed(np.zeros((9, 9)), 1.0, (20, 3))


# =========================================================================
# 8. 台帳としての最低限
# =========================================================================

def test_every_public_op_is_exported_and_callable():
    z = plane(15, 15, 5.0, 10.0, 45.0)
    for name in D.__all__:
        obj = getattr(D, name)
        if not callable(obj):
            continue
        assert name.startswith("dem_"), name


def test_the_module_states_the_conventions_that_silently_break_things():
    doc = D.__doc__ or ""
    for probe in ("北を 0 度", "行 0 が北", "メートル", "terrain"):
        assert probe in doc, f"規約の記述 {probe!r} が docstring から消えている"


# =========================================================================
# 9. 台帳とガイド —— 「載っているが走っていない」を防ぐ
# =========================================================================

def test_the_ledger_lists_every_op_and_finds_its_implementation():
    """``opsdem`` が ``demops`` の全 op を持ち、実体が全部見つかること。

    台帳に載っていない op は docs/ops にも Studio ヘルプにも 1 枚も出ず、
    連鎖ファザーも一度も呼ばない(この repo が 2026-09-02 に 192 op で
    踏んだ形)。数を突き合わせるのは、片方だけ足したときに気づくため。
    """
    import opsdem
    public = {n for n in D.__all__ if callable(getattr(D, n))}
    assert set(opsdem.OPSDEM) == public
    assert opsdem.missing() == []


def test_the_ledger_declares_a_chainable_output_for_fill_sinks():
    """埋めた結果は**まだ標高格子**。ここを image2d と宣言すると、族内の
    連鎖(埋める → 流す)が型で切れて、水文の 3 op が到達しなくなる。"""
    import opsdem
    assert opsdem.OPSDEM["dem_fill_sinks"]["out"] == "depth"
    assert opsdem.OPSDEM["dem_fill_sinks"]["in"] == ["depth"]
    # 実際に繋がることを型宣言と別に確かめる(宣言だけでは繋がらない)
    z = -_gauss_hill(2.0, half_extent=24.0, amp=6.0, sigma=8.0)[0]  # 窪地を作る
    filled = opsdem.call("dem_fill_sinks", z, 1e-6)
    d = opsdem.call("dem_flow_direction", filled, 2.0)
    assert d.shape == z.shape


def test_the_fuzzer_can_build_arguments_for_every_dem_op():
    """必須引数(``cell_size`` / ``azimuth_deg`` / ``observer_rc``)が
    ``PARAM_HINTS`` に無いと、13 op すべてが「引数が組めない」で静かに
    スキップされる —— 台帳に載せる作業とは**別の作業**なので別に固定する。"""
    import inspect
    import sys as _sys

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.join(ROOT, "tools") not in _sys.path:
        _sys.path.insert(0, os.path.join(ROOT, "tools"))
    from typed_catalog import PARAM_HINTS

    import opsdem
    unbindable = []
    for name, meta in opsdem.OPSDEM.items():
        sig = inspect.signature(meta["func"])
        data = len(meta["in"])
        for p in list(sig.parameters.values())[data:]:
            if p.default is inspect.Parameter.empty and p.name not in PARAM_HINTS:
                unbindable.append(f"{name}.{p.name}")
    assert not unbindable, f"ファザーが束縛できない必須引数: {unbindable}"


def test_the_family_guide_python_snippet_actually_runs():
    """ガイドの最小例を**実行**する。読めるだけの例は、規約(北 0 度・東回り、
    行 0 が北)を取り違えたまま記事へコピーされる。"""
    import re
    guide = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "docs", "ops", "dem", "guides", "dem_terrain_analysis.md")
    with open(guide, encoding="utf-8") as f:
        blocks = re.findall(r"```python\n(.*?)```", f.read(), re.S)
    runnable = [b for b in blocks if "import demops" in b]
    assert runnable, "dem ガイドから実行できる例が消えている"
    for src in runnable:
        exec(compile(src, guide, "exec"), {"__name__": "__guide__"})


# =========================================================================
# 10. 地心座標(ECEF / 地心球)と地球曲率
# =========================================================================

def test_ecef_hits_the_two_points_we_know_by_definition():
    """赤道の原点は (a, 0, 0)、北極は (0, 0, b)。楕円体の定義そのもの。"""
    eq = D.dem_geodetic_to_ecef(0.0, 0.0, 0.0)
    po = D.dem_geodetic_to_ecef(90.0, 0.0, 0.0)
    b = D.WGS84_A * (1.0 - D.WGS84_F)
    assert eq == pytest.approx([D.WGS84_A, 0.0, 0.0], abs=1e-6)
    assert po == pytest.approx([0.0, 0.0, b], abs=1e-6)


def test_the_geodetic_round_trip_closes():
    """測地 → ECEF → 測地 が戻ること。実測: 緯度 6.4e-12 度、高さ 8.5e-7 m。"""
    rng = np.random.default_rng(0)
    lat = rng.uniform(-89.0, 89.0, 500)
    lon = rng.uniform(-180.0, 180.0, 500)
    h = rng.uniform(-500.0, 9000.0, 500)
    back = D.dem_ecef_to_geodetic(D.dem_geodetic_to_ecef(lat, lon, h))
    assert np.max(np.abs(back[:, 0] - lat)) < 1e-9
    assert np.max(np.abs(((back[:, 1] - lon + 180.0) % 360.0) - 180.0)) < 1e-9
    assert np.max(np.abs(back[:, 2] - h)) < 1e-5


def test_the_geocentric_latitude_is_not_the_geodetic_one():
    """★ 混同しやすいので名指しで固定する。両者は最大 0.19 度ずれる。

    地心緯度(地球中心から見た角度)と測地緯度(楕円体の法線が赤道面となす角)は
    別物。東京(北緯 35.684 度)で 0.182 度 = 距離にして約 20 km。
    """
    g = D.dem_geocentric_grid(np.zeros((3, 3)), 35.684, 139.735, 3.88, spherical=True)
    assert 0.17 < 35.684 - g[0, 0, 1] < 0.19
    # 赤道と極では一致する(定義から)
    for lat in (0.0, 90.0):
        gg = D.dem_geocentric_grid(np.zeros((3, 3)), lat, 0.0, 1.0, spherical=True)
        assert abs(lat - gg[0, 0, 1]) < 1e-6


def test_the_geocentric_grid_round_trips_through_geodetic():
    dem = np.linspace(0.0, 100.0, 25).reshape(5, 5)
    xyz = D.dem_geocentric_grid(dem, 35.684, 139.735, 10.0)
    assert xyz.shape == (5, 5, 3)
    back = D.dem_ecef_to_geodetic(xyz)
    assert np.max(np.abs(back[..., 2] - dem)) < 1e-5     # 高さが戻る
    assert back[0, 0, 0] == pytest.approx(35.684, abs=1e-9)
    assert back[0, 0, 1] == pytest.approx(139.735, abs=1e-9)
    # 行が増えると南へ、列が増えると東へ
    assert back[1, 0, 0] < back[0, 0, 0]
    assert back[0, 1, 1] > back[0, 0, 1]


@pytest.mark.parametrize("dist,plain,refracted", [
    (1000.0, 0.0785, 0.0683), (5000.0, 1.9620, 1.7070),
    (10000.0, 7.8480, 6.8278), (30000.0, 70.632, 61.450),
])
def test_the_curvature_drop_matches_the_survey_table(dist, plain, refracted):
    assert D.dem_earth_curvature_drop(dist, 0.0) == pytest.approx(plain, rel=1e-3)
    assert D.dem_earth_curvature_drop(dist) == pytest.approx(refracted, rel=1e-3)


def test_the_web_mercator_cell_size_depends_on_latitude():
    """赤道の値を東京で使うと傾斜が 23 % 過小になる —— この族で最も多い事故。"""
    tokyo = D.dem_cell_size_webmercator(15, 35.684)
    equator = D.dem_cell_size_webmercator(15, 0.0)
    assert tokyo == pytest.approx(3.880, abs=0.002)      # 実データで確認した値
    assert equator == pytest.approx(4.777, abs=0.002)
    assert (equator - tokyo) / equator == pytest.approx(0.188, abs=0.005)
    # ズームが 1 上がると半分
    assert D.dem_cell_size_webmercator(16, 35.684) == pytest.approx(tokyo / 2)


def test_an_equiangular_grid_needs_the_geodetic_slope():
    """緯度経度の等角度格子を、一定のセル寸法で dem_slope に渡すと狂う。

    ★ 書き始めは「東西が過大になる」と思っていたが、測ったら**半分**だった。
    緯度方向の寸法(北緯 60 度で経度方向の 2 倍)を両軸に使うと、東西の勾配は
    「長すぎるセル」で割られて**過小**になる。向きは何を定数にしたかで決まる。
    """
    h = w = 41
    d_lat = d_lon = 1.0 / 3600.0                      # 1 秒メッシュ
    lat0 = 60.0
    # 東西方向にだけ 1 m/セル(実距離)で下る面を、等角度格子として作る
    n_rad = D.WGS84_A / np.sqrt(1 - D.WGS84_F * (2 - D.WGS84_F) * np.sin(np.radians(lat0)) ** 2)
    dx_m = np.radians(d_lon) * n_rad * np.cos(np.radians(lat0))
    z = -np.mgrid[0:h, 0:w][1] * dx_m * 0.1           # 東へ 10 % 下る
    good = D.dem_geodetic_slope(z, lat0, d_lat, d_lon)[3:-3, 3:-3]
    naive = D.dem_slope(z, np.radians(d_lat) * D.WGS84_A)[3:-3, 3:-3]
    want = np.degrees(np.arctan(0.1))
    assert np.mean(good) == pytest.approx(want, abs=0.01), np.mean(good)
    assert np.mean(naive) < 0.6 * np.mean(good), (np.mean(naive), np.mean(good))


def test_the_geocentric_ops_are_validated():
    with pytest.raises(ValueError, match=r"\[-90, 90\]"):
        D.dem_geodetic_to_ecef(91.0, 0.0)
    with pytest.raises(ValueError, match="finite"):
        D.dem_geodetic_to_ecef(0.0, 0.0, np.inf)
    with pytest.raises(ValueError, match="trailing axis of 3"):
        D.dem_ecef_to_geodetic(np.zeros((4, 2)))
    with pytest.raises(ValueError, match="distance_m"):
        D.dem_earth_curvature_drop(-1.0)
    with pytest.raises(ValueError, match="refraction"):
        D.dem_earth_curvature_drop(100.0, refraction=1.0)
    with pytest.raises(ValueError, match="zoom"):
        D.dem_cell_size_webmercator(30, 0.0)
    with pytest.raises(ValueError, match="Web Mercator range"):
        D.dem_cell_size_webmercator(15, 89.0)
    with pytest.raises(ValueError, match="d_lat_deg"):
        D.dem_geodetic_slope(np.zeros((9, 9)), 35.0, 0.0, 1.0)
