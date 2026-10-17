---
op: doe_orthogonal_array
dim: multivar
category: plan
in: 
out: design
examples: [doe_plan_tour, multivar_inspection_tour, poc_simcal_thin_film]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# doe_orthogonal_array — MULTIVAR `plan` op

- **データ種**: `なし` → `design`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.doe_orthogonal_array(name='L9', factors=None, columns=None) -> 'dict'` (実装を直接呼ぶなら `import doe; doe.doe_orthogonal_array(name='L9', factors=None, columns=None) -> 'dict'`、台帳から引くなら `opsmultivar.get("doe_orthogonal_array")`)

## 使い方

Orthogonal array L4 / L8 / L9 / L12 / L16 / L18 / L27 from a published table -> ``design``.

The arrays are **copied from published tables** (sources and the copy check in
:data:`OA_SOURCES`), not generated: Taguchi's numbering of columns is what
shop-floor literature and the linear graphs refer to, and a generated array with
another column order would silently assign factors to interaction columns.
Published level symbols 1, 2 (, 3) map to coded −1, +1 (, or −1, 0, +1).

``factors``: int / names / (name, lo, hi[, unit[, scale]]) (default: one factor per
column). ``columns``: 1-based column numbers to assign the factors to, in order
(default: the first k columns; for L18 column 1 is the two-level one).

The returned ``alias`` lists, for every pair of assigned factors, the columns their
interaction falls on and the share (see :func:`_oa_interaction_share`) — if such a
column also carries an assigned factor, that main effect is confounded with the
interaction. ``meta['strength2_ok']`` re-checks orthogonality on the table actually
used, and ``meta['regular']`` says whether interactions land on whole columns.

## 詳しい使い方ガイド

- [design_of_experiments ファミリ ガイド](../guides/design_of_experiments.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [doe_plan_tour](../../../../examples/doe_plan_tour.py) — `py -3.11 examples/doe_plan_tour.py`
- [multivar_inspection_tour](../../../../examples/multivar_inspection_tour.py) — `py -3.11 examples/multivar_inspection_tour.py`
- [poc_simcal_thin_film](../../../../examples/poc_simcal_thin_film.py) — `py -3.11 examples/poc_simcal_thin_film.py`

## 型が繋がる次の op(`design` を入力に取れる)

[doe_decode](../coding/doe_decode.md) · [rsm_fit](../analysis/rsm_fit.md) · [doe_main_effects](../analysis/doe_main_effects.md) · [sens_morris](../sensitivity/sens_morris.md) · [sens_sobol](../sensitivity/sens_sobol.md)

## 同カテゴリ(`plan`)

[doe_lhs](doe_lhs.md) · [doe_fractional_factorial](doe_fractional_factorial.md) · [doe_central_composite](doe_central_composite.md) · [doe_box_behnken](doe_box_behnken.md)

---
*Provenance: doe.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
