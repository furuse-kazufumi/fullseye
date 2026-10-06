---
op: curve_speed_limit
dim: drive
category: lateral
in: any
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# curve_speed_limit — DRIVE `lateral` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.curve_speed_limit(radius, *, side_friction: 'float', superelevation: 'float' = 0.0, g: 'float' = 9.81)` (実装を直接呼ぶなら `import drivelateral; drivelateral.curve_speed_limit(radius, *, side_friction: 'float', superelevation: 'float' = 0.0, g: 'float' = 9.81)`、台帳から引くなら `opsdrive.get("curve_speed_limit")`)

## 使い方

片勾配 i・横すべり摩擦係数 f の曲線(半径 R)で外へ滑らない上限速度 v = √(g R (i + f)/(1 − i f)) [m/s]。

道路構造令の解説 (2) 式 Z cos α − G sin α ≤ f (Z sin α + G cos α)(Z = G v²/(gR)、i = tan α)を v について解いた
厳密な形。i f ≥ 1 なら(どの速さでも外へは滑らない)``inf``。``radius`` は配列でもよい(> 0)。

**Raises** ``ValueError``: R ≤ 0、f < 0、|i| ≥ 1、i + f ≤ 0(止まっていても内へ滑る)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md) · [rear_axle_path](rear_axle_path.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
