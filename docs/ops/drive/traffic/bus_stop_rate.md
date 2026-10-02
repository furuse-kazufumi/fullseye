---
op: bus_stop_rate
dim: drive
category: traffic
in: any
out: any
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# bus_stop_rate — DRIVE `traffic` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.bus_stop_rate(x, *, bus_rear: 'float', bus_front: 'float', base: 'float', peak: 'float', spread: 'float')` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.bus_stop_rate(x, *, bus_rear: 'float', bus_front: 'float', base: 'float', peak: 'float', spread: 'float')`、台帳から引くなら `opsdrive.get("bus_stop_rate")`)

## 使い方

停車中のバスの前後で高い出現率 λ(x) = base + peak [exp(−½((x − rear)/spread)²) + exp(−½((x − front)/spread)²)]
[件/m]。バスの陰(前端の先)と後ろから人が出てくる、という形の例(値は呼び出し側の仮定)。上限は base + 2·peak。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`traffic`)

[idm_accel](idm_accel.md) · [idm_equilibrium_gap](idm_equilibrium_gap.md) · [idm_platoon_simulate](idm_platoon_simulate.md) · [driver_style](driver_style.md) · [lateral_wobble](lateral_wobble.md) · [ou_estimate](ou_estimate.md) · [social_force_step](social_force_step.md) · [pedestrian_crossing](pedestrian_crossing.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
