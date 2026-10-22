---
op: simcal_model
dim: simcal
category: model
in: 
out: simmodel
examples: [poc_pocket_interreflection, poc_simcal_pixel_shift, poc_simcal_telecentric, poc_simcal_thin_film, simcal_checks_tour, simcal_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# simcal_model — SIMCAL `model` op

- **データ種**: `なし` → `simmodel`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.simcal_model(chain=None, knobs=None, scene=None, nuisance=None, noise=None, conditions=None, stochastic=None, label='model') -> 'dict'` (実装を直接呼ぶなら `import simcal; simcal.simcal_model(chain=None, knobs=None, scene=None, nuisance=None, noise=None, conditions=None, stochastic=None, label='model') -> 'dict'`、台帳から引くなら `opssimcal.get("simcal_model")`)

## 使い方

Build a ``simmodel``: a forward chain of ops whose arguments are knobs with units, ranges and a noise model.

``chain`` — list of steps ``{"op": name, "args": {...}}``; ``op`` is any registered fullseye
op (e.g. ``"thin_film_reflectance"``) or a built-in stage (``"stage:gain_offset"``,
``"stage:scale"``, ``"stage:radial_cos4"``, ``"stage:radial_poly"``,
``"stage:gaussian_blur"``, ``"stage:as_image"``, ``"stage:mc_sample"``). Step 0 receives
``scene`` as its first argument (or nothing when ``scene`` is ``None``), each later step
the previous output.

``knobs`` — list of dicts ``{"name", "step" (index or op name), "arg", "lo", "hi", "unit",
"scale" ("linear" | "log"), "init", "prior" ((mean, sd) or None), "role" ("gain" |
"offset" | None), "fixed" (value or None)}``. A knob is bound to one argument of one
step; ``init`` defaults to the middle of the range (geometric middle on a log scale).

``conditions`` — optional list of ``{step: {arg: value}}`` (one output image per
condition: exposures, wavelengths, illumination angles). ``nuisance`` — names of knobs
that are fitted but not of interest; ``label`` names the model in reports. ``noise`` / ``stochastic`` — see the module
docstring.

The model is run once at the initial knobs and refused (``ValueError``) when a step is
unknown, a knob names an argument its op does not take, two knobs bind the same
argument, a range is empty or a log range is not positive, or the output is not a finite
2-D array. With no arguments: a demo model (chart -> cos^4 vignetting -> gain/offset, EMVA
noise) **with synthetic observations attached**, ready for :func:`simcal_fit`.

## 詳しい使い方ガイド

- [sim_to_real_calibration ファミリ ガイド](../guides/sim_to_real_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pocket_interreflection](../../../../examples/poc_pocket_interreflection.py) — `py -3.11 examples/poc_pocket_interreflection.py`
- [poc_simcal_pixel_shift](../../../../examples/poc_simcal_pixel_shift.py) — `py -3.11 examples/poc_simcal_pixel_shift.py`
- [poc_simcal_telecentric](../../../../examples/poc_simcal_telecentric.py) — `py -3.11 examples/poc_simcal_telecentric.py`
- [poc_simcal_thin_film](../../../../examples/poc_simcal_thin_film.py) — `py -3.11 examples/poc_simcal_thin_film.py`
- [simcal_checks_tour](../../../../examples/simcal_checks_tour.py) — `py -3.11 examples/simcal_checks_tour.py`
- [simcal_tour](../../../../examples/simcal_tour.py) — `py -3.11 examples/simcal_tour.py`

## 型が繋がる次の op(`simmodel` を入力に取れる)

[simcal_simulate](simcal_simulate.md) · [simcal_observe](simcal_observe.md) · [simcal_screen](../fit/simcal_screen.md) · [simcal_fit](../fit/simcal_fit.md) · [simcal_validate](../check/simcal_validate.md)

## 同カテゴリ(`model`)

[simcal_simulate](simcal_simulate.md) · [simcal_observe](simcal_observe.md)

---
*Provenance: simcal.py — SIMCAL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
