---
op: ford_circles
dim: math
category: construct
in: 
out: table
examples: [poc_theorems_as_pictures]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# ford_circles — MATH `construct` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ford_circles(max_denominator=12, lo=0, hi=1)` (実装を直接呼ぶなら `import mathops; mathops.ford_circles(max_denominator=12, lo=0, hi=1)`、台帳から引くなら `opsmath.get("ford_circles")`)

## 使い方

Ford circles for the Farey fractions — tangency *is* an integer identity.

For a fraction ``p/q`` in lowest terms the Ford circle sits at
``(p/q, 1/(2q**2))`` with radius ``1/(2q**2)``. Two such circles are
**tangent if and only if** ``|p*s - q*r| == 1`` — the Farey-neighbour
condition — and otherwise strictly disjoint. They never overlap.

★**Why this earns its place**: the picture's correctness is an identity
between integers, not a tolerance. ``|p*s - q*r|`` is computed in exact
integer arithmetic and compared with the *geometric* tangency
``|c_i - c_j| == r_i + r_j`` measured from the coordinates; the two must
agree on every pair. The number of fractions is the Farey length
``1 + sum(phi(q) for q in 1..n)``, another exact integer.

Returns a ``table``: ``x``, ``y``, ``radius``, ``p``, ``q``.

**Raises** ``ValueError``: ``max_denominator < 1``; ``lo >= hi``; the
interval or denominator would exceed the cap.

HALCON: no operator.

## ファミリ共通の入力契約(fail-closed)

mathops の全 op は入力を検証してから計算する(黙って通さない):

- **complex 入力は `ValueError`** — float64 への強制変換は虚部を黙って捨てる(numpy は ComplexWarning だけ出して「もっともらしく間違った」実数を返す)。`.real`/`.imag`/`abs()` を明示するか、複素対応の complexops を使う。
- **masked array(masked 要素あり)は `ValueError`** — マスクを剥がして下の生値を使う暗黙変換を拒否。埋める/落とすを明示する。
- **NaN/Inf は全入力で `ValueError`**(件数を明示して拒否 — 結果全体に伝播するため)。
- **形状は厳格**: 1-D と 2-D を暗黙昇格・ブロードキャストしない(vector 枠に matrix、matrix 枠に vector は `ValueError`。reshape を明示する)。
- **サイズ上限**: 行列を取る op と `stat_histogram` の bins は `mathops.MAX_ELEMENTS`(2^26 ≈ 6700 万要素)超で `ValueError`。

## 詳しい使い方ガイド

- [math_metrology ファミリ ガイド](../guides/math_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_theorems_as_pictures](../../../../examples/poc_theorems_as_pictures.py) — `py -3.11 examples/poc_theorems_as_pictures.py`

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md)

## 同カテゴリ(`construct`)

[circle_packing_apollonian](circle_packing_apollonian.md) · [phyllotaxis_pattern](phyllotaxis_pattern.md) · [neighbour_index_gaps](neighbour_index_gaps.md) · [ifs_fractal](ifs_fractal.md) · [ifs_similarity_dimension](ifs_similarity_dimension.md) · [space_filling_curve](space_filling_curve.md) · [curve_locality](curve_locality.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
