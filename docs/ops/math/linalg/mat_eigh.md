---
op: mat_eigh
dim: math
category: linalg
in: matrix
out: table
examples: [math_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# mat_eigh — MATH `linalg` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import mathops; mathops.mat_eigh(a)` (または `opsmath.get("mat_eigh")`)

## 使い方

Eigen-decomposition of a **symmetric** matrix (LAPACK ``syevd``).

    Returns ``(w, V)``: eigenvalues ``w`` in **ascending** order (all real —
    guaranteed by symmetry) and orthonormal eigenvectors as the **columns** of
    ``V`` (``A @ V[:, i] == w[i] * V[:, i]``).

    **Symmetric input only, verified**: ``max|A - A.T|`` above ``1e-10`` of the
    matrix scale raises ``ValueError``. This is deliberate fail-closing of two
    traps at once — a symmetric solver fed a non-symmetric matrix silently
    reads one triangle and returns a *plausible wrong* answer, and a general
    matrix has complex eigenvalues this real-valued API cannot even represent.
    For a covariance / Hessian / Gram matrix (the metrology cases) symmetry
    holds by construction; symmetrise explicitly (``(A + A.T) / 2``) if yours
    is symmetric-up-to-noise.

    **Sign trap (honest)**: each eigenvector is defined only up to sign, and
    eigenvectors of a *repeated* eigenvalue only up to rotation in that
    subspace. Compare ``|v·w|`` or subspaces, never raw columns.

    HALCON: ``eigenvalues_symmetric_matrix``.

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

[mat_solve](mat_solve.md) · [mat_lstsq](mat_lstsq.md) · [mat_svd](mat_svd.md) · [mat_pinv](mat_pinv.md) · [mat_cond](mat_cond.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
