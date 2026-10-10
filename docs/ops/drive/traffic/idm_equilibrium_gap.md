---
op: idm_equilibrium_gap
dim: drive
category: traffic
in: any
out: any
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# idm_equilibrium_gap — DRIVE `traffic` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.idm_equilibrium_gap(v, *, v0: 'float', T: 'float', s0: 'float', delta: 'float' = 4.0)` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.idm_equilibrium_gap(v, *, v0: 'float', T: 'float', s0: 'float', delta: 'float' = 4.0)`、台帳から引くなら `opsdrive.get("idm_equilibrium_gap")`)

## 使い方

IDM の平衡車間 s_e(v) = (s0 + v T) / sqrt(1 − (v/v0)^δ)(0 ≤ v < v0)。

Δv = 0 で ``idm_accel`` = 0 と置いて解いたもの(s* = s0 + vT)。v → v0 で発散する(希望速度では車間は要らない
= 前が無限に遠い)。a, b に依らない。

門: 先行車が一定速度のとき ``idm_platoon_simulate`` が収束した車間と rtol 1e-6 で一致。

**Raises** ``ValueError``: v < 0 または v ≥ v0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`traffic`)

[idm_accel](idm_accel.md) · [idm_platoon_simulate](idm_platoon_simulate.md) · [driver_style](driver_style.md) · [lateral_wobble](lateral_wobble.md) · [ou_estimate](ou_estimate.md) · [social_force_step](social_force_step.md) · [pedestrian_crossing](pedestrian_crossing.md) · [occlusion_reveal_distance](occlusion_reveal_distance.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
