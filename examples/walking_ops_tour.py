# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""walking_ops_tour — 点群から足場を選び、歩いた記録を足で検算する(台帳 walkterrain + locomotion の 24 op)。

    py -3.11 examples/walking_ops_tour.py

【この例が示すこと】
1. **足場** —— 段と穴のある床の点群(真値つきの合成)を ``elevation_map`` で高さ図にし、``fill_gaps`` /
   ``ground_plane`` / ``detect_obstacles`` / ``elevation_step_edges`` / ``elevation_traversability`` / ``foothold_score`` /
   ``roughness_map`` / ``elevation_normals`` / ``foothold_candidates`` / ``fuse_elevation`` / ``ground_surface``
   で「足を置ける所」の mask にする。箱の高さと段の位置は作ったときの値と一致する。
2. **足場の列** —— ``footstep_plan`` が mask の上で左右交互の着地点を決める(穴の上には置かない)。
3. **歩いた記録の検算** —— その着地点を踏む足の軌跡(遊脚は正弦の弧)を作り、``gait_step_events`` が
   着地点を 0 の誤差で取り戻し、``gait_phase`` / ``foot_slip_metrics`` が滑り 0・足で測る前進 = 胴の前進と読む。
   同じ胴の動きで足を置き直さない「見せかけ」は ``walking_ok = False``。
4. **釣り合い** —— 2 足支持の各コマで ``support_line_margin``(``com_support_margin`` は線分で ``-inf``)、
   LIPM の ``lipm_capture_point`` / ``capture_margin``、``static_contact_force_lp`` の力(左右対称なら等分)。
   シルエットの重心 ``com_from_silhouette``、接地点 ``contact_points``、``support_polygon`` も同じ記録から。

【グラウンドトゥルース】作った床(箱の高さ・段の列)、計画した着地点、作った COM の軌跡。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import fullseye as fs          # noqa: E402

LG = fs.ledger                 # 台帳(opsdrive の族 walkterrain / locomotion)から名前で呼ぶ
CELL = 0.05


def floor_cloud():
    """3.0 m × 1.0 m の床: x = 1.2 m から 0.06 m の段、x ∈ [2.0, 2.3] に高さ 0.25 m の箱、x ∈ [0.6, 0.75] は穴。"""
    H, W = 20, 60
    yy, xx = np.mgrid[0:H, 0:W]
    x = (xx + 0.5) * CELL
    y = (yy + 0.5) * CELL
    z = np.where(x >= 1.2, 0.06, 0.0)
    box = (x >= 2.0) & (x < 2.3) & (y >= 0.35) & (y < 0.65)
    z = z + np.where(box, 0.25, 0.0)
    keep = ~((x >= 0.6) & (x < 0.75))                     # 穴: 点が落ちない = 観測していない
    pts = np.stack([x[keep], y[keep], z[keep]], 1)
    return pts, box


