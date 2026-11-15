# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""heightmap_depth_camera_tour — 高さ図を深度カメラで直接撮り、知覚の連鎖を合成データで閉じる(新規 op)。

    py -3.11 examples/heightmap_depth_camera_tour.py

【この例が示すこと】
1. **閉形式** —— 平らな床と傾いた面を撮った深度が、光線と平面の交点の閉形式に 1e-12 で一致する。
2. **別の算法と一致** —— 同じ高さ図を三角形に分けて ``world_camera``(render3d のラスタ化)で撮ると、
   平面では 1e-9、曲面でも画素の中央値 1e-4 m 以内。当たる画素の集合も同じ。
3. **知覚の連鎖を閉じる**(製作の G1 いろは坂と同じ連鎖、op だけで) ——
   ``road_surface_heightmap``(ヘアピンの道、真値つき)→ ``heightmap_depth_camera``(頭の高さ 1.2 m、D435 級の雑音)
   → ``camera.depth_to_points`` → 世界へ → ``elevation_map``(平均)→ 車線の窓を ``crop_rectangle2`` →
   ``surface_form_remove`` で縦断勾配・横勾配を読み、作り方の真値と突き合わせる。
4. **雑音の則** —— σ_z = z²·σ_d/(f·b)(``acceptance_scan`` の triangulation と同じ形)。平面を 40 回撮った
   標準偏差が則と一致する。
5. **隠れ** —— 高い壁の向こうには当たらず、当たったセルは ``dem_viewshed``(独立した op)が見えると言う所だけ。

【グラウンドトゥルース】平面の閉形式、作った道の解析の真値、雑音の則の定数。
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
import camera as CAM           # noqa: E402
import demops                  # noqa: E402
import drivelateral as DL      # noqa: E402
import driveworld as DW        # noqa: E402
import image_gen               # noqa: E402
import roughness               # noqa: E402
import terrain as TR           # noqa: E402

LG = fs.ledger                 # 台帳(opsdrive の walkterrain)から名前で呼ぶ


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


