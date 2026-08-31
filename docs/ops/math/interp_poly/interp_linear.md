---
op: interp_linear
dim: math
category: interp_poly
in: signal × signal × signal
out: signal
examples: [math_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# interp_linear — MATH `interp_poly` op

- **データ種**: `signal × signal × signal` → `signal`
- **呼び出し**: `import mathops; mathops.interp_linear(x, y, xq, out_of_range='raise')` (または `opsmath.get("interp_linear")`)

## 使い方

Piecewise-linear interpolation of ``(x, y)`` samples at query *xq*.

    *x* must be strictly increasing (fail-closed: an unsorted or duplicated
    grid raises rather than being silently reordered). *xq* is a scalar or a
    1-D array; a scalar query returns a Python float, an array returns float64.

    **Out-of-range is an explicit choice**, never silent: ``'raise'`` (default)
    refuses any query outside ``[x[0], x[-1]]`` — a calibration table queried
    beyond its calibrated range is a wrong answer waiting to happen — while
    ``'clamp'`` holds the boundary values (the honest flat extension; there is
    deliberately no silent linear extrapolation mode).

    Exact on the nodes and exact for data that is genuinely piecewise linear.
    HALCON: ``get_y_value_funct_1d`` interpolates function pairs the same way
    (see :mod:`funct1d`, which works HALCON's index-grid convention; this op
    takes an arbitrary strictly-increasing x grid).

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

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [stat_describe](../stats/stat_describe.md) · [stat_histogram](../stats/stat_histogram.md) · [stat_zscore](../stats/stat_zscore.md) · [interp_cubic](interp_cubic.md) · [poly_fit](poly_fit.md) · [poly_eval](poly_eval.md)

## 同カテゴリ(`interp_poly`)

[interp_cubic](interp_cubic.md) · [poly_fit](poly_fit.md) · [poly_eval](poly_eval.md) · [poly_roots](poly_roots.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
