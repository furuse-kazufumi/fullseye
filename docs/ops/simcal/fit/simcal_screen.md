---
op: simcal_screen
dim: simcal
category: fit
in: simmodel
out: table
examples: [poc_simcal_pixel_shift, poc_simcal_telecentric, poc_simcal_thin_film, simcal_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# simcal_screen — SIMCAL `fit` op

- **データ種**: `simmodel` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.simcal_screen(model=None, method='morris', size=8, threshold=10.0, seed=0) -> 'dict'` (実装を直接呼ぶなら `import simcal; simcal.simcal_screen(model=None, method='morris', size=8, threshold=10.0, seed=0) -> 'dict'`、台帳から引くなら `opssimcal.get("simcal_screen")`)

## 使い方

Which knobs move the images above the camera noise, which are confounded, and how many output directions exist.

Runs the model on a screening plan over the free knobs' ranges — Morris trajectories
(``sensitivity.doe_morris``, ``size`` of them, (k+1) runs each) or a Saltelli plan
(``sensitivity.doe_saltelli`` with n = the power of two >= 8 x ``size`` rows, (k+2) n runs) —
and whitens every output by the noise standard deviation at the
initial knobs. The whitened outputs are reduced to principal components and the indices
are computed per component with ``sensitivity.sens_morris`` / ``sens_sobol`` (reused):
Morris ``mu_star_whitened`` = sqrt(sum over components of mu*^2) — roughly how many noise
standard deviations a full-range move of the knob shifts the images; Sobol' ``gsi_st`` =
the variance-weighted total index over components (Lamboni et al. 2011).
``output_dims`` = number of principal directions of the centred whitened runs above the
noise edge (``sensitivity.mv_residual_pca`` with sigma = 1): more free knobs than
output dims means the data cannot fix them all. Local confounding at the initial knobs:
``sensitivity.mv_confounding`` on the whitened Jacobian (gamma_K > ``threshold``).

``class`` per knob: ``no_influence`` (Morris: mu*_whitened < 1.96, i.e. a full-range move is
within noise; Sobol': gsi_st < 0.001), ``combination`` (in a confounded group: only a
combination is determined), else ``determined``. Needs a noise model (refused without).

## 詳しい使い方ガイド

- [sim_to_real_calibration ファミリ ガイド](../guides/sim_to_real_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_simcal_pixel_shift](../../../../examples/poc_simcal_pixel_shift.py) — `py -3.11 examples/poc_simcal_pixel_shift.py`
- [poc_simcal_telecentric](../../../../examples/poc_simcal_telecentric.py) — `py -3.11 examples/poc_simcal_telecentric.py`
- [poc_simcal_thin_film](../../../../examples/poc_simcal_thin_film.py) — `py -3.11 examples/poc_simcal_thin_film.py`
- [simcal_tour](../../../../examples/simcal_tour.py) — `py -3.11 examples/simcal_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`fit`)

[simcal_fit](simcal_fit.md)

---
*Provenance: simcal.py — SIMCAL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
