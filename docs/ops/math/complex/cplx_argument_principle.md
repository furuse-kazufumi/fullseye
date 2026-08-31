---
op: cplx_argument_principle
dim: math
category: complex
in: cpoints × cpoints
out: measurement
examples: [math_complex]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# cplx_argument_principle — MATH `complex` op

- **データ種**: `cpoints × cpoints` → `measurement`
- **呼び出し**: `import mathops; mathops.cplx_argument_principle(z, fz)` (または `opsmath.get("cplx_argument_principle")`)

## 使い方

Argument principle: count zeros minus poles enclosed by a contour, from
sampled values of ``f`` alone.

``Z - P = 1/(2*pi*i) ∮ f'/f dz`` equals the winding number of the **image
curve** ``f(z)`` around the origin (Cauchy 1831 / Riemann): as the contour
is traversed once counter-clockwise, the argument of ``f`` increases by
``2*pi (Z - P)``, counting multiplicities. Computing it as a winding number
of the image needs no derivative and no root finding — only ``f`` sampled
on the path — and returns an exact integer.

Honest limitations, all of them real:

  * It returns the **difference** ``Z - P``, never the two separately. A
    simple zero and a simple pole inside cancel to 0.
  * The result is multiplied by the winding number of the contour itself,
    so it equals ``Z - P`` only for a **simple, positively-oriented**
    contour (a clockwise one returns ``-(Z - P)``).
  * It is the winding of the *sampled* image polygon, so it **aliases low**
    on a coarse contour. A half-turn jump between samples is detected and
    raised; anything below that is indistinguishable from a genuine slower
    turn — ``f = z**5`` on a 4-point circle returns 1, not 5 (measured).
    A ``RuntimeWarning`` fires from ``pi/2`` per step onward
    (:data:`WIND_ALIAS_WARN`); the verification that actually works is to
    double ``n`` until the count repeats.

**Raises** ``ValueError``: ``f`` vanishes at a sample point (a zero *on*
the path — the count is undefined there), the image curve is undersampled
(a half-turn between consecutive samples: refine the contour), plus the
usual shape/finiteness contracts.

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

- [math_complex](../../../../examples/math_complex.py) — `py -3.11 examples/math_complex.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`complex`)

[cplx_contour_circle](cplx_contour_circle.md) · [cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md) · [cplx_mobius](cplx_mobius.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
