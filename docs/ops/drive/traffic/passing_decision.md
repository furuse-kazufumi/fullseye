---
op: passing_decision
dim: drive
category: traffic
in: 
out: any
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# passing_decision — DRIVE `traffic` op

- **データ種**: `なし` → `any`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.passing_decision(dist_oncoming: 'float', parked_len: 'float', margin_front: 'float', margin_back: 'float', v_ego: 'float', v_oncoming: 'float', *, lane_change_time: 'float', ego_length: 'float' = 0.0, pet_min: 'float' = 0.0, v_obstacle: 'float' = 0.0) -> 'str'` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.passing_decision(dist_oncoming: 'float', parked_len: 'float', margin_front: 'float', margin_back: 'float', v_ego: 'float', v_oncoming: 'float', *, lane_change_time: 'float', ego_length: 'float' = 0.0, pet_min: 'float' = 0.0, v_obstacle: 'float' = 0.0) -> 'str'`、台帳から引くなら `opsdrive.get("passing_decision")`)

## 使い方

対向車までの距離 ``dist_oncoming``(判断時、自車が x_in にいるとき)で "go" か "wait" を返す。

D ≥ D*(``passing_gap_required`` の ``d_required``)なら "go"(境目ちょうどは PET = pet_min で go)。
``dist_oncoming = +inf`` は「対向車なし」= "go"(他の引数の検査はする)。−inf・NaN は ValueError。
``v_obstacle`` > 0 は走っている障害物(``passing_gap_required``)。
門: D* ± ε で判断が切り替わる / ``passing_simulate`` の PET が pet_min になる境目と D* が一致。

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
