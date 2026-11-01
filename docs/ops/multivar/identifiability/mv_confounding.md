---
op: mv_confounding
dim: multivar
category: identifiability
in: matrix
out: table
gpu: なし
examples: [poc_simcal_thin_film, sensitivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# mv_confounding — MULTIVAR `identifiability` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mv_confounding(S=None, names=None, threshold=10.0, log_params=False, max_subset=None) -> 'dict'` (実装を直接呼ぶなら `import sensitivity; sensitivity.mv_confounding(S=None, names=None, threshold=10.0, log_params=False, max_subset=None) -> 'dict'`、台帳から引くなら `opsmultivar.get("mv_confounding")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Collinearity index gamma_K (Brun, Reichert & Künsch 2001): which parameters the data can fix.

``S`` is the sensitivity matrix (observations x parameters): column j = the change of
every output per change of parameter j (finite differences of a simulation, or a
Jacobian), ideally already scaled to be dimensionless (Brun: s_ij = dtheta_j / sc_i *
dy_i/dtheta_j). Each column is normalised to unit length, ``s~_j = s_j / ||s_j||``, and for
a parameter subset K

    gamma_K = 1 / sqrt( min eigenvalue of S~_K^T S~_K ).

gamma_K = 1 for orthogonal columns; it grows when a change in one parameter can be
compensated by the others (Brun et al. use 10-15 as the critical range; ``threshold``
defaults to 10). Returned: ``delta_msqr`` (importance, sqrt(mean s_ij^2) on the given
scale), gamma of the full set and of every subset up to ``max_subset`` (all subsets
for <= 14 parameters), the ``confounded_pairs`` (gamma > threshold), the largest
identifiable subsets, the ``undetermined_direction`` of the full set (eigenvector of
the smallest eigenvalue: moving the parameters along it barely changes the output),
and per ``confounded_groups`` entry (the union of the minimal confounded subsets) the
combinations the data ``determined`` (eigenvalue of the group's S~^T S~ >=
1/threshold^2) and those ``undetermined``; parameters in no group are
``determined_individually``.
With ``log_params=True`` (columns are sensitivities to log parameters) the
combinations are written as products of powers — e.g. ``n^1 * d^1`` when only the
product of refractive index and thickness reaches the data. Columns that are all zero
are reported as ``no_influence`` and left out of gamma.

## 詳しい使い方ガイド

- [design_of_experiments ファミリ ガイド](../guides/design_of_experiments.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_simcal_thin_film](../../../../examples/poc_simcal_thin_film.py) — `py -3.11 examples/poc_simcal_thin_film.py`
- [sensitivity_tour](../../../../examples/sensitivity_tour.py) — `py -3.11 examples/sensitivity_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`identifiability`)

[mv_residual_pca](mv_residual_pca.md)

---
*Provenance: sensitivity.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
