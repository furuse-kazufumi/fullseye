---
op: cr_drive
dim: drive
category: commonroad
in: table
out: table
examples: [poc_driving_commonroad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# cr_drive — DRIVE `commonroad` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cr_drive(scene, pp_index: 'int' = 0, *, route=None, v_cruise=None, a_max: 'float' = 1.5, b_max: 'float' = 3.0, lookahead: 'float' = 5.0, dt=None, stop_lines=None, hold_s: 'float' = 2.0, goal_inset: 'float' = 0.2, idm_T: 'float' = 1.2, stop_margin: 'float' = 0.6, a_lat: 'float' = 2.5, k_v: 'float' = 0.6, follow_width: 'float' = 2.0, follow_obstacles: 'bool' = True, curvature_window: 'float' = 10.0, horizon=None, params=None) -> 'dict'` (実装を直接呼ぶなら `import drivecommonroad; drivecommonroad.cr_drive(scene, pp_index: 'int' = 0, *, route=None, v_cruise=None, a_max: 'float' = 1.5, b_max: 'float' = 3.0, lookahead: 'float' = 5.0, dt=None, stop_lines=None, hold_s: 'float' = 2.0, goal_inset: 'float' = 0.2, idm_T: 'float' = 1.2, stop_margin: 'float' = 0.6, a_lat: 'float' = 2.5, k_v: 'float' = 0.6, follow_width: 'float' = 2.0, follow_obstacles: 'bool' = True, curvature_window: 'float' = 10.0, horizon=None, params=None) -> 'dict'`、台帳から引くなら `opsdrive.get("cr_drive")`)

## 使い方

自分の運転手(縦 IDM + pure pursuit)を CommonRoad の planning problem で走らせる。

縦: IDM(a_max, b_max, idm_T, s₀ = stop_margin)で、目標 = 経路終点(ゴール lanelet の ``goal_inset`` 地点、止まった先行車と
見なす)・``stop_lines``(経路の弧長の列、または ``"scene"`` で lanelet の stopLine を経路に射影。止まったら ``hold_s`` 秒で発進)・
経路上の先行障害物(``follow_obstacles``、中心が経路から ``follow_width`` 以内で前にある物)。希望速度 v₀ = min(v_cruise, 経路の
制限, 曲率の許容 √(a_lat/|κ|)、κ は ``curvature_window`` m の移動平均)。横: 見通し L_d = max(lookahead, k_v·v) の pure pursuit、
δ̇ ∈ ±0.4。各 step は :func:`ks_step`(RK4)。``horizon`` = step 数(既定 = ゴール time_step 区間の上端 − 初期 time_step)。

返り値 ``{"kind": "commonroad_run", "t", "time_step", "x", "y" (車両中心), "x_rear", "y_rear", "delta", "v", "psi",
"u" (T−1, 2), "s" (中心の弧長), "s_front", "lat_err", "v_allow", "stops": [(time_step, s_front, kind, target_s)], "events",
"route", "goal_reached", "goal_index", "params", "dt", "pp_id", "initial_time_step", "v_limit"}``。

門: |a| ≤ max(a_max, b_max)、0 ≤ v ≤ v_limit、停止線の前端が 0〜1 m 手前で止まる、cr_feasible が feasible、ゴール到達。

**Raises** ``ValueError``: scene / route が不正、pp_index 範囲外、速度の上限が決まらない(制限も v_cruise も無い)、
初期位置がどの lanelet にも無い、stop_lines が経路の外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_commonroad](../../../../examples/poc_driving_commonroad.py) — `py -3.11 examples/poc_driving_commonroad.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`commonroad`)

[cr_synthetic](cr_synthetic.md) · [cr_read](cr_read.md) · [cr_route](cr_route.md) · [ks_step](ks_step.md) · [cr_drive_sweep](cr_drive_sweep.md) · [cr_feasible](cr_feasible.md) · [cr_collision](cr_collision.md) · [cr_solution_xml](cr_solution_xml.md)

---
*Provenance: drivecommonroad.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
