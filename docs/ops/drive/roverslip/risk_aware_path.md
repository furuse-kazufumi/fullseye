---
op: risk_aware_path
dim: drive
category: roverslip
in: table × any × any
out: table
examples: [poc_rover_slip_risk_path]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# risk_aware_path — DRIVE `roverslip` op

- **データ種**: `table × any × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.risk_aware_path(cost_map, start, goal) -> 'dict'` (実装を直接呼ぶなら `import roverslip; roverslip.risk_aware_path(cost_map, start, goal) -> 'dict'`、台帳から引くなら `opsdrive.get("risk_aware_path")`)

## 使い方

:func:`cvar_cost_map` の辺の所要時間の上で、8 近傍の Dijkstra(向きのある辺 —— 登りと下りで違う)。

``start``・``goal`` は (行, 列)。返り値 ``{"path": (n, 2) の添字, "cost": 合計の所要時間 [s] (届かなければ inf),
"reached": bool, "cost_to_come": (H, W)}``。届かないときは ``path`` が空。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_rover_slip_risk_path](../../../../examples/poc_rover_slip_risk_path.py) — `py -3.11 examples/poc_rover_slip_risk_path.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`roverslip`)

[bekker_pressure](bekker_pressure.md) · [bekker_wheel_sinkage](bekker_wheel_sinkage.md) · [wheel_forces](wheel_forces.md) · [wheel_sinkage](wheel_sinkage.md) · [wheel_traction_curve](wheel_traction_curve.md) · [slope_slip_curve](slope_slip_curve.md) · [ground_shift_track](ground_shift_track.md) · [odometry_slip](odometry_slip.md)

---
*Provenance: roverslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
