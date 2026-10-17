---
op: simcal_observe
dim: simcal
category: model
in: simmodel × images
out: simmodel
examples: [poc_pocket_interreflection, simcal_checks_tour, simcal_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# simcal_observe — SIMCAL `model` op

- **データ種**: `simmodel × images` → `simmodel`
- **呼び出し**: `import fullseye as fs; fs.ledger.simcal_observe(model=None, images=None, roi=None, align=False, exposure=None, max_shift=8, split='train') -> 'dict'` (実装を直接呼ぶなら `import simcal; simcal.simcal_observe(model=None, images=None, roi=None, align=False, exposure=None, max_shift=8, split='train') -> 'dict'`、台帳から引くなら `opssimcal.get("simcal_observe")`)

## 使い方

Attach measured images to a simmodel: alignment, region of interest and exposure normalisation.

``images`` — one 2-D array per condition (shape = what the model outputs). ``align=True``
registers each image to the simulation at the initial knobs by phase correlation
(``filters_freq.phase_correlation_fft``, integer pixels), shifts it back and masks the
wrapped border; a shift larger than ``max_shift`` is refused. ``roi`` = boolean mask or
``(row0, row1, col0, col1)``. ``exposure`` = a factor per image to divide by (the noise
variance is divided by its square) — **refused when the model has a free gain knob**: the
two scale the same signal. ``split`` labels the data ``train`` / ``holdout`` / ``locked``
(the TRAIN / OBSERVED / LOCKED discipline of ``robust.py``). Returns a new simmodel with
``observed`` filled (the input is not modified), including ``data_range``.

## 詳しい使い方ガイド

- [sim_to_real_calibration ファミリ ガイド](../guides/sim_to_real_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pocket_interreflection](../../../../examples/poc_pocket_interreflection.py) — `py -3.11 examples/poc_pocket_interreflection.py`
- [simcal_checks_tour](../../../../examples/simcal_checks_tour.py) — `py -3.11 examples/simcal_checks_tour.py`
- [simcal_tour](../../../../examples/simcal_tour.py) — `py -3.11 examples/simcal_tour.py`

## 型が繋がる次の op(`simmodel` を入力に取れる)

[simcal_simulate](simcal_simulate.md) · [simcal_screen](../fit/simcal_screen.md) · [simcal_fit](../fit/simcal_fit.md) · [simcal_validate](../check/simcal_validate.md)

## 同カテゴリ(`model`)

[simcal_model](simcal_model.md) · [simcal_simulate](simcal_simulate.md)

---
*Provenance: simcal.py — SIMCAL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
