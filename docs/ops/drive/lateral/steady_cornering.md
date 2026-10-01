---
op: steady_cornering
dim: drive
category: lateral
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# steady_cornering — DRIVE `lateral` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.steady_cornering(speed: 'float', radius: 'float', params: 'dict') -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivelateral; drivelateral.steady_cornering(speed: 'float', radius: 'float', params: 'dict') -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("steady_cornering")`)

## 使い方

線形 2 輪等価モデルの定常円旋回(速さ u、旋回半径 R = u/r、左旋回を正)。

R は前向きの速さ u とヨーレート r で定義する(線形モデルの慣習)。重心の軌跡の実際の半径は合成の速さ / r =
R √(1 + tan²β) で、β が小さい範囲で R に等しい(門で確かめた差は β² の桁)。

返り値: ``steer`` δ = L/R + K u²/R [rad]、``yaw_rate`` r = u/R、``lateral_accel`` u²/R、
``sideslip`` β = l_r/R − m l_f u²/(C_r L R)、``yaw_gain`` r/δ = (u/L)/(1 + K u²/L)、``front_slip``・``rear_slip``
(軸の横すべり角)、``K``。R < 0 で右旋回(符号がそのまま反転)。

**Raises** ``ValueError``: u ≤ 0、R = 0 / 非有限、母数の誤り、1 + K u²/L ≤ 0(臨界速度以上)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md) · [rear_axle_path](rear_axle_path.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
