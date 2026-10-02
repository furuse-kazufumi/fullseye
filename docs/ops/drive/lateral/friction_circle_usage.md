---
op: friction_circle_usage
dim: drive
category: lateral
in: any
out: any
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# friction_circle_usage — DRIVE `lateral` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.friction_circle_usage(ax, ay, *, mu: 'float', g: 'float' = 9.81) -> 'np.ndarray'` (実装を直接呼ぶなら `import drivelateral; drivelateral.friction_circle_usage(ax, ay, *, mu: 'float', g: 'float' = 9.81) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("friction_circle_usage")`)

## 使い方

摩擦円の使用率 √(a_x² + a_y²) / (μ g)(1 を超えたら摩擦円の外 = タイヤが路面から受けられる力を超える)。

``ax``, ``ay``: 縦・横の加速度 [m/s²] (同じ形、または放送できる形)。``mu``: 路面とタイヤの摩擦係数(> 0)。
返り値: 使用率の配列(入力と同じ形)。

**Raises** ``ValueError``: 非有限、μ ≤ 0、g ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_lateral](../../../../examples/poc_driving_lateral.py) — `py -3.11 examples/poc_driving_lateral.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`lateral`)

[curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md) · [rear_axle_path](rear_axle_path.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
