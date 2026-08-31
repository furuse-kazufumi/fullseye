---
op: cplx_mobius
dim: math
category: complex
in: cpoints
out: cpoints
examples: [math_complex]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# cplx_mobius — MATH `complex` op

- **データ種**: `cpoints` → `cpoints`
- **呼び出し**: `import mathops; mathops.cplx_mobius(z, a, b, c, d)` (または `opsmath.get("cplx_mobius")`)

## 使い方

Möbius (linear fractional) map ``w = (a z + b) / (c z + d)``.

The automorphisms of the Riemann sphere: every Möbius map is conformal and
sends circles-and-lines to circles-and-lines. Two standard cases the tests
pin: the Cayley transform ``(z - i)/(z + i)`` maps the real axis onto the
unit circle (``|w| = 1``) and ``i`` to ``0``; the inversion ``1/z`` maps the
unit circle onto itself.

The determinant ``a d - b c`` must not vanish — that degenerate case is not
a map but a constant (every point collapses to ``a/c``), which is refused
rather than returned as a suspiciously uniform answer.

**Raises** ``ValueError``: ``|a d - b c|`` below ``1e-12`` of the
coefficient scale (degenerate/constant map), a sample **at** the pole
``z = -d/c`` (the image is the point at infinity, which float64 cannot
represent), an overflowed result (a sample microscopically close to that
pole), plus the usual shape and finiteness contracts.

HALCON: no operator (``projective_trans_point_2d`` is the real-plane
projective analogue).

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

[cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md)

## 同カテゴリ(`complex`)

[cplx_contour_circle](cplx_contour_circle.md) · [cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
