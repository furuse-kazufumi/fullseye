---
op: ifs_similarity_dimension
dim: math
category: construct
in: 
out: measurement
examples: [poc_theorems_as_pictures]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# ifs_similarity_dimension — MATH `construct` op

- **データ種**: `なし` → `measurement`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ifs_similarity_dimension(preset='sierpinski', maps=None, tol=1e-13)` (実装を直接呼ぶなら `import mathops; mathops.ifs_similarity_dimension(preset='sierpinski', maps=None, tol=1e-13)`、台帳から引くなら `opsmath.get("ifs_similarity_dimension")`)

## 使い方

Moran's equation ``sum(r_i**d) = 1`` solved for ``d`` — from the maps alone.

The similarity dimension of a self-similar set, computed **before** anything
is drawn. Valid when the pieces overlap only on a set of measure zero (the
open set condition); affine maps that are not similarities (the fern) have
no single ratio, so this raises rather than returning a number that looks
right (measured: the fern's four maps have singular-value ratios from 0.16
to 0.85, so no ``r_i`` exists).

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

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`construct`)

[circle_packing_apollonian](circle_packing_apollonian.md) · [ford_circles](ford_circles.md) · [phyllotaxis_pattern](phyllotaxis_pattern.md) · [neighbour_index_gaps](neighbour_index_gaps.md) · [ifs_fractal](ifs_fractal.md) · [space_filling_curve](space_filling_curve.md) · [curve_locality](curve_locality.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
