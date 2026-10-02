---
op: tether_slack_angle
dim: drive
category: kendama
in: 
out: any
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# tether_slack_angle — DRIVE `kendama` op

- **データ種**: `なし` → `any`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.tether_slack_angle(theta0: 'float', L: 'float', g: 'float' = 9.81)` (実装を直接呼ぶなら `import kendama; kendama.tether_slack_angle(theta0: 'float', L: 'float', g: 'float' = 9.81)`、台帳から引くなら `opsdrive.get("tether_slack_angle")`)

## 使い方

真下で速さ v₀ = √(2gL(1 − cos θ₀)) をもつ玉(棒なら θ₀ で止まるエネルギー)のひもが弛む角 θ_s(真下から)。

導出: v² = 2gL(cos θ − cos θ₀)、T = m(v²/L + g cos θ) = m g (3 cos θ − 2 cos θ₀) = 0 → **cos θ_s = (2/3) cos θ₀**。
上半分(cos θ_s < 0)に達するのは cos θ₀ < 0 ⇔ θ₀ > π/2 のときだけ。θ₀ ≤ π/2 なら張力は θ₀ で m g cos θ₀ ≥ 0 まで下がる
だけで弛まない → None。θ₀ = π(頂点にちょうど届くエネルギー)で θ_s = arccos(−2/3) = 131.8°。θ₀ ∈ (0, π] 以外は ValueError。
θ₀ > π/2 の玉を静止から放すと最初から弛む(張力 m g cos θ₀ < 0)ので、θ₀ は真下での速さで与える。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`kendama`)

[kendama_params](kendama_params.md) · [elliptic_k_agm](elliptic_k_agm.md) · [pendulum_period_exact](pendulum_period_exact.md) · [pendulum_launch_speed](pendulum_launch_speed.md) · [pendulum_rod_simulate](pendulum_rod_simulate.md) · [tether_tension_fixed](tether_tension_fixed.md) · [swing_up_plan](swing_up_plan.md) · [swing_up_apex](swing_up_apex.md)

---
*Provenance: kendama.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
