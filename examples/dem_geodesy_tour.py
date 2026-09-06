# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""地心座標と地球の丸み —— 測地 ⇄ ECEF の往復、DEM の地心格子、曲率落ち、緯度で変わるセル寸法。

    py -3.11 examples/dem_geodesy_tour.py

【この例が示すこと】
DEM を「地球中心から見た座標」で扱う 6 つの op(``dem_geodetic_to_ecef`` /
``dem_ecef_to_geodetic`` / ``dem_geocentric_grid`` / ``dem_earth_curvature_drop`` /
``dem_cell_size_webmercator`` / ``dem_geodetic_slope``)を、**式で答えが決まる入力**
だけで通し、返り値を閉形式と突き合わせる。

【グラウンドトゥルース(どれも式で決まる)】
1. 赤道上の本初子午線 (0, 0, 0) は ECEF で (a, 0, 0)、北極 (90, 0, 0) は (0, 0, b)。
   楕円体上の点は必ず x²/a² + y²/a² + z²/b² = 1 を満たし、高さ h を足すと**法線方向**へ
   ちょうど h [m] 動く(法線 = (cosφ cosλ, cosφ sinλ, sinφ))。
2. 測地 → ECEF → 測地の往復は緯度経度 1e-9 度・高さ 1e-6 m 以内で戻る(docstring の
   主張は 1e-12 度 / 1e-7 m。ここでは実測を印字して、その桁で assert する)。
3. 地心緯度と測地緯度の差は atan((1-e²) tanφ) と φ の差 —— 緯度 45 度で **0.19 度**。
4. ``dem_geocentric_grid`` の隣接セル間距離は ``cell_size`` に一致し(相対 1e-4 以内)、
   北西角は ``dem_geodetic_to_ecef(lat0, lon0)`` そのもの。ECEF 側を測地に戻せば
   標高がそのまま(1e-6 m)返る。``spherical=True`` の半径は |xyz| と一致し、
   地心緯度は閉形式 atan((1-e²) tanφ) と一致する。
5. 曲率落ちは (1-k) d²/(2R)。docstring の表(1 / 5 / 10 / 30 km)と 5 mm 以内で一致し、
   距離 2 倍で 4 倍になる。
6. Web メルカトルの分解能はズーム 0・赤道で 2πa/256 = 156543.0339 m、ズームが 1 上がると
   半分、東京(北緯 35.68 度)の z=15 で 3.880 m(赤道 4.777 m)。
7. 緯度経度の格子に置いた**東西傾斜 10 度の平面**は、``dem_geodetic_slope`` では 10 度、
   緯度方向の寸法を両軸に使った素朴な ``dem_slope`` では atan(tan10° · cos φ · N/M) になる
   (北緯 60 度で約半分の 5.06 度)。南北傾斜の平面ではどちらも 10 度。

【読み方】
各節は「与えたもの / 返ったもの / 閉形式 / 差」を印字する。差が閾値を超えると assert で
落ちる。最後に所要秒数を印字する(60 秒未満が規約)。

★EXTEND: 実際の緯度経度・標高タイルに差し替えるときは ``LAT0`` / ``LON0`` / ``dem``
を自分のデータにし、セル寸法は ``dem_cell_size_webmercator(zoom, 緯度)`` で計算する
(赤道の値をそのまま使うと東京で傾斜が 23 % 過小になる)。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

# ★リポジトリ直下を通しておかないと ``demops`` が見つからない(この例は
#   `fullseye` を import しないので、パスフックが効かない)。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import demops                                                    # noqa: E402

# WGS84 の定数(demops と同じ値。ここでは「閉形式を自分で組む」ために再掲する)。
A = demops.WGS84_A                          # 長半径 [m]
F = demops.WGS84_F                          # 扁平率
E2 = F * (2.0 - F)                          # 第一離心率の二乗
B = A * (1.0 - F)                           # 短半径 [m] = 6356752.314245...
R_MEAN = demops.EARTH_MEAN_RADIUS           # 曲率落ちに使う平均半径 [m]

# ★EXTEND: 自分のタイルの北西角に差し替える(ここは東京付近)。
LAT0, LON0 = 35.68, 139.76


def _radii(lat_deg):
    """子午線曲率半径 M と卯酉線曲率半径 N [m](閉形式)。"""
    sp = math.sin(math.radians(lat_deg))
    m_rad = A * (1.0 - E2) / (1.0 - E2 * sp * sp) ** 1.5
    n_rad = A / math.sqrt(1.0 - E2 * sp * sp)
    return m_rad, n_rad


