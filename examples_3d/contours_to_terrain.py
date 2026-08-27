# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""contours_to_terrain — 等高線(標高付き輪郭)から地形の高さ場(DEM)を復元する。

実世界の問題:
    地形図の **等高線**(各線が一定標高)や、連続断面の輪郭から、面としての地形
    (高さ場 z=f(x,y)、DEM)を作りたい。等高線は線の上でしか標高を与えないので、
    線と線の **間** を面として内挿する必要がある(GIS/測量/地図デジタイズの定番)。

原理と連鎖:
    各等高線の点を (x, y, 標高) の散布点として集め、match3d.fit_poly_surface で
    z=f(x,y) の多項式サーフェスに最小二乗当てはめ、eval_poly_surface で格子(DEM)に
    展開する。「等高線(2D+標高)→ 散布点 → サーフェス当てはめ → 高さ場格子」の連鎖。

グラウンドトゥルース(beat-the-null):
    既知の丘(放物面 z = H - k·((x-cx)^2+(y-cy)^2)、= 2次多項式)の等高線を使う。
    復元 DEM が、等高線の **間** も含めて真の地形に一致する(全域 RMSE が小さい)。
    beat-the-null: 各格子点に「最も近い等高線の標高」を割り当てる階段近似は、線の間で
    大きく外れる(RMSE が当てはめの数倍)。標高一定(平均)の平坦近似はさらに悪い。
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy.spatial import cKDTree

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

import match3d  # fit_poly_surface(x,y,z,degree) / eval_poly_surface(model,x,y)


def main() -> int:
    rng = np.random.default_rng(0)
    S = 60.0
    cx = cy = S / 2.0
    H = 100.0                                   # 山頂標高
    Rr = 26.0                                   # 裾野半径
    k = H / (Rr * Rr)                           # 放物面係数(z = H - k*rho^2)

    def terrain(x, y):
        return H - k * ((x - cx) ** 2 + (y - cy) ** 2)

    # --- 1) 既知地形の等高線(標高付き輪郭)を生成 → 散布点 (x,y,標高) ---
    elevations = np.array([10, 25, 40, 55, 70, 85], dtype=float)   # 6 本の等高線
    cxs, cys, czs = [], [], []
    for e in elevations:
        rho = np.sqrt(max(H - e, 0.0) / k)      # その標高の等高線半径
        t = np.linspace(0, 2 * np.pi, 48, endpoint=False)
        cxs.append(cx + rho * np.cos(t))
        cys.append(cy + rho * np.sin(t))
        czs.append(np.full(t.size, e))
    px = np.concatenate(cxs); py = np.concatenate(cys)
    pz = np.concatenate(czs) + rng.normal(0, 0.5, sum(len(a) for a in czs))  # 測量ノイズ
    print(f"[GT] 等高線 {len(elevations)} 本 → 散布点 {px.size} 個(標高 {elevations.min():.0f}〜{elevations.max():.0f}m)")

    # --- 2) サーフェス当てはめ → DEM 格子へ展開(輪郭→点→面→格子)---
    model = match3d.fit_poly_surface(px, py, pz, degree=2)
    gx, gy = np.meshgrid(np.linspace(6, S - 6, 60), np.linspace(6, S - 6, 60))
    dem = match3d.eval_poly_surface(model, gx, gy)
    print(f"[GT] 当てはめ残差 rms={model['rms']:.3f}m、DEM 格子 {dem.shape}")

    # --- 3) GT: 等高線の「間」も含め全域で真の地形に一致 ---
    truth = terrain(gx, gy)
    inside = ((gx - cx) ** 2 + (gy - cy) ** 2) <= (Rr - 2) ** 2       # 裾野内で評価
    fit_rmse = float(np.sqrt(np.mean((dem[inside] - truth[inside]) ** 2)))

    # beat-null (a): 最も近い等高線の標高を割り当てる階段近似
    tree = cKDTree(np.column_stack([px, py]))
    _, idx = tree.query(np.column_stack([gx[inside], gy[inside]]))
    stair = pz[idx]
    stair_rmse = float(np.sqrt(np.mean((stair - truth[inside]) ** 2)))
    # beat-null (b): 標高一定(平均)の平坦近似
    flat_rmse = float(np.sqrt(np.mean((pz.mean() - truth[inside]) ** 2)))

    print(f"[GT] 全域RMSE: 当てはめ {fit_rmse:.2f}m / 最近傍等高線(階段) {stair_rmse:.2f}m / 平坦 {flat_rmse:.2f}m")
    assert fit_rmse < 0.03 * H, f"復元DEMが真の地形と合わない: RMSE {fit_rmse:.2f}m"
    assert fit_rmse < 0.3 * stair_rmse, "階段近似と差がつかない(内挿の価値が出ていない)"
    assert fit_rmse < 0.2 * flat_rmse, "平坦近似と差がつかない"

    print("\nPASS: 等高線(標高付き輪郭)から散布点を集め、サーフェス当てはめで地形の高さ場"
          "(DEM)を復元 — 線の間も含め全域RMSE %.2fm(階段近似 %.2fm・平坦 %.2fm を大きく下回る)。"
          "等高線→点→面→格子の表現変換が地形データで通った。" % (fit_rmse, stair_rmse, flat_rmse))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
