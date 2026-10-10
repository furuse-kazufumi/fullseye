---
op: fresnel_integrals
dim: drive
category: lateral
in: any
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# fresnel_integrals — DRIVE `lateral` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.fresnel_integrals(x)` (実装を直接呼ぶなら `import drivelateral; drivelateral.fresnel_integrals(x)`、台帳から引くなら `opsdrive.get("fresnel_integrals")`)

## 使い方

フレネル積分 C(x) = ∫₀ˣ cos(π t²/2) dt、S(x) = ∫₀ˣ sin(π t²/2) dt(奇関数)。

|x| ≤ 3.5 はべき級数、それより大きいと漸近展開(補助関数 f, g)。誤差は 1e-8 以下(門: 数値積分)。
返り値: (C, S)(x と同じ形)。

**Raises** ``ValueError``: 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
