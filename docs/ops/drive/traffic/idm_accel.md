---
op: idm_accel
dim: drive
category: traffic
in: any
out: any
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# idm_accel — DRIVE `traffic` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.idm_accel(v, gap, dv, *, v0: 'float', T: 'float', a: 'float', b: 'float', s0: 'float', delta: 'float' = 4.0)` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.idm_accel(v, gap, dv, *, v0: 'float', T: 'float', a: 'float', b: 'float', s0: 'float', delta: 'float' = 4.0)`、台帳から引くなら `opsdrive.get("idm_accel")`)

## 使い方

Intelligent Driver Model の加速度(Treiber, Hennecke, Helbing 2000)。

    a_IDM = a [ 1 − (v/v0)^δ − (s*/s)² ],   s* = s0 + max(0, v T + v Δv / (2 sqrt(a b)))

``dv`` = Δv = v − v_lead(近づいていれば正)、``gap`` = s = 先行車の後端までの距離(> 0、``inf`` = 前が空き)。
``v``, ``gap``, ``dv`` は numpy の放送で配列でも動く(スカラーを渡せば float を返す)。

門: 平衡車間 ``idm_equilibrium_gap`` で Δv = 0 なら 0、gap = inf で a(1 − (v/v0)^δ)。

**Raises** ``ValueError``: v < 0、gap ≤ 0、非有限、母数が正でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`traffic`)

[idm_equilibrium_gap](idm_equilibrium_gap.md) · [idm_platoon_simulate](idm_platoon_simulate.md) · [driver_style](driver_style.md) · [lateral_wobble](lateral_wobble.md) · [ou_estimate](ou_estimate.md) · [social_force_step](social_force_step.md) · [pedestrian_crossing](pedestrian_crossing.md) · [occlusion_reveal_distance](occlusion_reveal_distance.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
