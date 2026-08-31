---
op: cplx_contour_circle
dim: math
category: complex
in: 
out: cpoints
examples: [math_complex]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# cplx_contour_circle — MATH `complex` op

- **データ種**: `` → `cpoints`
- **呼び出し**: `import mathops; mathops.cplx_contour_circle(center=0.0, radius=1.0, n=256, orientation='ccw')` (または `opsmath.get("cplx_contour_circle")`)

## 使い方

Sample a circle as a closed contour — the standard integration path.

Returns ``n`` complex points ``center + radius * exp(±i * 2*pi*k/n)``,
``k = 0..n-1``. The closing segment ``z[-1] -> z[0]`` is **implicit**: the
first point is *not* repeated (every contour op in this family closes the
polygon itself; repeating it would only add a zero-length segment).

*orientation* is explicit because in complex analysis the sign of every
result depends on it: ``'ccw'`` (default) is the positive/mathematical
direction — the one for which the residue theorem, the Cauchy formula and
the argument principle carry a ``+`` sign — and ``'cw'`` negates all three.

Honest limitation: this is a **polygon** through samples of the circle, not
the circle. Its enclosed area is short by a factor ``sinc``-like in
``2*pi/n``, and every quadrature on it converges as ``O(n^-2)``
(:func:`cplx_contour_integral` documents the measured rate).

**Raises** ``ValueError``: non-finite *center*/*radius*, ``radius <= 0``,
``n`` not an integer in ``[3, MAX_CONTOUR_POINTS]`` (a fail-closed size cap
— ``n=10**9`` would allocate 16 GB), unknown *orientation*.

HALCON: no complex-plane operator (``gen_circle_contour_xld`` draws the
same geometry as an XLD contour for image space).

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

## 型が繋がる次の op(`cpoints` を入力に取れる)

[cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md) · [cplx_mobius](cplx_mobius.md)

## 同カテゴリ(`complex`)

[cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md) · [cplx_mobius](cplx_mobius.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
