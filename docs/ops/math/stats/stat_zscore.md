---
op: stat_zscore
dim: math
category: stats
in: signal
out: signal
examples: [math_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# stat_zscore — MATH `stats` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import mathops; mathops.stat_zscore(x)` (または `opsmath.get("stat_zscore")`)

## 使い方

Standardise a 1-D sample: ``(x - mean) / std`` (population ``ddof=0``).

    The result has mean 0 and standard deviation 1 — the common currency for
    comparing residuals across scales and flagging outliers (``|z| > 3``).

    **A constant input raises ``ValueError``** — the decision, stated: with
    zero variance the z-score is 0/0. Returning silent zeros would claim "every
    point is perfectly average", which is *a* convention but hides upstream
    breakage (a sensor stuck at one value would sail through an outlier gate).
    Fail-closed instead; a caller who wants the all-zeros convention can catch
    this and substitute deliberately.

    HALCON: no direct tuple operator (compose ``tuple_mean`` +
    ``tuple_deviation`` + arithmetic).

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

## 型が繋がる次の op(`signal` を入力に取れる)

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [stat_describe](stat_describe.md) · [stat_histogram](stat_histogram.md) · [interp_linear](../interp_poly/interp_linear.md) · [interp_cubic](../interp_poly/interp_cubic.md) · [poly_fit](../interp_poly/poly_fit.md) · [poly_eval](../interp_poly/poly_eval.md)

## 同カテゴリ(`stats`)

[stat_describe](stat_describe.md) · [stat_histogram](stat_histogram.md) · [stat_covariance](stat_covariance.md) · [stat_correlation](stat_correlation.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
