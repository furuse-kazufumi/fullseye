---
op: cplx_contour_integral
dim: math
category: complex
in: cpoints × cpoints
out: cscalar
examples: [math_complex]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# cplx_contour_integral — MATH `complex` op

- **データ種**: `cpoints × cpoints` → `cscalar`
- **呼び出し**: `import mathops; mathops.cplx_contour_integral(z, fz)` (または `opsmath.get("cplx_contour_integral")`)

## 使い方

Closed contour integral ``∮ f(z) dz`` by the chordal trapezoidal rule.

*z* are the contour vertices (closing segment implicit, see
:func:`cplx_contour_circle`) and *fz* the function sampled at exactly those
points — the op never calls back into Python, so any ``f`` is allowed as
long as you can sample it. The quadrature is
``sum_k (f_k + f_{k+1})/2 * (z_{k+1} - z_k)``, i.e. the trapezoidal rule
along the *chords*; it is exact for a piecewise-linear integrand and second
order otherwise.

Ground truth it reproduces: ``f = 1/(z - a)`` around a circle enclosing
``a`` integrates to ``2*pi*i`` (Cauchy); measured on the unit circle with
``a = 0``, the relative error is 1.0e-4 at ``n = 256`` and
6.3e-6 at ``n = 1024`` — a factor 16.0 for 4x
refinement, i.e. the ``O(n^-2)`` rate, *not* the spectral accuracy the
trapezoid rule enjoys when applied in the angle parameter. That difference
is the honest price of accepting an arbitrary point list instead of a
parametrisation.

Orientation follows the sample order: a clockwise contour returns the
negative of the counter-clockwise one.

**Raises** ``ValueError``: fewer than 3 points, ``len(z) != len(fz)``, a
degenerate contour (all points coincide), non-finite/masked input, or a sum
that overflowed (``|f|`` near a pole *on* the path).

HALCON: no operator (contour integration is not part of its tuple/XLD API).

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

## 型が繋がる次の op(`cscalar` を入力に取れる)

—

## 同カテゴリ(`complex`)

[cplx_contour_circle](cplx_contour_circle.md) · [cplx_poly_eval](cplx_poly_eval.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md) · [cplx_mobius](cplx_mobius.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
