---
op: design_min_radius
dim: drive
category: lateral
in: any
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# design_min_radius — DRIVE `lateral` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.design_min_radius(design_speed_kmh, *, side_friction: 'float', superelevation: 'float') -> 'np.ndarray'` (実装を直接呼ぶなら `import drivelateral; drivelateral.design_min_radius(design_speed_kmh, *, side_friction: 'float', superelevation: 'float') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("design_min_radius")`)

## 使い方

道路構造令の解説 (3) 式の最小曲線半径 R = V² / (127 (i + f)) [m] (V は km/h)。

(2) 式から分母の i f を落とし(i f ≪ 1)、3.6² g ≈ 127 とした設計の式。厳密な上限速度は :func:`curve_speed_limit`。

**Raises** ``ValueError``: V ≤ 0、f < 0、i + f ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md) · [rear_axle_path](rear_axle_path.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
