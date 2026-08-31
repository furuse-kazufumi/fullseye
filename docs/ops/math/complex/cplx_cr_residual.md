---
op: cplx_cr_residual
dim: math
category: complex
in: cimage
out: measurement
examples: [math_complex]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# cplx_cr_residual — MATH `complex` op

- **データ種**: `cimage` → `measurement`
- **呼び出し**: `import mathops; mathops.cplx_cr_residual(f, spacing=1.0)` (または `opsmath.get("cplx_cr_residual")`)

## 使い方

Cauchy-Riemann residual of a sampled complex field — "is this field
holomorphic?" as a number.

With ``f = u + i v`` sampled on a uniform grid, holomorphy means
``u_x = v_y`` and ``u_y = -v_x`` (Cauchy-Riemann). This returns the
**relative** residual ``max(|u_x - v_y|, |u_y + v_x|) / max|grad|``
(central differences, ``numpy.gradient``): ``0`` = the samples satisfy CR to
the discretisation limit, ``2`` = the field is the conjugate of a
holomorphic one (``conj(z)`` gives exactly 2), values in between = partly
analytic or noisy.

**Grid convention (it decides the sign of the answer)**: ``f[i, j]`` is the
field at ``z = x0 + j*spacing + i*spacing*1j`` — rows index the *increasing
imaginary* axis, columns the real axis. Image arrays usually run rows
*downward*; feeding one directly measures the conjugate field, whose
residual is ``2``, not ``0``. Flip rows (``f[::-1]``) to use image data.

Discretisation, honestly: central differences are exact for polynomials of
degree <= 2, so ``f = z**2`` returns exactly 0; for higher order the
residual floors at ``O(h^2 * |f'''|)`` (measured: ``f = z**3`` on a
``[-1,1]^2`` grid returns 1.7e-3 at ``h`` and 4.2e-4 at
``h/2`` — a factor 4.00, the expected second order). Read a
small value as "consistent with holomorphic at this resolution", never as
proof.

A constant field returns ``0.0`` (it is holomorphic; the ``0/0`` of the
normalisation is resolved by that limit, and stated here rather than left
to numpy).

**Raises** ``ValueError``: not a 2-D array, either dimension below 3 (no
central difference exists), non-finite/masked input, over-cap size,
non-finite or non-positive *spacing*.

HALCON: no operator (``derivate_gauss`` supplies the real-valued
derivatives one would build this from).

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

[cplx_contour_circle](cplx_contour_circle.md) · [cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
