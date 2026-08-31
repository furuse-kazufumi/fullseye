---
op: poly_fit
dim: math
category: interp_poly
in: signal × signal
out: table
examples: [math_metrology, signal_filter]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# poly_fit — MATH `interp_poly` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import mathops; mathops.poly_fit(x, y, degree)` (または `opsmath.get("poly_fit")`)

## 使い方

Least-squares polynomial fit with its conditioning **on the record**.

    Fits ``y ≈ c[0] x^d + ... + c[d]`` (coefficients highest-power-first, the
    :func:`poly_eval` / ``np.polyval`` convention) by SVD least squares on the
    Vandermonde matrix. *degree* must be an integer ``>= 0`` with at least
    ``degree + 1`` samples (fail-closed: an exactly-determined fit is allowed,
    an under-determined one is not).

    Returns a dict — the fit and its health, inseparable:

    ``coeffs`` ``(degree + 1,)`` float64 · ``degree`` · ``cond`` the Vandermonde
    condition number (:func:`mat_cond` of the design matrix) · ``rms_residual``
    root-mean-square of ``y - p(x)``.

    **The conditioning mechanism**: when ``cond > POLY_COND_WARN`` (1e10) a
    ``RuntimeWarning`` is emitted *and* the number is in the result — an
    equispaced degree-10 fit on raw pixel coordinates is already past it. High
    degree on a raw coordinate range is the classic double trap: the
    Vandermonde columns become near-collinear (digits lost, coefficients
    unstable) and the fit oscillates between nodes (Runge phenomenon, Runge
    1901). Centre and scale x to ``[-1, 1]`` first, or keep degree ≤ ~6.

    HALCON: no public polynomial-fitting tuple operator (fitting of this kind
    lives inside HALCON's calibration internals).

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
- [signal_filter](../../../../examples/signal_filter.py) — `py -3.11 examples/signal_filter.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`interp_poly`)

[interp_linear](interp_linear.md) · [interp_cubic](interp_cubic.md) · [poly_eval](poly_eval.md) · [poly_roots](poly_roots.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
