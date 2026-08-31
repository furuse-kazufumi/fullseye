---
op: cplx_winding_number
dim: math
category: complex
in: cpoints
out: measurement
examples: [math_complex]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# cplx_winding_number — MATH `complex` op

- **データ種**: `cpoints` → `measurement`
- **呼び出し**: `import mathops; mathops.cplx_winding_number(z, w=0.0)` (または `opsmath.get("cplx_winding_number")`)

## 使い方

Winding number of a closed contour around a point (turning number).

How many times the polygon ``z`` (closing segment implicit) travels
counter-clockwise around *w*: ``+1`` for a simple positively-oriented loop
containing it, ``-1`` clockwise, ``0`` outside, ``±k`` for a ``k``-fold
loop. Computed as the sum of the principal-value argument increments of
``z_k - w`` divided by ``2*pi`` and rounded — for a *polygon* that sum is an
exact multiple of ``2*pi``, so the result is an exact integer, not an
estimate (the rounding merely removes ~1e-14 of accumulated float error).

Honest limitation — **the count can alias low, and no local check can stop
it**: this is the winding number of the polygon *through the samples*,
which equals that of the underlying curve only if the sampling resolves it.
A segment that turns the ray to *w* by ``>= pi`` is ambiguous (which side
did it pass?) and raises. Below that there is no contradiction to detect:
``z**5`` sampled on a 4-point circle turns exactly ``pi/2`` per step and
counts **1** instead of 5 (measured). From ``pi/2`` up, a
``RuntimeWarning`` says so (``WIND_ALIAS_WARN``); the only real remedy is
the classical one — refine until the count stops changing.

**Raises** ``ValueError``: *w* coincides with a vertex or lies on a segment
(the winding number is undefined on the contour), a segment subtends
``>= pi`` as seen from *w* (undersampled — refine the contour), fewer than
3 points, degenerate contour, non-finite/masked input.

HALCON: no operator (``test_region_point`` answers the related but weaker
inside/outside question for regions).

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

[cplx_contour_circle](cplx_contour_circle.md) · [cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md) · [cplx_mobius](cplx_mobius.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
