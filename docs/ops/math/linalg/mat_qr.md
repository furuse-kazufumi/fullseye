---
op: mat_qr
dim: math
category: linalg
in: matrix
out: table
examples: [numerics_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# mat_qr — MATH `linalg` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mat_qr(a, method='householder')` (実装を直接呼ぶなら `import mathops; mathops.mat_qr(a, method='householder')`、台帳から引くなら `opsmath.get("mat_qr")`)

## 使い方

QR factorisation ``A = Q @ R`` (``Q`` with orthonormal columns, ``R`` upper triangular).

``method``: ``"householder"`` (default, LAPACK ``geqrf``), ``"mgs"`` (modified Gram–Schmidt) or
``"cgs"`` (classical Gram–Schmidt). All three give the same ``Q`` in exact arithmetic; in floating
point the **loss of orthogonality** ``max|QᵀQ − I|`` grows like ε·κ² for CGS, ε·κ for MGS and stays
near ε for Householder (Björck 1967; Giraud et al. 2005) — the reason libraries use Householder.

Returns a dict: ``Q``, ``R``, ``orthogonality_loss``, ``residual`` = max|A − QR| / max|A|,
``cond`` = 2-norm condition number of ``A``.

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

- [numerics_tour](../../../../examples/numerics_tour.py) — `py -3.11 examples/numerics_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md) · [dwt_inverse](../transform/dwt_inverse.md)

## 同カテゴリ(`linalg`)

[mat_solve](mat_solve.md) · [mat_lstsq](mat_lstsq.md) · [mat_svd](mat_svd.md) · [mat_eigh](mat_eigh.md) · [mat_pinv](mat_pinv.md) · [mat_cond](mat_cond.md) · [mat_lu](mat_lu.md) · [mat_cholesky](mat_cholesky.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
