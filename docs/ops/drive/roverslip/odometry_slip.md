---
op: odometry_slip
dim: drive
category: roverslip
in: any × signal × scalar
out: table
examples: [poc_rover_slip_risk_path]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# odometry_slip — DRIVE `roverslip` op

- **データ種**: `any × signal × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.odometry_slip(position, wheel_angle, radius: 'float', window: 'int' = 1) -> 'dict'` (実装を直接呼ぶなら `import roverslip; roverslip.odometry_slip(position, wheel_angle, radius: 'float', window: 'int' = 1) -> 'dict'`、台帳から引くなら `opsdrive.get("odometry_slip")`)

## 使い方

視覚オドメトリの位置の列と車輪の累積回転角から、実際の滑り率 ``s = 1 − Δx / (r Δφ)``。

``position`` は (T,) の進んだ距離か (T, 2) の平面の位置 [m]、``wheel_angle`` は (T,) の車輪の累積回転角 [rad]、
``radius`` = r [m]。``window`` 個ぶんの区間でまとめて割る(短い区間は雑音を拾う)。車輪がほとんど回らない
区間(``r Δφ`` が全体の中央値の 1 % 未満)は nan。返り値 ``{"slip": (T − window,), "slip_total": 全区間の 1 個,
"distance": 区間ごとの車体の移動 [m], "wheel_travel": 区間ごとの r Δφ [m]}``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_rover_slip_risk_path](../../../../examples/poc_rover_slip_risk_path.py) — `py -3.11 examples/poc_rover_slip_risk_path.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`roverslip`)

[bekker_pressure](bekker_pressure.md) · [bekker_wheel_sinkage](bekker_wheel_sinkage.md) · [wheel_forces](wheel_forces.md) · [wheel_sinkage](wheel_sinkage.md) · [wheel_traction_curve](wheel_traction_curve.md) · [slope_slip_curve](slope_slip_curve.md) · [ground_shift_track](ground_shift_track.md) · [slip_gp_fit](slip_gp_fit.md)

---
*Provenance: roverslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
