---
op: curve_locality
dim: math
category: construct
in: pairs
out: table
examples: [poc_theorems_as_pictures]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# curve_locality — MATH `construct` op

- **データ種**: `pairs` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.curve_locality(points, gaps=(1, 2, 4, 8, 16, 32))` (実装を直接呼ぶなら `import mathops; mathops.curve_locality(points, gaps=(1, 2, 4, 8, 16, 32))`、台帳から引くなら `opsmath.get("curve_locality")`)

## 使い方

Points ``k`` apart along the curve — how far apart are they on the plane?

The reason a space-filling curve is used for storage layout, texture tiling
or rendering order is **locality**: neighbours in the ordering should stay
neighbours in space. This op measures that directly — for each gap ``k`` it
returns the mean Euclidean distance between points ``i`` and ``i + k``.

★**Why this earns its place**: the claim "Hilbert has better locality than
scanning row by row" is usually asserted and never measured. Here it is a
table you can read: a Hilbert curve grows roughly as ``sqrt(k)`` (measured
1.00 / 1.53 / 2.12 / 3.17 / 4.29 / 6.38 at k = 1 .. 32), while a boustrophedon
scan grows nearly **linearly** (1.00 / 1.96 / 3.79 / 7.07 / 12.12 / 16.07) —
an honest, reproducible gap rather than a slogan.

Parameters
----------
points : (N, 2) array
    The curve's points **in visiting order**.
gaps : ints
    Index gaps to report. Gaps at or beyond ``N`` are dropped (not an error;
    a short curve simply has nothing to say about a long gap).

Returns a ``table``: ``gap`` (int), ``mean_distance``, and ``ratio`` =
``mean_distance / mean_distance[gap == 1]`` so curves of different scales can
be compared directly.

**Raises** ``ValueError``: not an (N, 2) array; fewer than 2 points;
non-finite coordinates; every requested gap out of range.

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

[circle_packing_apollonian](circle_packing_apollonian.md) · [ford_circles](ford_circles.md) · [phyllotaxis_pattern](phyllotaxis_pattern.md) · [neighbour_index_gaps](neighbour_index_gaps.md) · [ifs_fractal](ifs_fractal.md) · [ifs_similarity_dimension](ifs_similarity_dimension.md) · [space_filling_curve](space_filling_curve.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
