---
op: mv_pca
dim: multivar
category: analysis
in: matrix
out: table
examples: [multivar_inspection_tour, poc_simcal_thin_film]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# mv_pca — MULTIVAR `analysis` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mv_pca(X=None, standardize=True, n_components=None, threshold=0.9, n_parallel=200, parallel_stat='mean', seed=0, memory_budget=None) -> 'dict'` (実装を直接呼ぶなら `import multivar; multivar.mv_pca(X=None, standardize=True, n_components=None, threshold=0.9, n_parallel=200, parallel_stat='mean', seed=0, memory_budget=None) -> 'dict'`、台帳から引くなら `opsmultivar.get("mv_pca")`)

## 使い方

Principal components of a table (samples x variables) and how many of them the data support.

PCA is the SVD of the centred (by default also unit-variance) matrix
``Xc = U S V^T``: scores ``U S``, loadings ``V``, eigenvalues ``S^2/(n-1)`` (the
covariance or correlation eigenvalues — the tests check this identity).

The number of components is reported three ways, because each fails differently:

* ``cumulative`` — the smallest count reaching ``threshold`` of the variance (a
  convention, not a test: with many noisy columns it keeps noise);
* ``parallel`` — Horn's parallel analysis (Horn 1965): keep component i while its
  eigenvalue exceeds the ``parallel_stat`` (``"mean"`` as in Horn, or ``"p95"``) of
  the i-th eigenvalue of ``n_parallel`` normal random tables of the same shape
  treated the same way;
* ``mdl`` — the MDL criterion of Wax & Kailath 1985 (``mathspectral.n_sources_mdl``,
  reused) on the centred data; it assumes white noise of equal variance in every
  column, which standardising breaks, so it is computed only with
  ``standardize=False`` (homogeneous columns: pixels, features in one unit) and is
  ``None`` otherwise.

``n_components`` fixes how many scores/loadings to return (default: the parallel
count, at least 1). Accepts a matrix or a ``feat_image_vector`` table.

## 詳しい使い方ガイド

- [design_of_experiments ファミリ ガイド](../guides/design_of_experiments.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [multivar_inspection_tour](../../../../examples/multivar_inspection_tour.py) — `py -3.11 examples/multivar_inspection_tour.py`
- [poc_simcal_thin_film](../../../../examples/poc_simcal_thin_film.py) — `py -3.11 examples/poc_simcal_thin_film.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`analysis`)

[mv_pls](mv_pls.md) · [rsm_fit](rsm_fit.md) · [doe_main_effects](doe_main_effects.md)

---
*Provenance: multivar.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
