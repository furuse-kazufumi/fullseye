---
op: mv_residual_pca
dim: multivar
category: identifiability
in: matrix
out: table
examples: [sensitivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# mv_residual_pca — MULTIVAR `identifiability` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mv_residual_pca(R=None, noise_sigma=None, n_perm=100, seed=0) -> 'dict'` (実装を直接呼ぶなら `import sensitivity; sensitivity.mv_residual_pca(R=None, noise_sigma=None, n_perm=100, seed=0) -> 'dict'`、台帳から引くなら `opsmultivar.get("mv_residual_pca")`)

## 使い方

Do the residuals of a fitted model still carry structure? PCA of a residual matrix vs. noise.

``R`` is (observations x variables) — e.g. one row per image, one column per pixel or
feature, holding measured minus simulated. It is **not** centred: a bias common to
every observation is itself a structure the model lacks.

A component counts as structural when its singular value exceeds the noise edge:

* with ``noise_sigma`` (e.g. the temporal noise from an EMVA 1288 characterisation):
  the largest singular value of an n x p matrix of i.i.d. noise is about
  sigma (sqrt(n) + sqrt(p)) (Marchenko-Pastur edge), used as the threshold;
* without it: permutation parallel analysis (Buja & Eyuboglu 1992) — each column is
  shuffled independently ``n_perm`` times, which keeps every column's distribution
  but destroys structure shared across columns, and component i must beat the 95th
  percentile of the shuffled i-th singular values. (It cannot see a structure that
  lives inside single columns, e.g. a constant bias column — use ``noise_sigma``
  for that.)

Returns the singular values, the threshold(s), ``n_structural``, the share of the
residual energy in the structural components, and their loadings (reshape a loading
to the image shape to see *where* the model is wrong) and scores.

## 詳しい使い方ガイド

- [design_of_experiments ファミリ ガイド](../guides/design_of_experiments.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sensitivity_tour](../../../../examples/sensitivity_tour.py) — `py -3.11 examples/sensitivity_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`identifiability`)

[mv_confounding](mv_confounding.md)

---
*Provenance: sensitivity.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
