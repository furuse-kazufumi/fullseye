---
op: occlusion_safe_speed
dim: drive
category: traffic
in: any
out: any
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# occlusion_safe_speed — DRIVE `traffic` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.occlusion_safe_speed(d, *, reaction: 'float', brake: 'float')` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.occlusion_safe_speed(d, *, reaction: 'float', brake: 'float')`、台帳から引くなら `opsdrive.get("occlusion_safe_speed")`)

## 使い方

見えた瞬間から距離 d 以内に止まれる最大速度 v = b(−ρ + sqrt(ρ² + 2d/b))。

v ρ + v²/(2b) = d(空走 + 制動。``rsssafety.rss_stopping_distance(v, ρ, accel=0, brake=b)`` と同じ式)を v について
解いた正の根。桁落ちを避けて v = 2d / (ρ + sqrt(ρ² + 2d/b)) で計算する(ρ = 0 で sqrt(2 b d))。
d は配列でもよい。d ≤ 0 なら 0(見えた時には既に間に合わない)。

門: ``rss_stopping_distance(v, ρ, 0, b)`` == d(第 2 実装、rtol 1e-12)。

**Raises** ``ValueError``: reaction < 0、brake ≤ 0、d が非有限(inf は許して inf を返す)。

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
