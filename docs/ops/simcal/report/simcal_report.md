---
op: simcal_report
dim: simcal
category: report
in: calresult
out: table
examples: [poc_simcal_thin_film, simcal_checks_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# simcal_report — SIMCAL `report` op

- **データ種**: `calresult` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.simcal_report(result=None) -> 'dict'` (実装を直接呼ぶなら `import simcalcheck; simcalcheck.simcal_report(result=None) -> 'dict'`、台帳から引くなら `opssimcal.get("simcal_report")`)

## 使い方

One table of a calibration: each knob's value, unit, interval and class, the gates, and the reasons for refusals.

``rows`` — one dict per knob (``knob``, ``unit``, ``scale``, ``value`` or ``None``, ``std``,
``interval`` from the uncertainty or the profile, ``class`` = ``estimated`` / ``fixed`` /
``undetermined`` with ``reason``); ``combos`` — determined combinations; ``gates`` — every
check that was run with pass/fail; ``errors`` — train / holdout / locked reduced chi^2;
``text`` — the same as plain lines. Reports what is there: a check that was not run is listed
as ``not run``, never as passed.

## 詳しい使い方ガイド

- [sim_to_real_calibration ファミリ ガイド](../guides/sim_to_real_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_simcal_thin_film](../../../../examples/poc_simcal_thin_film.py) — `py -3.11 examples/poc_simcal_thin_film.py`
- [simcal_checks_tour](../../../../examples/simcal_checks_tour.py) — `py -3.11 examples/simcal_checks_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`report`)

—

---
*Provenance: simcalcheck.py — SIMCAL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
