---
op: mat_lu
dim: math
category: linalg
in: matrix
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# mat_lu — MATH `linalg` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mat_lu(a, pivoting='partial')` (実装を直接呼ぶなら `import mathops; mathops.mat_lu(a, pivoting='partial')`、台帳から引くなら `opsmath.get("mat_lu")`)

## 使い方

LU factorisation ``P @ A = L @ U`` (``L`` unit lower, ``U`` upper).

``pivoting="partial"`` (default, LAPACK ``getrf``) swaps rows so every multiplier is ``|l| <= 1``.
``pivoting="none"`` is plain Gaussian elimination, kept **on purpose** as the classic failure: on
``[[1e-20, 1], [1, 1]]`` the multiplier is 1e20, ``U[1,1]`` rounds to −1e20 and ``L @ U`` loses the
original ``A[1,1] = 1`` entirely (Trefethen & Bau, Lecture 20).

Returns a dict: ``P``, ``L``, ``U``, ``growth`` = max|U| / max|A| (the growth factor; huge growth
means the factorisation is numerically meaningless) and ``residual`` = max|P A − L U| / max|A|.

## ファミリ共通の入力契約(fail-closed)

mathops の全 op は入力を検証してから計算する(黙って通さない):

- **complex 入力は `ValueError`** — float64 への強制変換は虚部を黙って捨てる(numpy は ComplexWarning だけ出して「もっともらしく間違った」実数を返す)。`.real`/`.imag`/`abs()` を明示するか、複素対応の complexops を使う。
- **masked array(masked 要素あり)は `ValueError`** — マスクを剥がして下の生値を使う暗黙変換を拒否。埋める/落とすを明示する。
- **NaN/Inf は全入力で `ValueError`**(件数を明示して拒否 — 結果全体に伝播するため)。
- **形状は厳格**: 1-D と 2-D を暗黙昇格・ブロードキャストしない(vector 枠に matrix、matrix 枠に vector は `ValueError`。reshape を明示する)。
- **サイズ上限**: 行列を取る op と `stat_histogram` の bins は `mathops.MAX_ELEMENTS`(2^26 ≈ 6700 万要素)超で `ValueError`。

## 詳しい使い方ガイド

- [math_metrology ファミリ ガイド](../guides/math_metrology.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md) · [dwt_inverse](../transform/dwt_inverse.md) · [chebyshev_eval_nd](../numerics/chebyshev_eval_nd.md)

## 同カテゴリ(`linalg`)

[mat_solve](mat_solve.md) · [mat_lstsq](mat_lstsq.md) · [mat_svd](mat_svd.md) · [mat_eigh](mat_eigh.md) · [mat_pinv](mat_pinv.md) · [mat_cond](mat_cond.md) · [mat_qr](mat_qr.md) · [mat_cholesky](mat_cholesky.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