def main() -> int:
    checks = []
    pts, box = floor_cloud()
    grid = LG.elevation_map(pts, cell=CELL, bounds=(0.0, 3.0, 0.0, 1.0))[0]
    n_hole = int(np.isnan(grid).sum())
    filled = LG.fill_gaps(grid)
    fused = LG.fuse_elevation([grid, grid])
    print("1. 高さ図 %s、観測していないセル %d(穴 3 列 × 20 行)、fill_gaps 後 %d"
          % (grid.shape, n_hole, int(np.isnan(filled).sum())))
    checks.append(n_hole == 60 and not np.isnan(filled).any() and np.array_equal(np.isnan(fused), np.isnan(grid)))

    mask_obs, obs = LG.detect_obstacles(grid, cell=CELL, clearance=0.12, extent=(0.0, 3.0, 0.0, 1.0))
    edges, rise = LG.elevation_step_edges(grid, min_rise=0.04)
    print("   障害物 %d 個: 平面からの高さ %.3f m(作った箱 0.25 m。頑健な平面が段 0.06 m を傾きとして吸うので"
          "箱の所の地面が低めに出る)、面積 %.3f m²(作った値 %.3f)"
          % (len(obs), obs[0]["height"], obs[0]["area"], box.sum() * CELL ** 2))
    checks.append(len(obs) == 1 and abs(obs[0]["area"] - box.sum() * CELL ** 2) < 1e-12)
    step_cols = sorted(set(np.nonzero(edges[:3].any(0))[0].tolist()))
    print("   段差の列(上の 3 行): %s(段は列 24 = x 1.2 m)" % step_cols)
    checks.append(23 in step_cols and 24 in step_cols)

    ok = LG.elevation_traversability(grid, cell=CELL, max_step=0.1, max_slope=0.6)
    score = LG.foothold_score(grid, cell=CELL)
    rough = LG.roughness_map(grid)
    normals = LG.elevation_normals(grid, cell=CELL)
    envelope = LG.ground_surface(grid, cell=CELL, radius=0.2)
    plane = LG.ground_plane(grid)
    cands = LG.foothold_candidates(grid, cell=CELL, min_score=0.9, extent=(0.0, 3.0, 0.0, 1.0))
    # 箱の上面は平らなので局所の門(段・傾き・粗さ)だけでは「置ける」になる(16 セル)。障害物の mask で外す。
    foothold = ok & (score > 0.9) & (rough < 0.01) & ~mask_obs
    print("   足を置ける所 %d / %d セル(箱・段の縁・穴を除く)、候補 %d 点、平らな所の法線 %s、"
          "地面の包絡の最大 %.3f m、平面の傾き %.3f m"
          % (foothold.sum(), foothold.size, len(cands), np.round(normals[5, 5], 6).tolist(),
             float(envelope.max()), float(np.ptp(plane))))
    checks.append(not foothold[box].any() and not foothold[:, 12:15].any() and len(cands) > 0)

    # ---- 2. 足場の列 ------------------------------------------------------------------- #
    # 歩隔は 0.1〜0.3 m、歩幅は 0.25 m まで。左足 = y が大きい側(行 13)、右足 = 行 6 から。
    plan = LG.footstep_plan(foothold, CELL, ((13, 1), (6, 1)), 36, 0.25, 0.1, 0.4,
                            extent=(0.0, 3.0, 0.0, 1.0))
    steps = plan["steps"]
    print("2. 足場の列: %d 歩、費用 %.3f、左右 %s、穴の上に置いた足 %d"
          % (plan["n_steps"], plan["cost"], "".join(s["side"] for s in steps),
             sum(12 <= s["cell"][1] < 15 for s in steps)))
    checks.append(plan["reached"] and all(foothold[s["cell"]] for s in steps)
                  and all(a["side"] != b["side"] for a, b in zip(steps, steps[1:])))

    # ---- 3. 歩いた記録を作って、足で検算する ------------------------------------------- #
    dt, swing, stance = 0.01, 24, 16
    T = 20 + len(steps) * (swing // 2 + stance) + swing + 40
    feet = np.zeros((T, 2, 3))
    pos = {"L": np.array([(1 + 0.5) * CELL, (13 + 0.5) * CELL, 0.0]),
           "R": np.array([(1 + 0.5) * CELL, (6 + 0.5) * CELL, 0.0])}
    side_idx = {"L": 0, "R": 1}
    feet[:, 0], feet[:, 1] = pos["L"], pos["R"]
    t0, truth = 20, []
    for s in steps:
        f = side_idx[s["side"]]
        a, b = pos[s["side"]].copy(), np.array([*s["xy"], grid[s["cell"]]])
        for i in range(swing):
            u = (i + 1) / (swing + 1)
            feet[t0 + i, f] = a + (b - a) * u + np.array([0.0, 0.0, 0.12 * math.sin(math.pi * u)])
        feet[t0 + swing:, f] = b
        pos[s["side"]] = b
        truth.append((t0 + swing, b[:2]))
        t0 += swing // 2 + stance
    ground_z = np.where(feet[..., 0] >= 1.2, 0.06, 0.0)
    rel = feet.copy()
    rel[..., 2] -= ground_z                                   # 足の下の床からの高さ
    ev = LG.gait_step_events(rel, dt, 0.01, 0.03)
    err = max(float(np.linalg.norm(e["xy"] - tx)) for e, (_, tx) in zip(ev["steps"], truth))
    print("3. 取り出した一歩 %d(計画 %d)、着地点の誤差の最大 %.2e m、交互 %s"
          % (len(ev["steps"]), len(steps), err, ev["alternating"]))
    checks.append(len(ev["steps"]) == len(steps) and err < 1e-12 and ev["alternating"])

    phase = LG.gait_phase(rel[..., 2], ground=0.0, contact_tol=0.005)
    body = np.c_[feet[:, :, :2].mean(1), np.full(T, 0.85)]
    slip = LG.foot_slip_metrics(feet, phase["stance"], body)
    fake = LG.foot_slip_metrics(np.repeat(feet[:1], T, 0), np.ones((T, 2), bool), body)
    print("   滑り %.2e m、足で測る前進 %.3f m / 胴 %.3f m、walking_ok %s;足を置き直さない見せかけ %s"
          % (slip["max_slip_observed"], slip["foot_advance"], slip["body_advance"], slip["walking_ok"],
             fake["walking_ok"]))
    checks.append(slip["walking_ok"] and slip["max_slip_observed"] < 1e-12 and not fake["walking_ok"])

    # ---- 4. 釣り合い ------------------------------------------------------------------- #
    k = truth[3][0] + 2                                       # 2 足支持のコマ
    two = feet[k]
    com = np.r_[two[:, :2].mean(0) + [0.02, 0.0], 0.85]
    lm = LG.support_line_margin(com, two)
    cm = LG.com_support_margin(com, two)
    xi = LG.lipm_capture_point(com[None], np.array([[0.3, 0.0, 0.0]]), 0.85)[0]
    capm = LG.capture_margin(com, [0.3, 0.0, 0.0], 0.85, two)
    print("4. 2 足支持: 線分までの余裕 %.4f m(com_support_margin は %s)、捕捉点 x = %.4f(COM x %.4f)、"
          "捕捉の余裕 %.4f m" % (lm, cm, xi[0], com[0], capm))
    w = math.sqrt(9.81 / 0.85)
    checks.append(cm == -math.inf and lm <= 0.0 and abs(xi[0] - com[0] - 0.3 / w) < 1e-12 and capm < 0.0)

    sym = np.array([[1.0, 0.6, 0.0], [1.0, 0.4, 0.0]])
    lp = LG.static_contact_force_lp(sym, np.tile([0.0, 0.0, 1.0], (2, 1)), [1.0, 0.5, 0.85], 40.0, 0.8)
    print("   左右対称の 2 足の法線力 %s N(体重 %.2f N の半分ずつ)" % (np.round(lp["normal"], 6).tolist(), 40 * 9.81))
    checks.append(lp["feasible"] and np.allclose(lp["normal"], 40 * 9.81 / 2, rtol=1e-9))

    cloud = np.r_[pts, two + [0.0, 0.0, 0.0]]
    contacts = LG.contact_points(cloud, [0.0, 0.0, 1.0, 0.0], tol=0.01)[0]
    poly = LG.support_polygon(np.r_[feet[k], [[feet[k, 0, 0] + 0.2, feet[k, 0, 1], 0.0]]], ground=0.0)
    sil = np.zeros((40, 20), bool)
    sil[5:35, 8:12] = True
    rc = LG.com_from_silhouette(sil)
    print("   接地点 %d 点、支持多角形の面積 %.4f m²、シルエットの重心 %s"
          % (len(contacts), poly["area"], rc))
    checks.append(len(contacts) > 0 and poly["area"] > 0 and rc == (19.5, 9.5))

    ok_all = all(bool(c) for c in checks)
    print("PASS" if ok_all else "FAIL", "(%d / %d)" % (sum(bool(c) for c in checks), len(checks)))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
