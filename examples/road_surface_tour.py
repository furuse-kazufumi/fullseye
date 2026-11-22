# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""road_surface_tour — 横断の決まりを持つ道の面を、セルごとの解析の真値つきで作る(新規 op ``road_surface_heightmap``)。

    py -3.11 examples/road_surface_tour.py

【この例が示すこと】
1. **直線の道** —— 勾配 6 %・拝み勾配 2 % の 2 車線。高さ図が世界の座標の閉形式 z = g·x − c·|y| に 1e-12 で一致し、
   真値の勾配 0.06・横勾配 ∓0.02 を返す。
2. **ヘアピン(半径 35 m の円弧)** —— 線形は既存の ``clothoid_points``。円の中心からの極座標の閉形式
   z = g·R·φ − c·|R − r| に 1e-9 で一致する(局所の円弧へ射影し直すので、折線の頂点の mm の段が出ない)。
   中心線の勾配 6 % に対し、内側の車線は 6.3 %、外側は 5.8 %(1/(1 − κe))。
3. **片勾配のすりつけ** —— 道路構造令の表(``TRANSITION_LENGTH``: 設計速度 30 km/h → 25 m、``MAX_SUPERELEVATION``)
   の長さで拝み → 片勾配 6 % へ。右の車線の横勾配は途中で 0(平ら = 水が流れない所)を通る。
4. **放物線の縦断曲線** —— 2 m おきの標本の間でも z_c(s) が閉形式に一致する(3 次 Hermite)。
5. **既存の op で読み戻す** —— 回した直線の道の車線の窓を ``crop_rectangle2`` → ``surface_form_remove`` に
   かけると係数が (g, −c) に戻り、``dem_slope`` の中央値が atan(√(g² + c²)) になる。
6. **地形へなじませる** —— 外側の地形(同じ格子)へ 5 m から 4.5 m かけて混ぜる。車道は地形に依らずビット一致。

【グラウンドトゥルース】作った線形の閉形式(直線・円・放物線)と道路構造令の表。真値は作り方の偏微分で、
数値微分ではない(高さ図の中心差分と 1e-5 で合うことも確かめる)。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import examplefig as figs     # noqa: E402
import fullseye as fs          # noqa: E402
import demops                  # noqa: E402
import drivelateral as DL      # noqa: E402
import image_gen               # noqa: E402
import roughness               # noqa: E402

LG = fs.ledger                 # 台帳(opsdrive の lateral)から名前で呼ぶ


def centres(H, T):
    ext, c = T["extent"], T["cell"]
    return np.meshgrid(ext[0] + (np.arange(H.shape[1]) + 0.5) * c, ext[2] + (np.arange(H.shape[0]) + 0.5) * c)


