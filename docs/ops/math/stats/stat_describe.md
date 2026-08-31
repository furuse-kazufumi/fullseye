---
op: stat_describe
dim: math
category: stats
in: signal
out: table
examples: [math_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# stat_describe — MATH `stats` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import mathops; mathops.stat_describe(x)` (または `opsmath.get("stat_describe")`)

## 使い方

Five-number-plus summary of a 1-D sample, as a plain dict.

Returns ``{"n", "mean", "std", "min", "max", "percentiles"}`` where
``percentiles`` is ``{"p5", "p25", "p50", "p75", "p95"}`` (linear
interpolation between order statistics, numpy's default). ``std`` is the
**population** standard deviation (``ddof=0`` — well-defined down to a
single sample; multiply by ``sqrt(n/(n-1))`` for the sample estimator,
which is what :func:`stat_covariance` uses, documented there).

The tails matter in metrology: ``mean``/``std`` of residuals say how good
the fit is *on average*; ``p5``/``p95`` say how bad the *outliers* are —
report both, a fit can pass on RMS and fail on extremes.

HALCON: ``tuple_mean`` / ``tuple_deviation`` / ``tuple_min`` /
``tuple_max`` (the percentile row has no single HALCON tuple operator).

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

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`stats`)

[stat_histogram](stat_histogram.md) · [stat_covariance](stat_covariance.md) · [stat_correlation](stat_correlation.md) · [stat_zscore](stat_zscore.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
