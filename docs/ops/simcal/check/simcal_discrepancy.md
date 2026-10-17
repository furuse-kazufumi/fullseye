---
op: simcal_discrepancy
dim: simcal
category: check
in: calresult
out: calresult
examples: [poc_pocket_interreflection, poc_simcal_thin_film, simcal_checks_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# simcal_discrepancy — SIMCAL `check` op

- **データ種**: `calresult` → `calresult`
- **呼び出し**: `import fullseye as fs; fs.ledger.simcal_discrepancy(result=None, level=0.99) -> 'dict'` (実装を直接呼ぶなら `import simcalcheck; simcalcheck.simcal_discrepancy(result=None, level=0.99) -> 'dict'`、台帳から引くなら `opssimcal.get("simcal_discrepancy")`)

## 使い方

Is there structure in the noise-normalised residuals that the model cannot produce (model discrepancy)?

The residual of every valid pixel is divided by the noise standard deviation (camera noise
plus the model's own sample variance), so white residuals have unit variance. With three or
more conditions the matrix is conditions x pixels valid in all of them; with fewer it is the
rows x columns of the (first) residual image (a smooth spatial pattern is low-rank there).
``sensitivity.mv_residual_pca`` counts the components whose singular value exceeds the
Tracy-Widom ``level`` point of white noise of that shape (Johnstone 2001; ``level`` in 0.90 /
0.95 / 0.99 — the bare Marchenko-Pastur edge sqrt(n) + sqrt(p) is exceeded by pure noise
10-14 % of the time, measured). Structure found: ``verdict = "structure"``, the loadings as
maps (where the model is wrong), and a warning that every uncertainty of the result is
optimistic — a calibrated knob may be absorbing the missing physics.

## 詳しい使い方ガイド

- [sim_to_real_calibration ファミリ ガイド](../guides/sim_to_real_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pocket_interreflection](../../../../examples/poc_pocket_interreflection.py) — `py -3.11 examples/poc_pocket_interreflection.py`
- [poc_simcal_thin_film](../../../../examples/poc_simcal_thin_film.py) — `py -3.11 examples/poc_simcal_thin_film.py`
- [simcal_checks_tour](../../../../examples/simcal_checks_tour.py) — `py -3.11 examples/simcal_checks_tour.py`

## 型が繋がる次の op(`calresult` を入力に取れる)

[simcal_identifiability](simcal_identifiability.md) · [simcal_uncertainty](simcal_uncertainty.md) · [simcal_validate](simcal_validate.md) · [simcal_report](../report/simcal_report.md)

## 同カテゴリ(`check`)

[simcal_identifiability](simcal_identifiability.md) · [simcal_uncertainty](simcal_uncertainty.md) · [simcal_validate](simcal_validate.md)

---
*Provenance: simcalcheck.py — SIMCAL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
