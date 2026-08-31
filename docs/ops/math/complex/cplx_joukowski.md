---
op: cplx_joukowski
dim: math
category: complex
in: cpoints
out: cpoints
examples: [math_complex]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# cplx_joukowski — MATH `complex` op

- **データ種**: `cpoints` → `cpoints`
- **呼び出し**: `import mathops; mathops.cplx_joukowski(z, c=1.0)` (または `opsmath.get("cplx_joukowski")`)

## 使い方

Joukowski (Zhukovsky) conformal map ``w = z + c^2 / z``.

The classical aerofoil map (Zhukovsky 1910): the circle ``|z| = c`` folds
onto the flat plate ``[-2c, 2c]`` of the real axis (``z = c e^(i t)`` gives
``w = 2c cos t`` — exact, and what the tests pin); a circle of radius
``R > c`` centred at the origin maps to the ellipse with semi-axes
``R + c^2/R`` and ``R - c^2/R``; and a circle through ``z = c`` whose
centre is offset into the second quadrant maps to a cambered aerofoil with
a cusped trailing edge — the reason the map exists.

Conformal (angle-preserving) everywhere except at ``z = ±c``, where the
derivative ``1 - c^2/z^2`` vanishes and angles are **doubled** — that is
what creates the cusp, and it is a property of the map, not a defect.

**Raises** ``ValueError``: a sample at ``z = 0`` (the map's pole), a result
that overflowed (a sample so close to 0 that ``c^2/z`` leaves float64
range), a non-finite or non-positive-real *c*, plus the usual shape and
finiteness contracts.

HALCON: no operator (conformal maps are not part of its transform set).

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

[cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_mobius](cplx_mobius.md)

## 同カテゴリ(`complex`)

[cplx_contour_circle](cplx_contour_circle.md) · [cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_mobius](cplx_mobius.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
