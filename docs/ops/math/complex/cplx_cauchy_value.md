---
op: cplx_cauchy_value
dim: math
category: complex
in: cpoints × cpoints
out: cscalar
examples: [math_complex]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# cplx_cauchy_value — MATH `complex` op

- **データ種**: `cpoints × cpoints` → `cscalar`
- **呼び出し**: `import mathops; mathops.cplx_cauchy_value(z, fz, w)` (または `opsmath.get("cplx_cauchy_value")`)

## 使い方

Cauchy's integral formula: recover ``f(w)`` **inside** a contour from its
values **on** the contour.

``f(w) = 1/(2*pi*i*n) ∮ f(zeta)/(zeta - w) dzeta`` where ``n`` is the
winding number of the contour around *w* (Cauchy 1831; the division by
``n`` is what makes a doubly-wound contour give the same answer). Valid
only if ``f`` is holomorphic on and inside the contour — nothing here can
check that, and this is the honest limit of the op: fed values of a
non-holomorphic ``f`` (or of one with a pole inside) it returns the
integral, which is then simply *not* ``f(w)``.

Accuracy inherits the ``O(n^-2)`` chordal quadrature of
:func:`cplx_contour_integral` and degrades as *w* approaches the path
(the integrand's peak sharpens): measured for ``f(z) = z**2`` on a
256-point unit circle, the absolute error is 9.0e-6 at ``w = 0.3`` and
8.1e-5 at ``w = 0.9`` — 9x worse for a point 7x closer to the path
(0.7 -> 0.1 of clearance). The blow-up is real but gradual; what it does
*not* survive is clearance below one sampling step, which is refused.

**Raises** ``ValueError``: *w* outside the contour (winding 0 — the
integral is then 0 and returning it as "f(w)" would be a lie), *w* closer
to the contour than one sampling step (the quadrature is meaningless
there — refine the contour), plus everything
:func:`cplx_winding_number` and :func:`cplx_contour_integral` refuse.

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

## 型が繋がる次の op(`cscalar` を入力に取れる)

—

## 同カテゴリ(`complex`)

[cplx_contour_circle](cplx_contour_circle.md) · [cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md) · [cplx_mobius](cplx_mobius.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
