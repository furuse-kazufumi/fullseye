---
op: neighbour_index_gaps
dim: math
category: construct
in: pairs
out: signal
examples: [poc_theorems_as_pictures]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# neighbour_index_gaps — MATH `construct` op

- **データ種**: `pairs` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.neighbour_index_gaps(points, k=6)` (実装を直接呼ぶなら `import mathops; mathops.neighbour_index_gaps(points, k=6)`、台帳から引くなら `opsmath.get("neighbour_index_gaps")`)

## 使い方

How far apart *in index* are a point's nearest neighbours — parastichy as a number.

In a phyllotactic pattern the visible spirals (**parastichies**) are not drawn
by anything; they are an illusion of which florets happen to sit next to each
other. This op replaces the illusion with a count: for every point, take its
*k* nearest neighbours **in space** and record the difference of their
**ordering indices**. The histogram of those differences is returned, index
``g`` holding how many neighbour pairs were ``g`` apart.

★**Why this earns its place**: with the golden angle the peaks land on
**Fibonacci numbers** (8, 13, 21, 34, 55 ...), and with any other angle they
do not. That is a statement about the arrangement which can be checked
**without looking at the picture** — which is the whole point, because the
spirals look convincing at every angle.

Parameters
----------
points : (N, 2) array
    Ordered points — **the order is the data here**, not a convenience.
k : int >= 1
    Neighbours per point (6 is the natural choice: a well-packed planar
    arrangement is locally hexagonal).

Returns a ``signal``: ``counts[g]`` = number of neighbour pairs whose index
difference is ``g`` (``counts[0]`` is always 0 — a point is not its own
neighbour).

**Raises** ``ValueError``: not an (N, 2) array; fewer than ``k + 1`` points;
``k`` below 1; non-finite coordinates.

Limits: the first points of a spiral sit near the centre where the packing
is degenerate, so the histogram has a low-index tail that carries no
parastichy information. Compare *peaks*, not the raw tail.

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

## 型が繋がる次の op(`signal` を入力に取れる)

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [stat_describe](../stats/stat_describe.md) · [stat_histogram](../stats/stat_histogram.md) · [stat_zscore](../stats/stat_zscore.md) · [interp_linear](../interp_poly/interp_linear.md) · [interp_cubic](../interp_poly/interp_cubic.md) · [interp_scattered](../interp_poly/interp_scattered.md)

## 同カテゴリ(`construct`)

[circle_packing_apollonian](circle_packing_apollonian.md) · [ford_circles](ford_circles.md) · [phyllotaxis_pattern](phyllotaxis_pattern.md) · [ifs_fractal](ifs_fractal.md) · [ifs_similarity_dimension](ifs_similarity_dimension.md) · [space_filling_curve](space_filling_curve.md) · [curve_locality](curve_locality.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
