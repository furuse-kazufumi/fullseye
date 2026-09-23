---
op: ifs_fractal
dim: math
category: construct
in: 
out: pairs
examples: [poc_theorems_as_pictures]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# ifs_fractal — MATH `construct` op

- **データ種**: `なし` → `pairs`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ifs_fractal(preset='sierpinski', maps=None, n_points=60000, seed=0, burn_in=32)` (実装を直接呼ぶなら `import mathops; mathops.ifs_fractal(preset='sierpinski', maps=None, n_points=60000, seed=0, burn_in=32)`、台帳から引くなら `opsmath.get("ifs_fractal")`)

## 使い方

Chaos game on an iterated function system — the dimension is a closed form.

Picks a map at random (by ``weights``, or by area if none are given), applies
it, and plots the orbit. After a short burn-in the orbit lands on the
attractor and stays there, so the picture is the attractor and not a path to
it.

★**Why this earns its place — two numbers that must agree and were computed
two different ways**:

  - *Moran's equation.* For similarities with ratios ``r_i`` satisfying the
    open set condition, the similarity dimension ``d`` is the unique root of
    ``sum(r_i**d) == 1`` — a closed form read off the **maps**, before
    anything is drawn. Sierpinski gives ``log 3 / log 2 = 1.5850``, the Koch
    curve ``log 4 / log 3 = 1.2619``, Cantor dust ``log 4 / log 3`` as well.
  - *Box counting.* This repository's existing ``fractal_dimension``
    operator measures the dimension from the **drawing**. The two must agree,
    and they are not the same computation: one is algebra on the maps, the
    other is a regression on a rasterised image.

  Hutchinson's theorem gives a third, structural check: the attractor is
  **invariant**, so applying every map to the point set maps it back into
  itself.

``maps`` overrides ``preset``: a sequence of ``(a, b, c, d, e, f)`` meaning
``x -> [[a, b], [c, d]] x + [e, f]``.

Returns ``pairs`` ``(n, 2)``.

**Raises** ``ValueError``: unknown preset; a map that is not 6 numbers; a map
that is not a contraction (spectral norm >= 1 — the orbit would escape);
``n_points`` below 1 or over the cap; negative ``burn_in``.

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

## 型が繋がる次の op(`pairs` を入力に取れる)

[neighbour_index_gaps](neighbour_index_gaps.md) · [curve_locality](curve_locality.md)

## 同カテゴリ(`construct`)

[circle_packing_apollonian](circle_packing_apollonian.md) · [ford_circles](ford_circles.md) · [phyllotaxis_pattern](phyllotaxis_pattern.md) · [neighbour_index_gaps](neighbour_index_gaps.md) · [ifs_similarity_dimension](ifs_similarity_dimension.md) · [space_filling_curve](space_filling_curve.md) · [curve_locality](curve_locality.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
