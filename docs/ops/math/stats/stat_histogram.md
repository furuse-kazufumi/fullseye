---
op: stat_histogram
dim: math
category: stats
in: signal
out: pairs
examples: [math_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# stat_histogram — MATH `stats` op

- **データ種**: `signal` → `pairs`
- **呼び出し**: `import mathops; mathops.stat_histogram(x, bins=10, range=None, density=False)` (または `opsmath.get("stat_histogram")`)

## 使い方

Histogram of a 1-D sample with the binning **explicit**.

*bins* is a positive integer count of equal-width bins; *range* is an
explicit ``(lo, hi)`` (finite, ``lo < hi``) or ``None`` to span the data
(values exactly at ``hi`` land in the last bin, numpy's convention; with an
explicit *range*, values outside it are excluded from every bin — they
simply do not count, which is why passing *range* explicitly is the honest
choice when comparing histograms across datasets). With ``density=False``
(default) *counts* are occurrence **frequencies** (int64, summing to the
number of in-range samples); with ``density=True`` they form a
**probability density** (float64, integrating to 1 over the range).
A *range* that excludes **every** sample raises ``ValueError`` under
``density=True`` (the density would be 0/0 — silent NaNs refused) while
``density=False`` honestly returns all-zero counts. *bins* is capped at
``MAX_ELEMENTS`` (the edge/count arrays are allocations too).

Returns ``(counts, edges)`` — ``edges`` has ``bins + 1`` entries;
bin *i* is ``[edges[i], edges[i+1])``.

HALCON: ``tuple_histo_range`` (and ``gray_histo`` for whole images).

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

- [math_metrology](../../../../examples/math_metrology.py) — `py -3.11 examples/math_metrology.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

—

## 同カテゴリ(`stats`)

[stat_describe](stat_describe.md) · [stat_covariance](stat_covariance.md) · [stat_correlation](stat_correlation.md) · [stat_zscore](stat_zscore.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
