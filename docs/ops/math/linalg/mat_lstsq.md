---
op: mat_lstsq
dim: math
category: linalg
in: matrix × signal
out: table
examples: [math_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# mat_lstsq — MATH `linalg` op

- **データ種**: `matrix × signal` → `table`
- **呼び出し**: `import mathops; mathops.mat_lstsq(a, b, rcond=None)` (または `opsmath.get("mat_lstsq")`)

## 使い方

Least-squares solution of an over-determined system ``A x ≈ b``
(LAPACK ``gelsd``, SVD-based).

*a* is ``(m, n)`` with ``m >= n`` (at least as many equations as unknowns;
an under-determined system is refused — its minimum-norm answer is a
different question, ask :func:`mat_pinv`). *b* is ``(m,)`` or ``(m, k)``.
*rcond* is the singular-value cutoff relative to the largest (``None`` =
numpy's machine-precision default); singular values below it are treated
as zero, which is what keeps a noisy rank-deficient fit stable.

Returns a dict — the fit **and** its honesty telemetry together:

``x`` solution ``(n,)`` or ``(n, k)`` · ``residual_ss`` sum of squared
residuals ``||b - A x||²`` (float, or ``(k,)`` per column — computed
explicitly, so it is present even when the matrix is rank-deficient) ·
``rank`` effective rank at *rcond* · ``singular_values`` of *A*
(descending). ``rank < n`` means the data does not determine every
parameter — report that, don't hide it.

HALCON: ``solve_matrix`` on a non-square system (same normal-equation
machinery behind ``vector_to_hom_mat2d`` and friends).

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

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`linalg`)

[mat_solve](mat_solve.md) · [mat_svd](mat_svd.md) · [mat_eigh](mat_eigh.md) · [mat_pinv](mat_pinv.md) · [mat_cond](mat_cond.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