def main() -> int:
    checks = []
    K = np.array([[120.0, 0.0, 63.5], [0.0, 120.0, 47.5], [0.0, 0.0, 1.0]])
    cell, ny, nx = 0.05, 160, 200
    X, Y = np.meshgrid((np.arange(nx) + 0.5) * cell, (np.arange(ny) + 0.5) * cell)
    R, t = look([1.0, 4.0, 1.8], [5.0, 4.0, 0.0])
    Cw = -R.T @ t

    # ---- 1. 平面の閉形式 ---------------------------------------------------------------- #
    a, b, c0 = 0.08, -0.03, 0.2
    Hp = c0 + a * X + b * Y
    d = LG.heightmap_depth_camera(Hp, (R, t), K, cell)
    v, u = np.mgrid[0:96, 0:128].astype(float)
    dw = np.stack([(u - 63.5) / 120.0, (v - 47.5) / 120.0, np.ones_like(u)], -1) @ R
    z = (c0 + a * Cw[0] + b * Cw[1] - Cw[2]) / (dw[..., 2] - a * dw[..., 0] - b * dw[..., 1])
    fin = np.isfinite(d)
    err = float(np.abs(d - z)[fin].max())
    print("1. 傾いた面: 閉形式との差の最大 %.1e m(当たった画素 %d / %d)" % (err, int(fin.sum()), d.size))
    checks.append(err < 1e-12)

    # ---- 2. world_camera(ラスタ化)と一致 --------------------------------------------- #
    Hh = 0.6 * np.exp(-((X - 5) ** 2 + (Y - 4) ** 2) / (2 * 0.8 ** 2)) + 0.05 * X
    idx = np.arange(ny * nx).reshape(ny, nx)
    q = [idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel()]
    F = np.r_[np.stack([q[0], q[1], q[3]], 1), np.stack([q[0], q[3], q[2]], 1)]
    world = {"V": np.stack([X.ravel(), Y.ravel(), Hh.ravel()], 1), "F": F,
             "face_color": np.full((len(F), 3), 0.5), "face_label": np.zeros(len(F), np.int64)}
    S = np.diag([1.0, -1.0, -1.0])
    pose = np.eye(4)
    pose[:3, :3], pose[:3, 3] = S @ R, S @ t
    wc = DW.world_camera(world, pose, K, 128, 96)
    dh = LG.heightmap_depth_camera(Hh, (R, t), K, cell)
    hit = wc["face"] >= 0
    diff = np.abs(dh - wc["depth"])[hit]
    print("2. 丘を world_camera と比べる: 当たる画素の集合が同じ %s、差の中央値 %.1e m・最大 %.1e m(双一次と三角形の違い)"
          % (bool(np.array_equal(np.isfinite(dh), hit)), float(np.median(diff)), float(diff.max())))
    checks.append(np.array_equal(np.isfinite(dh), hit) and np.median(diff) < 1e-4)

    # ---- 3. 知覚の連鎖(道 → 深度 → 点群 → 標高図 → 勾配) ------------------------------- #
    Rr, g = 35.0, 0.06
    L = math.pi * Rr
    ss = np.arange(0.0, L + 1e-9, 1.0)
    cp = DL.clothoid_points(L, ss, kappa0=1.0 / Rr, kappa1=1.0 / Rr)
    arc = {"x": cp["points"][:, 0], "y": cp["points"][:, 1], "z": g * ss, "s": ss,
           "heading": cp["heading"], "curvature": cp["curvature"]}
    ext = (-6.0, 42.0, -6.0, 76.0)
    Hr = DL.road_surface_heightmap(arc, cell, extent=ext)
    s_cam, e_cam = 40.0, 1.5                                             # 左の車線の中央に立つ
    th = s_cam / Rr
    px, py = (Rr - e_cam) * math.sin(th), Rr - (Rr - e_cam) * math.cos(th)
    zg = g * s_cam - 0.02 * e_cam
    look_ahead = 1.0                                                      # 1 m 先の路面を見る(足元 0.4 m から写る)
    ahead = th + look_ahead / (Rr - e_cam)
    tx, ty = (Rr - e_cam) * math.sin(ahead), Rr - (Rr - e_cam) * math.cos(ahead)
    Rc, tc = look([px, py, zg + 1.2], [tx, ty, g * Rr * ahead - 0.02 * e_cam])
    Kd = np.array([[90.0, 0.0, 59.5], [0.0, 90.0, 37.0], [0.0, 0.0, 1.0]])      # 120 × 75
    depth = LG.heightmap_depth_camera(Hr, (Rc, tc), Kd, cell, origin=(ext[0], ext[2]), max_range=3.0,
                                      disparity_sigma=0.01, baseline=0.05, seed=1)   # 1.5 m で 5 mm
    pts = (CAM.depth_to_points(depth, Kd) - tc) @ Rc
    emap, _ = LG.elevation_map(pts, cell=cell, agg="mean", bounds=ext)
    # 車線の窓(0.5〜1.5 m 先、幅 ±0.5 m。カメラに写っている範囲)を、その場の向きで切り出す
    thw = th + 1.0 / (Rr - e_cam)
    xw, yw = (Rr - e_cam) * math.sin(thw), Rr - (Rr - e_cam) * math.cos(thw)
    col, row = (xw - ext[0]) / cell - 0.5, (yw - ext[2]) / cell - 0.5
    filled = LG.fill_gaps(emap)
    seen = float(np.isfinite(image_gen.crop_rectangle2(np.where(np.isfinite(emap), 1.0, 0.0), row, col, thw,
                                                        10.0, 10.0)).mean())
    win = image_gen.crop_rectangle2(filled, row, col, thw, 10.0, 10.0)
    _res, coef = roughness.surface_form_remove(win, cell, order=1)
    tr_grade = g * Rr / (Rr - e_cam)
    print("3. 道 → 深度(120×75、雑音あり)→ 点群 %d 点 → 標高図 → 車線の窓(観測したセル %.0f %%): "
          "縦断 %.4f(真値 %.4f)、横 %.4f(真値 %.4f)" % (len(pts), 100 * seen, coef[1], tr_grade, coef[2], -0.02))
    checks.append(seen > 0.99 and abs(coef[1] - tr_grade) < 0.005 and abs(coef[2] + 0.02) < 0.005)

    # ---- 4. 雑音の則 ---------------------------------------------------------------------- #
    dn = LG.heightmap_depth_camera(Hp, (R, t), K, cell, max_range=6.0)
    fin = np.isfinite(dn)
    shots = np.array([LG.heightmap_depth_camera(Hp, (R, t), K, cell, disparity_sigma=0.1, baseline=0.05, seed=k,
                                                max_range=6.0) for k in range(40)])
    std = shots[:, fin].std(0)
    pred = dn[fin] ** 2 * 0.1 / (K[0, 0] * 0.05)
    ratio = float(np.median(std / pred))
    print("4. 雑音: 40 回撮った標準偏差 / 則 σ_z = z²σ_d/(f b) の中央値 %.3f" % ratio)
    checks.append(abs(ratio - 1.0) < 0.06)

    # ---- 5. 隠れ ------------------------------------------------------------------------ #
    Hw = np.zeros((ny, nx))
    Hw[:, 120] = 3.0
    dwall = LG.heightmap_depth_camera(Hw, (R, t), K, cell)
    pw = (CAM.depth_to_points(dwall, K) - t) @ R
    hitc = np.isfinite(LG.elevation_map(pw, cell=cell, agg="mean", bounds=(0.0, nx * cell, 0.0, ny * cell))[0])
    vis = np.asarray(demops.dem_viewshed(Hw, cell, (int(Cw[1] / cell), int(Cw[0] / cell)),
                                         observer_height_m=float(Cw[2]))) > 0.5
    print("5. 壁: 当たったセル %d、そのうち dem_viewshed が見えないと言うセル %d、壁の向こうに当たったセル %d"
          % (int(hitc.sum()), int((hitc & ~vis).sum()), int(hitc[:, 121:].sum())))
    checks.append(not (hitc & ~vis).any() and not hitc[:, 121:].any())

    figs.save_grid("depth_views", [dh, wc["depth"], np.where(hit, dh - wc["depth"], np.nan)],
                   ["heightmap_depth_camera", "world_camera(三角形)", "差 [m]"],
                   title="丘を 2 つの算法で撮る", signed=[False, False, True])
    # 見えた所だけを切り出す(格子の行 0 = 南なので上下を返して北を上に)。穴は nan のまま(埋めた後ではなく観測そのもの)
    ii, jj = np.nonzero(np.isfinite(emap))
    sl = (slice(max(ii.min() - 4, 0), ii.max() + 5), slice(max(jj.min() - 4, 0), jj.max() + 5))
    lo_hi = (float(np.nanmin(Hr[sl])), float(np.nanmax(Hr[sl])))
    figs.save_grid("road_chain", [depth, emap[sl][::-1], Hr[sl][::-1]],
                   ["頭の深度カメラ 120×75(雑音つき)[m]", "点群から作った標高図(見えた所、nan = 写っていない)",
                    "作った道の高さ(真値、同じ範囲)"],
                   title="道 → 深度 → 点群 → 標高図(ヘアピンの左の車線に立つ)", ncols=3,
                   vrange=[None, lo_hi, lo_hi], colorbar=True)

    ok_all = all(bool(c) for c in checks)
    print("PASS" if ok_all else "FAIL", "(%d / %d)" % (sum(bool(c) for c in checks), len(checks)))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
