---
op: doe_box_behnken
dim: multivar
category: plan
in: 
out: design
examples: [doe_plan_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# doe_box_behnken — MULTIVAR `plan` op

- **データ種**: `なし` → `design`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.doe_box_behnken(factors=3, center=3) -> 'dict'` (実装を直接呼ぶなら `import doe; doe.doe_box_behnken(factors=3, center=3) -> 'dict'`、台帳から引くなら `opsmultivar.get("doe_box_behnken")`)

## 使い方

Box-Behnken design (Box & Behnken 1960) for 3, 4 or 5 factors -> ``design``.

Three levels per factor and no run at a corner of the cube: for every pair of
factors, a 2^2 factorial (±1, ±1) with all other factors at 0, plus ``center``
centre runs — 12, 24 and 40 edge runs for k = 3, 4, 5 (the pair construction of
Box & Behnken's table for these k). Useful when the extreme corners are unsafe or
cannot be set. k = 4 is rotatable. Larger k use incomplete-block constructions
that are not reproduced here and are refused.

## 詳しい使い方ガイド

- [design_of_experiments ファミリ ガイド](../guides/design_of_experiments.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [doe_plan_tour](../../../../examples/doe_plan_tour.py) — `py -3.11 examples/doe_plan_tour.py`

## 型が繋がる次の op(`design` を入力に取れる)

[doe_decode](../coding/doe_decode.md) · [rsm_fit](../analysis/rsm_fit.md) · [doe_main_effects](../analysis/doe_main_effects.md) · [sens_morris](../sensitivity/sens_morris.md) · [sens_sobol](../sensitivity/sens_sobol.md)

## 同カテゴリ(`plan`)

[doe_lhs](doe_lhs.md) · [doe_orthogonal_array](doe_orthogonal_array.md) · [doe_fractional_factorial](doe_fractional_factorial.md) · [doe_central_composite](doe_central_composite.md)

---
*Provenance: doe.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
