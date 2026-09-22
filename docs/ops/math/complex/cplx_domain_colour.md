---
op: cplx_domain_colour
dim: math
category: complex
in: cimage
out: rgbimage
examples: [poc_complex_plane_fields]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# cplx_domain_colour — MATH `complex` op

- **データ種**: `cimage` → `rgbimage`
- **呼び出し**: `import fullseye as fs; fs.ledger.cplx_domain_colour(field, gamma=1.0, bands=0.0, saturation=1.0)` (実装を直接呼ぶなら `import mathops; mathops.cplx_domain_colour(field, gamma=1.0, bands=0.0, saturation=1.0)`、台帳から引くなら `opsmath.get("cplx_domain_colour")`)

## 使い方

Domain colouring: turn a complex field into an RGB image you can read.

Hue carries ``arg(z)`` (one full turn of the colour wheel per turn of the
argument, red at ``arg = 0``); value carries ``|z|`` through the **strictly
increasing** map ``t/(1+t)`` with ``t = |z|**gamma``, so a zero is exactly
black, ``|z| = 1`` is half brightness and a large modulus saturates at full
brightness. The saturation is **not** dropped far from the origin, so the
hue — and with it the argument — stays readable everywhere; pass
``saturation = 0`` for a plain grey ramp of the modulus alone. With
``bands = 0`` (the default) the
brightness is monotone in ``|z|``, which means the picture is *invertible*:
the argument comes back out of the hue and the modulus out of the value.

★**The picture proves a theorem.** Walk a small circle around a zero of
order *m* and the hue cycles through the colour wheel exactly *m* times;
around a pole of order *m*, *m* times the other way. That is the argument
principle, read off the image with no numbers — and this family's
``cplx_winding_number`` counts the same integer from the field itself, so
the drawing and the arithmetic check each other.

Parameters
----------
field : complex 2-D array (``cimage``)
    Typically from :func:`cplx_rational_field`.
gamma : float > 0
    Compresses (``<1``) or stretches (``>1``) the modulus ramp.
bands : float >= 0
    Classic modulus contours: ``bands`` shading cycles per decade of
    ``|z|``. **Non-zero breaks monotonicity** (that is the point — it draws
    level lines), so the inverse-mapping guarantee above holds only at 0.
saturation : float in [0, 1]

**Raises** ``ValueError``: not a 2-D complex array; non-finite samples
(a pole sampled exactly — see :func:`cplx_rational_field`); ``gamma <= 0``;
``bands < 0``; ``saturation`` outside [0, 1].

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

- [poc_complex_plane_fields](../../../../examples/poc_complex_plane_fields.py) — `py -3.11 examples/poc_complex_plane_fields.py`

## 型が繋がる次の op(`rgbimage` を入力に取れる)

—

## 同カテゴリ(`complex`)

[cplx_contour_circle](cplx_contour_circle.md) · [cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
