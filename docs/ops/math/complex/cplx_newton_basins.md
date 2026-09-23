---
op: cplx_newton_basins
dim: math
category: complex
in: signal
out: labels2d
examples: [poc_complex_plane_fields]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# cplx_newton_basins — MATH `complex` op

- **データ種**: `signal` → `labels2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.cplx_newton_basins(coeffs, centre=0j, half_width=2.0, shape=(256, 256), max_iter=64, tol=1e-10)` (実装を直接呼ぶなら `import mathops; mathops.cplx_newton_basins(coeffs, centre=0j, half_width=2.0, shape=(256, 256), max_iter=64, tol=1e-10)`、台帳から引くなら `opsmath.get("cplx_newton_basins")`)

## 使い方

Which root of a polynomial does Newton's method fall into, from each point?

Labels the window ``1..len(roots)`` by the root reached, and ``0`` where the
iteration has not converged within ``max_iter`` (the Julia set and its
neighbourhood). Roots come from ``numpy.roots`` — the same routine behind
this family's ``poly_roots`` — and are sorted by ``(Re, Im)`` so the label
of a given root does not change between runs.

★**Degree 2 has a closed-form answer, so the operator can be checked
exactly rather than plausibly.** Cayley (1879): for ``z**2 - 1`` the basins
are the two open half-planes ``Re z > 0`` and ``Re z < 0``, and the boundary
is the imaginary axis — no fractal. The famous fractal boundary appears at
degree 3, which Cayley could not settle; there the honest checks are
structural (every root's basin is non-empty; ``z**3 - 1`` is invariant under
rotation by ``2*pi/3``, and so is its labelling, up to the cyclic
relabelling of the roots).

``coeffs`` is highest-degree-first, as ``numpy.roots`` and ``poly_roots``
take it.

**Raises** ``ValueError``: text, non-finite or all-zero coefficients; a
non-zero constant (no roots); ``max_iter < 1``; ``tol <= 0``; degenerate
window. Points where the derivative vanishes are left unconverged (label
``0``) rather than divided by — a critical point is genuinely undecided.

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

## 型が繋がる次の op(`labels2d` を入力に取れる)

—

## 同カテゴリ(`complex`)

[cplx_contour_circle](cplx_contour_circle.md) · [cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