def _geocentric_lat(lat_deg):
    """測地緯度 → 地心緯度 [度](楕円体上、h = 0)。atan((1-e²) tanφ)。"""
    return math.degrees(math.atan((1.0 - E2) * math.tan(math.radians(lat_deg))))


def run() -> dict:
    """全節を実行し、検算した数字を dict で返す。"""
    t0 = time.perf_counter()
    out: dict = {}

    # ------------------------------------------------------------------ 1
    print("=== 1. 測地 → ECEF —— 赤道・極・楕円体面・法線 ===")
    # スカラ入力でも返りは (N, 3)(台帳の宣言 points に合わせて畳まれる)。
    p_eq = demops.dem_geodetic_to_ecef(0.0, 0.0, 0.0)
    p_np = demops.dem_geodetic_to_ecef(90.0, 0.0, 0.0)
    p_e90 = demops.dem_geodetic_to_ecef(0.0, 90.0, 0.0)
    assert p_eq.shape == (1, 3), f"スカラ入力の返りは (1, 3) のはず: {p_eq.shape}"
    print(f"  (0, 0, 0)  → {p_eq[0]}   閉形式 ({A:.1f}, 0, 0)")
    print(f"  (90, 0, 0) → {p_np[0]}   閉形式 (0, 0, {B:.6f})")
    print(f"  (0, 90, 0) → {p_e90[0]}   閉形式 (0, {A:.1f}, 0)")
    assert np.allclose(p_eq[0], [A, 0.0, 0.0], atol=1e-6)
    assert np.allclose(p_np[0], [0.0, 0.0, B], atol=1e-6)
    assert np.allclose(p_e90[0], [0.0, A, 0.0], atol=1e-6)

    # 楕円体上の点(h=0)は x²/a² + y²/a² + z²/b² = 1 を満たす —— 実装と独立な検算。
    rng = np.random.default_rng(0)
    lat = rng.uniform(-89.0, 89.0, 200)
    lon = rng.uniform(-180.0, 180.0, 200)
    p0 = demops.dem_geodetic_to_ecef(lat, lon, 0.0)
    ellip = (p0[:, 0] ** 2 + p0[:, 1] ** 2) / A ** 2 + p0[:, 2] ** 2 / B ** 2
    print(f"  楕円体方程式 x²/a²+y²/a²+z²/b² の最大ずれ {np.max(np.abs(ellip - 1.0)):.2e}")
    assert np.max(np.abs(ellip - 1.0)) < 1e-12

    # 高さ h を足すと法線方向へちょうど h 動く。
    h = 1234.5
    p1 = demops.dem_geodetic_to_ecef(lat, lon, h)
    phi, lam = np.radians(lat), np.radians(lon)
    normal = np.stack([np.cos(phi) * np.cos(lam), np.cos(phi) * np.sin(lam), np.sin(phi)], -1)
    shift_err = np.max(np.linalg.norm((p1 - p0) - h * normal, axis=1))
    print(f"  高さ {h} m を足した移動と法線×h の最大差 {shift_err:.2e} m")
    assert shift_err < 1e-6
    out["ellipsoid_residual"] = float(np.max(np.abs(ellip - 1.0)))
    out["normal_shift_err_m"] = float(shift_err)

    # ------------------------------------------------------------------ 2
    print("\n=== 2. ECEF → 測地 —— 往復誤差と極 ===")
    lats = np.linspace(-89.9, 89.9, 37)
    lons = np.linspace(-180.0, 180.0, 25)
    hs = np.array([-500.0, 0.0, 8848.0, 20000.0])
    LA, LO, HH = np.meshgrid(lats, lons, hs, indexing="ij")
    xyz = demops.dem_geodetic_to_ecef(LA.ravel(), LO.ravel(), HH.ravel())
    back = demops.dem_ecef_to_geodetic(xyz)
    d_lat = np.max(np.abs(back[:, 0] - LA.ravel()))
    # 経度は ±180 が同じ点なので、差は 360 で畳んでから測る。
    d_lon = np.max(np.abs((back[:, 1] - LO.ravel() + 180.0) % 360.0 - 180.0))
    d_h = np.max(np.abs(back[:, 2] - HH.ravel()))
    print(f"  {xyz.shape[0]} 点の往復: 緯度 {d_lat:.2e} 度 / 経度 {d_lon:.2e} 度 / 高さ {d_h:.2e} m")
    print("  (docstring の主張は 1e-12 度 / 1e-7 m。ここでは 1e-9 度 / 1e-6 m で判定)")
    assert d_lat < 1e-9 and d_lon < 1e-9 and d_h < 1e-6
    out["roundtrip_deg"] = float(max(d_lat, d_lon))
    out["roundtrip_m"] = float(d_h)

    # 極では cos φ = 0 で通常の高さの式が壊れるので、別枝 |z| - b が使われる。
    pole = demops.dem_ecef_to_geodetic(np.array([[0.0, 0.0, B + 1000.0]]))[0]
    print(f"  北極 +1000 m → 緯度 {pole[0]:.9f} / 高さ {pole[2]:.6f} m(閉形式 90 / 1000)")
    assert abs(pole[0] - 90.0) < 1e-9 and abs(pole[2] - 1000.0) < 1e-6

    # 地心緯度 ≠ 測地緯度: 楕円体上の緯度 45 度の点を地球中心から見た角度。
    p45 = demops.dem_geodetic_to_ecef(45.0, 0.0, 0.0)[0]
    geoc = math.degrees(math.asin(p45[2] / np.linalg.norm(p45)))
    print(f"  測地緯度 45 度の地心緯度 {geoc:.6f} 度(閉形式 {_geocentric_lat(45.0):.6f})"
          f" → 差 {45.0 - geoc:.4f} 度 ≈ {(45.0 - geoc) * math.pi / 180 * R_MEAN / 1e3:.1f} km")
    assert abs(geoc - _geocentric_lat(45.0)) < 1e-9
    out["geocentric_minus_geodetic_deg_at45"] = float(geoc - 45.0)

    # ------------------------------------------------------------------ 3
    print("\n=== 3. dem_geocentric_grid —— 格子の各セルを地球中心から見る ===")
    cell = 10.0
    hgrid, wgrid = 33, 33
    # ★EXTEND: dem を実データに差し替える(行 0 が北)。ここは既知の傾斜面。
    yy, xx = np.mgrid[0:hgrid, 0:wgrid].astype(np.float64)
    dem = 100.0 + 0.5 * xx * cell - 0.25 * yy * cell
    g = demops.dem_geocentric_grid(dem, LAT0, LON0, cell)
    assert g.shape == (hgrid, wgrid, 3)
    nw = demops.dem_geodetic_to_ecef(LAT0, LON0, dem[0, 0])[0]
    print(f"  北西角 {g[0, 0]} と dem_geodetic_to_ecef {nw} の差 {np.linalg.norm(g[0, 0] - nw):.2e} m")
    assert np.linalg.norm(g[0, 0] - nw) < 1e-6
    # 隣接セル間の弦長(標高差を除いた水平成分が cell に一致するかを見るため、
    # 平坦な格子でも測る)。
    flat = np.zeros((hgrid, wgrid))
    gf = demops.dem_geocentric_grid(flat, LAT0, LON0, cell)
    d_east = np.linalg.norm(np.diff(gf, axis=1), axis=-1)      # 東隣との距離
    d_south = np.linalg.norm(np.diff(gf, axis=0), axis=-1)     # 南隣との距離
    rel_e = np.max(np.abs(d_east / cell - 1.0))
    rel_s = np.max(np.abs(d_south / cell - 1.0))
    print(f"  隣接セル間距離の相対ずれ 東 {rel_e:.2e} / 南 {rel_s:.2e}(格子 {hgrid}x{wgrid}・{cell} m)")
    print("  → 東西は北西角の緯度で寸法を固定しているので、南へ行くほど cos φ ぶんだけ縮む"
          f"(理論値 tanφ·Δφ ≈ {math.tan(math.radians(LAT0)) * hgrid * cell / _radii(LAT0)[0]:.1e})。")
    assert rel_e < 1e-4 and rel_s < 1e-4
    # ECEF → 測地で標高がそのまま戻り、行 0 の緯度・列 0 の経度が北西角に一致する。
    back = demops.dem_ecef_to_geodetic(g.reshape(-1, 3)).reshape(hgrid, wgrid, 3)
    h_err = np.max(np.abs(back[..., 2] - dem))
    print(f"  格子を測地に戻した標高の最大差 {h_err:.2e} m / 行 0 の緯度差 "
          f"{np.max(np.abs(back[0, :, 0] - LAT0)):.2e} 度 / 列 0 の経度差 "
          f"{np.max(np.abs(back[:, 0, 1] - LON0)):.2e} 度")
    assert h_err < 1e-6
    assert np.max(np.abs(back[0, :, 0] - LAT0)) < 1e-9
    assert np.max(np.abs(back[:, 0, 1] - LON0)) < 1e-9
    # spherical=True: 半径は |xyz|、地心緯度は閉形式、経度は列 0 で lon0。
    gs = demops.dem_geocentric_grid(flat, LAT0, LON0, cell, spherical=True)
    r_err = np.max(np.abs(gs[..., 0] - np.linalg.norm(gf, axis=-1)))
    print(f"  spherical: 半径と |xyz| の差 {r_err:.2e} m / 北西角の地心緯度 {gs[0, 0, 1]:.6f} 度"
          f"(閉形式 {_geocentric_lat(LAT0):.6f}、測地緯度との差 {gs[0, 0, 1] - LAT0:.4f} 度)")
    assert r_err < 1e-6
    assert abs(gs[0, 0, 1] - _geocentric_lat(LAT0)) < 1e-9
    assert abs(gs[0, 0, 2] - LON0) < 1e-9
    out["grid_spacing_rel_err"] = float(max(rel_e, rel_s))
    out["grid_height_roundtrip_m"] = float(h_err)

    # ------------------------------------------------------------------ 4
    print("\n=== 4. 地球曲率落ち —— docstring の表と閉形式 ===")
    table = {1e3: (0.078, 0.068), 5e3: (1.962, 1.707), 10e3: (7.848, 6.828), 30e3: (70.63, 61.45)}
    print(f"  {'距離':>8}{'曲率のみ':>12}{'屈折込み':>12}{'表(曲率)':>12}{'表(屈折)':>12}")
    for d, (t_pure, t_refr) in table.items():
        pure = float(demops.dem_earth_curvature_drop(d, refraction=0.0))
        refr = float(demops.dem_earth_curvature_drop(d))
        print(f"  {d / 1e3:>6.0f} km{pure:>12.3f}{refr:>12.3f}{t_pure:>12.3f}{t_refr:>12.3f}")
        assert abs(pure - d * d / (2.0 * R_MEAN)) < 1e-9                  # 閉形式
        assert abs(refr - (1.0 - 0.13) * d * d / (2.0 * R_MEAN)) < 1e-9
        assert abs(pure - t_pure) < 5e-3 and abs(refr - t_refr) < 5e-3    # 表(3 桁)
    # 2 次: 距離 2 倍で 4 倍。配列入力もそのまま通る。
    ds = np.array([1e3, 2e3, 4e3])
    drops = demops.dem_earth_curvature_drop(ds)
    print(f"  距離 1/2/4 km の落ち {drops} → 比 {drops[1] / drops[0]:.6f} / {drops[2] / drops[1]:.6f}(閉形式 4)")
    assert abs(drops[1] / drops[0] - 4.0) < 1e-12 and abs(drops[2] / drops[1] - 4.0) < 1e-12
    out["curvature_drop_30km_m"] = float(demops.dem_earth_curvature_drop(30e3))

    # ------------------------------------------------------------------ 5
    print("\n=== 5. Web メルカトルのセル寸法 —— 緯度で変わる ===")
    z0 = float(demops.dem_cell_size_webmercator(0, 0.0))
    print(f"  z=0・赤道 {z0:.8f} m/px(閉形式 2πa/256 = {2 * math.pi * A / 256:.8f})")
    assert abs(z0 - 2 * math.pi * A / 256) < 1e-6
    c15_eq = float(demops.dem_cell_size_webmercator(15, 0.0))
    c15_tokyo = float(demops.dem_cell_size_webmercator(15, 35.68))
    c16_tokyo = float(demops.dem_cell_size_webmercator(16, 35.68))
    print(f"  z=15 赤道 {c15_eq:.3f} m / 東京 {c15_tokyo:.3f} m(docstring 4.777 / 3.880)"
          f" / z=16 東京 {c16_tokyo:.3f} m(半分)")
    assert abs(c15_eq - 4.777) < 5e-4 and abs(c15_tokyo - 3.880) < 5e-4
    assert abs(c15_tokyo / c16_tokyo - 2.0) < 1e-12
    assert abs(c15_tokyo / c15_eq - math.cos(math.radians(35.68))) < 1e-12
    # 赤道の値を東京で使うと傾斜が過小になる —— その割合を式で出す。
    under = 1.0 - math.degrees(math.atan(math.tan(math.radians(20.0)) * c15_tokyo / c15_eq)) / 20.0
    print(f"  赤道の寸法で東京の 20 度斜面を測ると {100 * under:.1f} % 過小(docstring「23 %」)")
    out["webmercator_z15_tokyo_m"] = c15_tokyo

    # ------------------------------------------------------------------ 6
    print("\n=== 6. dem_geodetic_slope —— 等角度格子の傾斜(東西と南北で違う) ===")
    n = 41
    d_deg = 1.0 / 3600.0                            # 1 秒メッシュ
    slope_deg = 10.0
    tan_s = math.tan(math.radians(slope_deg))
    for lat0 in (0.0, 35.68, 60.0):
        lat_rows = lat0 - np.arange(n) * d_deg
        m_rows = np.array([_radii(v)[0] for v in lat_rows])
        n_rows = np.array([_radii(v)[1] for v in lat_rows])
        # 行 i の東西 1 セルの実距離 [m] と、南北の累積距離 [m](台形則)。
        dx_rows = math.radians(d_deg) * n_rows * np.cos(np.radians(lat_rows))
        dy_rows = math.radians(d_deg) * m_rows
        y_cum = np.concatenate([[0.0], np.cumsum(0.5 * (dy_rows[1:] + dy_rows[:-1]))])
        cols = np.arange(n)[None, :]
        # (a) 東へ下る平面: z = -tanS · x、x は行ごとに違う東西距離。
        dem_ew = -tan_s * cols * dx_rows[:, None]
        # (b) 南へ下る平面: z = -tanS · y。
        dem_ns = -tan_s * np.broadcast_to(y_cum[:, None], (n, n))
        s_ew = demops.dem_geodetic_slope(dem_ew, lat0, d_deg, d_deg)[3:-3, 3:-3]
        s_ns = demops.dem_geodetic_slope(dem_ns, lat0, d_deg, d_deg)[3:-3, 3:-3]
        # 素朴な計算: 緯度方向の寸法を両軸に使う(公開 DEM で最も多い事故)。
        naive_ew = demops.dem_slope(dem_ew, float(dy_rows[0]))[3:-3, 3:-3]
        # 素朴な値の閉形式: atan(tanS · dx_i / dy_0) の内側平均。
        naive_expect = np.mean(np.degrees(np.arctan(tan_s * dx_rows[3:-3] / dy_rows[0])))
        print(f"  北緯 {lat0:>5.2f}: 東西 {np.mean(s_ew):.6f} 度 / 南北 {np.mean(s_ns):.6f} 度"
              f"(与えた {slope_deg})/ 素朴 {np.mean(naive_ew):.4f} 度(閉形式 {naive_expect:.4f})")
        assert abs(np.mean(s_ew) - slope_deg) < 1e-3, "東西の傾斜が緯度補正後に合わない"
        assert np.max(np.abs(s_ew - slope_deg)) < 1e-2
        assert abs(np.mean(s_ns) - slope_deg) < 1e-3, "南北の傾斜が合わない"
        assert abs(np.mean(naive_ew) - naive_expect) < 1e-3
        out[f"geodetic_slope_ew_lat{lat0:g}"] = float(np.mean(s_ew))
        out[f"naive_slope_ew_lat{lat0:g}"] = float(np.mean(naive_ew))
    print("  → 赤道では素朴な計算でも合う(cos 0 = 1)。北緯 60 度では東西が約半分に出る。")
    # units="percent" は 100·tan。radians は度の変換と一致。
    pct = demops.dem_geodetic_slope(dem_ns, 60.0, d_deg, d_deg, units="percent")[3:-3, 3:-3]
    rad = demops.dem_geodetic_slope(dem_ns, 60.0, d_deg, d_deg, units="radians")[3:-3, 3:-3]
    print(f"  percent {np.mean(pct):.6f}(閉形式 {100 * tan_s:.6f})/ radians {np.mean(rad):.6f}"
          f"(閉形式 {math.radians(slope_deg):.6f})")
    assert abs(np.mean(pct) - 100 * tan_s) < 1e-3
    assert abs(np.mean(rad) - math.radians(slope_deg)) < 1e-5

    out["elapsed_s"] = time.perf_counter() - t0
    return out


if __name__ == "__main__":
    r = run()
    print(f"\n所要 {r['elapsed_s']:.2f} 秒")
    print("PASS")
