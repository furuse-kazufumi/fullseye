---
op: mat_cond
dim: math
category: linalg
in: matrix
out: measurement
examples: [math_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# mat_cond — MATH `linalg` op

- **データ種**: `matrix` → `measurement`
- **呼び出し**: `import mathops; mathops.mat_cond(a)` (または `opsmath.get("mat_cond")`)

## 使い方

Spectral (2-norm) condition number ``s_max / s_min`` — the numerical
canary of the whole linalg family.

``cond == 1`` for an orthogonal/orthonormal matrix (the best possible);
``inf`` (returned, not raised — the question "how conditioned is it?" has
that honest answer) for an exactly singular one. A solve against *A* loses
roughly ``log10(cond(A))`` significant digits (Golub & Van Loan §2.6):

  * ``cond ~ 1e3``  — comfortable, ~13 digits survive.
  * ``cond ~ 1e8``  — half the digits are gone; residuals may still look
    small while parameters are off.
  * ``cond > 1e12`` — **do not trust** :func:`mat_solve` here: at best ~3
    digits remain. Rescale/centre the problem, or switch to
    :func:`mat_lstsq` / :func:`mat_pinv` with an honest ``rcond``.

Defined for any rectangular ``(m, n)`` matrix (via its singular values).
HALCON: no direct operator (combine ``norm_matrix`` of *A* and of its
inverse).

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

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`linalg`)

[mat_solve](mat_solve.md) · [mat_lstsq](mat_lstsq.md) · [mat_svd](mat_svd.md) · [mat_eigh](mat_eigh.md) · [mat_pinv](mat_pinv.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
