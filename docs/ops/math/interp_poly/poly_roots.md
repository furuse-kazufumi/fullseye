---
op: poly_roots
dim: math
category: interp_poly
in: signal
out: roots
examples: [math_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# poly_roots — MATH `interp_poly` op

- **データ種**: `signal` → `roots`
- **呼び出し**: `import mathops; mathops.poly_roots(coeffs, real_only=False, imag_tol=1e-09)` (または `opsmath.get("poly_roots")`)

## 使い方

All roots of a polynomial (coefficients highest-power-first) — complex
included.

Roots are the eigenvalues of the companion matrix (``np.roots``); the
polynomial must have degree ≥ 1 and a **non-zero leading coefficient**
(fail-closed: a zero leading coefficient means the stated degree is a lie —
trim it explicitly rather than have it silently dropped).

Returns complex128, sorted by real part then imaginary part
(deterministic). Complex answers are honest answers: ``x² + 1`` really does
have roots ``±i``, and hiding them would misreport the polynomial. Pass
``real_only=True`` to keep only roots whose imaginary part is negligible
(``|imag| <= imag_tol * max(1, |root|)``) and get them back as a sorted
float64 array — possibly **empty**, which is the correct answer for
``x² + 1``.

Numerical note: root-finding conditioning degrades with degree and with
clustered roots (a double root moves ~``sqrt(eps)`` under coefficient
noise — Wilkinson's classic analysis); treat high-degree roots as
approximate. HALCON: no root-finding tuple operator.

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

- [math_metrology](../../../../examples/math_metrology.py) — `py -3.11 examples/math_metrology.py`

## 型が繋がる次の op(`roots` を入力に取れる)

—

## 同カテゴリ(`interp_poly`)

[interp_linear](interp_linear.md) · [interp_cubic](interp_cubic.md) · [poly_fit](poly_fit.md) · [poly_eval](poly_eval.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