def main() -> int:
    checks = []
    # ---- 1. 直線の道 -------------------------------------------------------------------- #
    s = np.arange(0.0, 40.01, 0.5)
    straight = {"x": s, "y": np.zeros_like(s), "z": 0.06 * s, "s": s}
    H, T = DL.road_surface_heightmap(straight, 0.1, extent=(5.0, 35.0, -3.4, 3.4), return_truth=True)
    X, Y = centres(H, T)
    err = float(np.abs(H - (0.06 * X - 0.02 * np.abs(Y))).max())
    print("1. 直線: 閉形式との差の最大 %.1e m、真値の勾配 %.4f、横勾配 左 %.3f / 右 %.3f"
          % (err, float(np.median(T["grade"])), float(np.median(T["cross"][Y > 0])), float(np.median(T["cross"][Y < 0]))))
    checks.append(err < 1e-12 and np.allclose(T["grade"], 0.06))
    assert np.array_equal(LG.road_surface_heightmap(straight, 0.1, extent=(5.0, 35.0, -3.4, 3.4)), H)   # 台帳は高さ図

    # ---- 2. ヘアピン(半径 35 m) -------------------------------------------------------- #
    R, g = 35.0, 0.06
    L = math.pi * R
    ss = np.arange(0.0, L + 1e-9, 1.0)
    cp = DL.clothoid_points(L, ss, kappa0=1.0 / R, kappa1=1.0 / R)
    arc = {"x": cp["points"][:, 0], "y": cp["points"][:, 1], "z": g * ss, "s": ss,
           "heading": cp["heading"], "curvature": cp["curvature"]}
    Ha, Ta = DL.road_surface_heightmap(arc, 0.1, extent=(-6.0, 42.0, -6.0, 76.0), return_truth=True)
    X, Y = centres(Ha, Ta)
    r, phi = np.hypot(X, Y - R), np.arctan2(X, R - Y)
    e = R - r
    on = (phi > 0.05) & (phi < math.pi - 0.05) & (np.abs(e) < 3.4)
    err = float(np.abs(Ha - (g * R * phi - 0.02 * np.abs(e)))[on].max())
    g_in = float(np.median(Ta["grade"][on & (np.abs(e - 1.5) < 0.1)]))
    g_out = float(np.median(Ta["grade"][on & (np.abs(e + 1.5) < 0.1)]))
    print("2. ヘアピン R 35 m: 極座標の閉形式との差 %.1e m、勾配 内側の車線 %.4f(閉形式 %.4f)/ 外側 %.4f(%.4f)"
          % (err, g_in, g * R / (R - 1.5), g_out, g * R / (R + 1.5)))
    gerr = float(np.abs(Ta["grade"] - g * R / (R - e))[on].max())       # セルごとに 1/(1 − κe) の閉形式
    print("   真値の勾配と閉形式 g·R/(R − e) の差の最大 %.1e" % gerr)
    checks.append(err < 1e-9 and gerr < 1e-9 and g_in > g > g_out)

    # ---- 3. 片勾配のすりつけ(道路構造令の表) -------------------------------------------- #
    L_run, rate = float(DL.TRANSITION_LENGTH[30]), 0.06
    sr = np.arange(0.0, 60.01, 0.5)
    runoff = {"x": sr, "y": np.zeros_like(sr), "z": 0.04 * sr, "s": sr,
              "beta": np.clip((sr - 10.0) / L_run, 0.0, 1.0), "rate": np.full_like(sr, rate)}
    Hr, Tr = DL.road_surface_heightmap(runoff, 0.1, extent=(0.0, 60.0, -3.4, 3.4), return_truth=True)
    X, Y = centres(Hr, Tr)
    i_r = int(np.argmin(np.abs(Y[:, 0] + 1.55)))
    i_l = int(np.argmin(np.abs(Y[:, 0] - 1.55)))
    xr = X[0].copy()
    cr, cl = Tr["cross"][i_r], Tr["cross"][i_l]
    flat_at = float(X[0][int(np.argmin(np.abs(cr)))])
    print("3. すりつけ %.0f m(設計速度 30 km/h の表)、片勾配 %.2f(表の上限 %.2f): 右の車線の横勾配 %.3f → %.3f、"
          "平らになる所 s = %.2f m(閉形式 %.2f)"
          % (L_run, rate, DL.MAX_SUPERELEVATION["other"], cr[0], cr[-1], flat_at, 10.0 + L_run * 0.02 / (0.02 + rate)))
    checks.append(abs(cr[0] - 0.02) < 1e-12 and abs(cr[-1] + rate) < 1e-12
                  and abs(flat_at - (10.0 + L_run * 0.02 / (0.02 + rate))) <= 0.05)

    # ---- 4. 放物線の縦断曲線 ------------------------------------------------------------ #
    g1, g2, Lv = 0.02, 0.09, 30.0
    sv = np.arange(0.0, Lv + 1e-9, 2.0)
    vc = {"x": sv, "y": np.zeros_like(sv), "z": g1 * sv + (g2 - g1) * sv ** 2 / (2 * Lv), "s": sv}
    Hv, Tv = DL.road_surface_heightmap(vc, 0.1, extent=(0.0, 30.0, -0.05, 0.05), return_truth=True)
    xv = (np.arange(Hv.shape[1]) + 0.5) * 0.1
    err = float(np.abs(Hv[0] - (g1 * xv + (g2 - g1) * xv ** 2 / (2 * Lv))).max())
    print("4. 縦断曲線(2 m おきの標本): 閉形式との差の最大 %.1e m" % err)
    checks.append(err < 1e-12)

    # ---- 5. 既存の op で読み戻す ---------------------------------------------------------- #
    psi, gg, cc, cell = 0.7, 0.07, 0.02, 0.05
    sl = np.arange(-5.0, 45.01, 0.5)
    rot = {"x": sl * math.cos(psi), "y": sl * math.sin(psi), "z": gg * sl, "s": sl,
           "heading": np.full_like(sl, psi), "curvature": np.zeros_like(sl)}
    Hp, Tp = DL.road_surface_heightmap(rot, cell, extent=(-2.0, 36.0, -4.0, 30.0), return_truth=True)
    xw, yw = 20.0 * math.cos(psi) - 1.5 * math.sin(psi), 20.0 * math.sin(psi) + 1.5 * math.cos(psi)
    win = image_gen.crop_rectangle2(Hp, (yw - Tp["extent"][2]) / cell - 0.5, (xw - Tp["extent"][0]) / cell - 0.5,
                                    psi, 20.0, 18.0)
    _res, coef = roughness.surface_form_remove(win, cell, order=1)
    lane = DL.road_surface_heightmap({"x": sl, "y": np.zeros_like(sl), "z": gg * sl, "s": sl}, 0.1,
                                     extent=(5.0, 35.0, 0.3, 2.7))
    slope_med = float(np.median(demops.dem_slope(lane, 0.1)))
    print("5. crop_rectangle2 → surface_form_remove: (縦断, 横) = (%.6f, %.6f)(作った値 %.2f, %.2f)、"
          "dem_slope の中央値 %.6f°(閉形式 %.6f°)"
          % (coef[1], coef[2], gg, -cc, slope_med, math.degrees(math.atan(math.hypot(gg, cc)))))
    checks.append(abs(coef[1] - gg) < 1e-9 and abs(coef[2] + cc) < 1e-9
                  and abs(slope_med - math.degrees(math.atan(math.hypot(gg, cc)))) < 1e-9)

    # ---- 6. 地形へなじませる ------------------------------------------------------------ #
    H0, T0 = DL.road_surface_heightmap(straight, 0.1, return_truth=True)
    X, Y = centres(H0, T0)
    terr = 0.3 * np.abs(Y) + 0.01 * X + 0.2 * np.sin(X / 3.0)
    H1, T1 = DL.road_surface_heightmap(straight, 0.1, terrain=terr, return_truth=True)
    car = T0["carriageway"]
    print("6. 地形へなじませる: 車道 %d セルはビット一致 %s、混ぜたセルの真値は nan %d"
          % (int(car.sum()), bool(np.array_equal(H1[car], H0[car])), int(np.isnan(T1["grade"]).sum())))
    checks.append(np.array_equal(H1[car], H0[car]) and np.isnan(T1["grade"]).sum() > 0)

    # 図は北を上に(格子の行 0 = 南なので上下を返す)。真値は車道のセルだけ(ヘアピンの中心へ行くと 1/(1 − κe) が発散する)
    car = Ta["carriageway"]
    figs.save("hairpin_heights", Ha[::-1], "ヘアピン(半径 35 m、勾配 6 %、拝み 2 %)の高さ図 [m](北が上)",
              colorbar=True, unit="m")
    figs.save_grid("hairpin_truth", [np.where(car, Ta["grade"], np.nan)[::-1], np.where(car, Ta["cross"], np.nan)[::-1]],
                   ["真値の縦断勾配(内側ほど急、車道の縁で 5.5〜6.7 %)", "真値の横勾配(+ で左が上がる、拝みで ∓2 %)"],
                   title="road_surface_heightmap の解析の真値(車道のセル)", colorbar=True)
    figs.save_plot("runoff_cross", [("左の車線", xr, cl), ("右の車線", xr, cr)],
                   xlabel="s [m]", ylabel="横勾配 ∂z/∂e", title="片勾配のすりつけ(25 m、6 %)",
                   caption="拝み 2 % から片勾配 6 % へ。右の車線は途中で平ら(0)を通る。")
    figs.save("blend", H1[::-1], "地形へなじませた道(車道はそのまま、5 m から 4.5 m かけて地形へ。北が上)",
              colorbar=True, unit="m")

    ok_all = all(bool(c) for c in checks)
    print("PASS" if ok_all else "FAIL", "(%d / %d)" % (sum(bool(c) for c in checks), len(checks)))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
