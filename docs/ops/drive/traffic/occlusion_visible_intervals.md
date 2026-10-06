---
op: occlusion_visible_intervals
dim: drive
category: traffic
in: any
out: any
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# occlusion_visible_intervals — DRIVE `traffic` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.occlusion_visible_intervals(ego_xy, ego_heading: 'float', parked_box, emerge_xy, s_max: 'float') -> 'list'` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.occlusion_visible_intervals(ego_xy, ego_heading: 'float', parked_box, emerge_xy, s_max: 'float') -> 'list'`、台帳から引くなら `opsdrive.get("occlusion_visible_intervals")`)

## 使い方

自車の目が p(s) = ego_xy + s h を 0 ≤ s ≤ s_max 進む間に、点 ``emerge_xy`` が **見えている** 前進量の区間の列。

``occlusion_reveal_distance`` は「最初に見える所」だけを返すが、見え方は単調でない: 駐車車両の幅の帯の外(歩道の上)の点は、
遠くからは車と縁石の隙間越しに見え、近づくと隠れ、また見える。ここでは見える/見えないが切り替わり得る候補(角をかすめる視線と
進路の交点、進路と辺の交点 —— 閉形式)で [0, s_max] を区切り、各区間の中点で視線を判定して、見える区間を [(s0, s1), ...]
(昇順、隣り合う見える区間は結合)で返す。区間の端の縦距離は h · (e − p(s))。点が箱の内部なら []。

**Raises** ``ValueError``: 形・非有限・寸法 ≤ 0、s_max ≤ 0。

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
