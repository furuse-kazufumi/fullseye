---
op: doe_fractional_factorial
dim: multivar
category: plan
in: 
out: design
examples: [doe_plan_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# doe_fractional_factorial — MULTIVAR `plan` op

- **データ種**: `なし` → `design`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.doe_fractional_factorial(factors=5, p=2, generators=None, center=0) -> 'dict'` (実装を直接呼ぶなら `import doe; doe.doe_fractional_factorial(factors=5, p=2, generators=None, center=0) -> 'dict'`、台帳から引くなら `opsmultivar.get("doe_fractional_factorial")`)

## 使い方

Regular two-level fractional factorial 2^(k-p) from generators (Box & Hunter 1961) -> ``design``.

The first ``k - p`` factors (letters A, B, C ... skipping I) form a full factorial
in standard (Yates) order, A changing fastest. Each generator ``"D=ABC"`` sets an
added factor's column to the product of base columns (``"E=-ABD"`` for the other
half). ``generators=None`` takes the recommended generators for (k, p) from the
NIST/SEMATECH e-Handbook table (:data:`FF_NIST`, 5.3.3.4.7 Table 3.17, after Box, Hunter
& Hunter); ``p=0`` or ``generators=()`` gives the full factorial 2^k.

The defining relation (every product of generator words ``I = ABCD = ...``), the
**resolution** (length of the shortest word: III = main effects aliased with two-factor
interactions, IV = main effects clear but 2fi aliased with each other, V = 2fi clear)
and the alias table of main effects and two-factor interactions are returned in
``meta`` and ``alias``. They are computed from the generators, and the returned
matrix is checked against them (each aliased pair of columns is identical up to sign).

``center`` adds centre runs (coded 0) for a curvature check; they do not change the
alias structure.

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

[doe_lhs](doe_lhs.md) · [doe_orthogonal_array](doe_orthogonal_array.md) · [doe_central_composite](doe_central_composite.md) · [doe_box_behnken](doe_box_behnken.md)

---
*Provenance: doe.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
