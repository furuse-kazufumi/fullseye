---
op: cplx_laurent_coeffs
dim: math
category: complex
in: cpoints × cpoints
out: table
examples: [math_complex]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# cplx_laurent_coeffs — MATH `complex` op

- **データ種**: `cpoints × cpoints` → `table`
- **呼び出し**: `import mathops; mathops.cplx_laurent_coeffs(z, fz, kmin=-1, kmax=4)` (または `opsmath.get("cplx_laurent_coeffs")`)

## 使い方

Laurent (and Taylor) coefficients on a **uniformly sampled circle** —
residues included.

For ``f`` holomorphic on an annulus around ``c``,
``f(z) = sum_k c_k (z - c)^k`` with
``c_k = 1/(2*pi*i) ∮ f(zeta)/(zeta - c)^(k+1) dzeta``. On a circle of
radius ``r`` sampled at ``n`` equally spaced angles this becomes a discrete
Fourier sum, ``c_k = (1/(n r^k)) sum_j f_j exp(-i k theta_j)`` — the
trapezoidal rule in the angle, where it converges **geometrically** rather
than as ``O(n^-2)`` (Trefethen & Weideman 2014, "The exponentially
convergent trapezoidal rule").

``c_-1`` **is the residue** at ``c`` (when ``c`` is the only singularity
inside), ``c_k`` for ``k >= 0`` are the Taylor coefficients
``f^(k)(c)/k!``, and a non-zero ``c_-m`` for ``m > 1`` reveals a pole of
order ``m``. Measured on the unit circle with ``f = 1/(z - 0.5)``,
``n = 64``: ``c_-1 = 1`` and ``c_-2 = 0.5`` to 1e-16 (machine precision).

Returns a dict: ``k`` (int64 orders, ``kmin..kmax``) · ``c`` (complex128
coefficients) · ``center`` · ``radius``. The centre is the sample mean,
which is exact for a uniformly sampled circle.

**Orientation, and how it differs from the rest of the family**: the sum
runs over the sample *set*, not the sample *order*, so this op always
returns the coefficients of the positively oriented circle — the standard
definition — whatever order the points arrive in. Feed a clockwise circle
and ``c_-1`` still comes back ``+`` the residue, while
``cplx_contour_integral / (2*pi*i)`` on the same points returns ``-`` it
(verified). Both are right; they answer different questions (the intrinsic
coefficient vs the integral along *this* traversal). Do not cross-check one
against the other without fixing the orientation first.

Honest limitation — **aliasing**: the discrete sum cannot distinguish
``c_k`` from ``c_{k+n}``, so a coefficient carries the alias sum
``sum_m c_{k+m n} r^{m n}``. That is negligible for a rapidly converging
series (the ``0.5^64`` term above) and ruinous near the annulus boundary.
Requesting more than ``n`` coefficients is refused for the same reason.

**Raises** ``ValueError``: the samples are not a uniformly spaced circle
(unequal radii or unequal angular gaps beyond ``1e-8`` relative — this op
is *not* valid on an arbitrary contour, and silently pretending otherwise
would return numbers that mean nothing), ``kmin > kmax``, more than ``n``
coefficients requested, non-integer orders, and a coefficient that
overflowed (``r^-k`` for a small radius and a large negative order).

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

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`complex`)

[cplx_contour_circle](cplx_contour_circle.md) · [cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_joukowski](cplx_joukowski.md) · [cplx_mobius](cplx_mobius.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
