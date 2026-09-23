---
op: circle_packing_apollonian
dim: math
category: construct
in: 
out: table
examples: [poc_theorems_as_pictures]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# circle_packing_apollonian — MATH `construct` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.circle_packing_apollonian(curvatures=(-1.0, 2.0, 2.0, 3.0), depth=4, min_curvature=0.0)` (実装を直接呼ぶなら `import mathops; mathops.circle_packing_apollonian(curvatures=(-1.0, 2.0, 2.0, 3.0), depth=4, min_curvature=0.0)`、台帳から引くなら `opsmath.get("circle_packing_apollonian")`)

## 使い方

Apollonian gasket from a Descartes quadruple — every circle a theorem.

Four mutually tangent circles satisfy the **Descartes circle theorem**

    (k1 + k2 + k3 + k4)**2 == 2 * (k1**2 + k2**2 + k3**2 + k4**2)

where ``k = 1/r`` is the curvature (negative for the enclosing circle). The
theorem is quadratic in ``k4``, so a triple of mutually tangent circles has
**two** solutions and the second is ``k4' = 2*(k1+k2+k3) - k4``; recursing on
that reflection fills the gasket. The centres follow the complex form
``k4*z4 = k1*z1 + k2*z2 + k3*z3 +- 2*sqrt(k1*k2*z1*z2 + ...)``, so no
geometry is fitted — every circle is produced by an exact algebraic step.

★**Why this earns its place**: the drawing carries its own proof. Each circle
can be checked against Descartes to machine precision, tangency is
``|z_i - z_j| == |r_i +- r_j|`` exactly, and **an integral quadruple stays
integral for ever** — start from ``(-1, 2, 2, 3)`` and every curvature in the
infinite packing is an integer (Lagarias-Mallows-Wilks). A drawing routine
that is slightly wrong cannot keep integers integral.

Parameters
----------
curvatures : 4 floats
    A Descartes quadruple. The default ``(-1, 2, 2, 3)`` is the smallest
    integral gasket. Must satisfy the theorem to ``1e-9`` relative.
depth : int >= 0
    Reflection levels. Level 0 is the four seed circles; each further level
    adds ``4 * 3**(level-1)``, so the total is ``2 * 3**depth + 2``.
min_curvature : float
    Drop circles smaller than ``1/min_curvature`` (0 = keep all).

Returns a ``table``: ``x``, ``y``, ``radius``, ``curvature``, ``depth``
(the enclosing circle has negative curvature and positive radius).

**Raises** ``ValueError``: not four curvatures; the quadruple does not
satisfy Descartes; every curvature negative or zero (no packing); ``depth``
negative or so large the packing exceeds the cap; non-finite input.

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

[ford_circles](ford_circles.md) · [phyllotaxis_pattern](phyllotaxis_pattern.md) · [neighbour_index_gaps](neighbour_index_gaps.md) · [ifs_fractal](ifs_fractal.md) · [ifs_similarity_dimension](ifs_similarity_dimension.md) · [space_filling_curve](space_filling_curve.md) · [curve_locality](curve_locality.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
