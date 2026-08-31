---
op: mat_svd
dim: math
category: linalg
in: matrix
out: table
examples: [math_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# mat_svd — MATH `linalg` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import mathops; mathops.mat_svd(a, full_matrices=False)` (または `opsmath.get("mat_svd")`)

## 使い方

Singular value decomposition ``A = U @ diag(s) @ Vt`` (LAPACK ``gesdd``).

Returns ``(U, s, Vt)`` with ``s`` descending and non-negative. With the
default ``full_matrices=False`` the *thin* SVD is returned (``U`` is
``(m, r)``, ``Vt`` is ``(r, n)``, ``r = min(m, n)``) — enough to
reconstruct ``A`` exactly and what every rank/PCA use wants; pass ``True``
for the full orthogonal bases.

**Sign trap (honest)**: each singular-vector pair ``(u_i, v_i)`` is defined
only up to a simultaneous sign flip, and vectors within a *degenerate*
(equal-``s``) block only up to rotation. Assert on ``s``, on
``U diag(s) Vt``, or on projectors — never on raw ``U``/``Vt`` entries.

HALCON: ``svd_matrix``.

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

[mat_solve](mat_solve.md) · [mat_lstsq](mat_lstsq.md) · [mat_eigh](mat_eigh.md) · [mat_pinv](mat_pinv.md) · [mat_cond](mat_cond.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
