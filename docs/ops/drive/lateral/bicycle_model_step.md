---
op: bicycle_model_step
dim: drive
category: lateral
in: any
out: any
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# bicycle_model_step — DRIVE `lateral` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.bicycle_model_step(state, steer, speed, params: 'dict', dt: 'float') -> 'np.ndarray'` (実装を直接呼ぶなら `import drivelateral; drivelateral.bicycle_model_step(state, steer, speed, params: 'dict', dt: 'float') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("bicycle_model_step")`)

## 使い方

線形 2 輪等価モデルの 1 刻み(古典的な 4 次 Runge–Kutta、刻みの間 δ と u は一定)。

``state``: (..., 5) = (x, y, ψ, v_y, r)(重心の位置 [m]、向き [rad]、車の座標の横速度 [m/s]、ヨーレート [rad/s])。
``steer``: 前輪の舵角 δ [rad] (state の先頭の形に放送)。``speed``: 前向きの速さ u [m/s] (> 0、放送)。
``params`` には ``inertia``(I_z [kg m²])も要る。返り値: 次の状態(同じ形)。

横力は線形(飽和しない)。u → 0 で式が特異になるので u ≥ 0.5 m/s を要求する(低速は運動学で扱う)。

**Raises** ``ValueError``: 形の誤り、非有限、u < 0.5、dt ≤ 0、I_z が無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_lateral](../../../../examples/poc_driving_lateral.py) — `py -3.11 examples/poc_driving_lateral.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md) · [rear_axle_path](rear_axle_path.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
