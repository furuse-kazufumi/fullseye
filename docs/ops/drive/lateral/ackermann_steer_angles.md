---
op: ackermann_steer_angles
dim: drive
category: lateral
in: any
out: table
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# ackermann_steer_angles — DRIVE `lateral` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ackermann_steer_angles(radius, wheelbase: 'float', track: 'float') -> 'Dict[str, np.ndarray]'` (実装を直接呼ぶなら `import drivelateral; drivelateral.ackermann_steer_angles(radius, wheelbase: 'float', track: 'float') -> 'Dict[str, np.ndarray]'`、台帳から引くなら `opsdrive.get("ackermann_steer_angles")`)

## 使い方

アッカーマンの内外輪の舵角(後車軸の中心の旋回半径 R、ホイールベース L、輪距 t)。

δ_in = atan(L/(R − t/2))、δ_out = atan(L/(R + t/2))、2 輪等価 δ = atan(L/R)。cot δ_out − cot δ_in = t/L。
返り値: ``inner``, ``outer``, ``bicycle`` [rad]、``front_inner_radius`` √((R − t/2)² + L²)、``front_outer_radius``、
``rear_inner_radius`` R − t/2、``offtracking``(定常の内輪差 = 前内輪 − 後内輪の半径)。

**Raises** ``ValueError``: R ≤ t/2(内側の後輪が旋回の中心を越える)、L ≤ 0、t < 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_lateral](../../../../examples/poc_driving_lateral.py) — `py -3.11 examples/poc_driving_lateral.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [offtracking_circle](offtracking_circle.md) · [rear_axle_path](rear_axle_path.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
