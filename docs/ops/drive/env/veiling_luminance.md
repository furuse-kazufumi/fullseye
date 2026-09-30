---
op: veiling_luminance
dim: drive
category: env
in: any × any
out: any
examples: [poc_veiling_glare]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# veiling_luminance — DRIVE `env` op

- **データ種**: `any × any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.veiling_luminance(E_glare, theta_deg, *, model: 'str' = 'stiles_holladay', age: 'float' = 40.0, p: 'float' = 0.5)` (実装を直接呼ぶなら `import driveenv; driveenv.veiling_luminance(E_glare, theta_deg, *, model: 'str' = 'stiles_holladay', age: 'float' = 40.0, p: 'float' = 0.5)`、台帳から引くなら `opsdrive.get("veiling_luminance")`)

## 使い方

減能グレアの光幕輝度 L_v [cd/m²] (配列可)。E_glare = 目の位置での光源の照度 [lx]、θ = 光源と視線の角 [度]。

``model="stiles_holladay"``: L_v = 10 E / θ²(θ は 1°〜30° 程度で使われる経験式)。
``model="cie"``: CIE 146:2002 の一般式 L_v/E = 10/θ³ + (5/θ² + 0.1 p/θ)(1 + (age/62.5)⁴) + 0.0025 p
(p = 目の色素の係数、既定 0.5)。θ ≤ 0 は拒否(光源そのものは光幕でなく像)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_veiling_glare](../../../../examples/poc_veiling_glare.py) — `py -3.11 examples/poc_veiling_glare.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`env`)

[julian_day](julian_day.md) · [sun_at](sun_at.md) · [sun_events](sun_events.md) · [sun_vector](sun_vector.md) · [sun_illuminance](sun_illuminance.md) · [koschmieder](koschmieder.md) · [mor_from_beta](mor_from_beta.md) · [beta_from_mor](beta_from_mor.md)

---
*Provenance: driveenv.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
