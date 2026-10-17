---
op: simcal_simulate
dim: simcal
category: model
in: simmodel
out: images
examples: [poc_simcal_thin_film, simcal_checks_tour, simcal_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# simcal_simulate — SIMCAL `model` op

- **データ種**: `simmodel` → `images`
- **呼び出し**: `import fullseye as fs; fs.ledger.simcal_simulate(model=None, theta=None, seed=None) -> 'list'` (実装を直接呼ぶなら `import simcal; simcal.simcal_simulate(model=None, theta=None, seed=None) -> 'list'`、台帳から引くなら `opssimcal.get("simcal_simulate")`)

## 使い方

Run a simmodel's chain at given knob values -> one 2-D array per condition (``images``).

``theta`` is ``{knob: value}`` in natural units (missing knobs take their initial or fixed
value; a ``calresult`` is accepted and its ``theta_hat`` used). Values outside a knob's
range are allowed here (a simulation is not a fit). ``seed`` overrides the common-random-
number seed of a stochastic model (``None`` = the model's own). Refuses an unknown knob
name or a non-finite output.

## 詳しい使い方ガイド

- [sim_to_real_calibration ファミリ ガイド](../guides/sim_to_real_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_simcal_thin_film](../../../../examples/poc_simcal_thin_film.py) — `py -3.11 examples/poc_simcal_thin_film.py`
- [simcal_checks_tour](../../../../examples/simcal_checks_tour.py) — `py -3.11 examples/simcal_checks_tour.py`
- [simcal_tour](../../../../examples/simcal_tour.py) — `py -3.11 examples/simcal_tour.py`

## 型が繋がる次の op(`images` を入力に取れる)

[simcal_observe](simcal_observe.md)

## 同カテゴリ(`model`)

[simcal_model](simcal_model.md) · [simcal_observe](simcal_observe.md)

---
*Provenance: simcal.py — SIMCAL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
