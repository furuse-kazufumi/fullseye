---
op: cplx_rational_field
dim: math
category: complex
in: roots × roots
out: cimage
examples: [poc_complex_plane_fields]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# cplx_rational_field — MATH `complex` op

- **データ種**: `roots × roots` → `cimage`
- **呼び出し**: `import fullseye as fs; fs.ledger.cplx_rational_field(zeros, poles, gain=1.0, centre=0j, half_width=2.0, shape=(256, 256))` (実装を直接呼ぶなら `import mathops; mathops.cplx_rational_field(zeros, poles, gain=1.0, centre=0j, half_width=2.0, shape=(256, 256))`、台帳から引くなら `opsmath.get("cplx_rational_field")`)

## 使い方

Sample a rational function ``R(z) = gain * prod(z - zeros) / prod(z - poles)``.

Returns the complex image ``R(z)`` over a rectangular window of the plane —
the *area* counterpart of this family's contour operators. The product is
formed in log space (``exp(sum(log(z - zk)) - sum(log(z - pm)))``) so a
degree-30 numerator does not overflow before the denominator can divide it
back down; the branch cuts of the individual logarithms cancel in the
exponential, so the result is the ordinary principal value of the quotient,
not a branch of it.

★**Why this earns its place**: the field is not decoration. The argument
principle says that the winding number of ``R`` along a closed contour
equals *(zeros inside) - (poles inside)*, counted with multiplicity — so
this family's own ``cplx_argument_principle`` / ``cplx_winding_number``
are an independent oracle for every field this operator produces, and
:func:`cplx_domain_colour` makes that integer **visible** as the number of
times the hue cycles.

Parameters
----------
zeros, poles : complex array-like
    Roots of the numerator and denominator, repeated for multiplicity.
    Either may be empty (a polynomial, or ``1/q``). ``poly_roots`` produces
    exactly this ``roots`` vocabulary.
gain : complex
    Leading coefficient.
centre, half_width, shape :
    The window, as in :func:`cplx_plane_grid`.

**Raises** ``ValueError``: a pole (or zero) lands *exactly* on a sample, so
the value there is not a number — nudge ``centre`` by half a pixel or take
an odd ``shape`` (the message says which pole and where); non-finite input;
the window is degenerate; the result overflows to infinity anyway (the gain
and the window disagree by more than float64 can hold).

HALCON: no operator (HALCON has no complex-plane family).

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

- [poc_complex_plane_fields](../../../../examples/poc_complex_plane_fields.py) — `py -3.11 examples/poc_complex_plane_fields.py`

## 型が繋がる次の op(`cimage` を入力に取れる)

[cplx_cr_residual](cplx_cr_residual.md) · [cplx_domain_colour](cplx_domain_colour.md) · [mandelbrot_interior](mandelbrot_interior.md)

## 同カテゴリ(`complex`)

[cplx_contour_circle](cplx_contour_circle.md) · [cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
