---
op: understeer_gradient
dim: drive
category: lateral
in: 
out: table
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# understeer_gradient — DRIVE `lateral` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.understeer_gradient(params: 'dict') -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivelateral; drivelateral.understeer_gradient(params: 'dict') -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("understeer_gradient")`)

## 使い方

アンダーステア勾配 K = (m/L)(l_r/C_f − l_f/C_r) [rad/(m/s²)] と、特性速度 / 臨界速度。

``params``: ``mass`` [kg]、``l_f``・``l_r``(重心から前・後車軸)[m]、``c_f``・``c_r``(軸ごとのコーナリングパワー)[N/rad]。
返り値: ``K``、``kind``("understeer" / "neutral" / "oversteer")、``characteristic_speed``(K > 0 で √(L/K)、
ヨーレートゲインが最大の速さ)、``critical_speed``(K < 0 で √(−L/K)、これを超えると不安定)。無いものは ``inf``。

**Raises** ``ValueError``: 欠けた / 正でない母数。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_lateral](../../../../examples/poc_driving_lateral.py) — `py -3.11 examples/poc_driving_lateral.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md) · [rear_axle_path](rear_axle_path.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
