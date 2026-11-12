---
op: acceptance_error_budget
dim: acceptance
category: budget
in: table × table × table
out: table
gpu: なし
examples: [poc_virtual_acceptance_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# acceptance_error_budget — ACCEPTANCE `budget` op

- **データ種**: `table × table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.acceptance_error_budget(sensor, factors, mpe, layout=None, exclude_fraction=0.003, n_repeat=1, seed=0)` (実装を直接呼ぶなら `import acceptance3d; acceptance3d.acceptance_error_budget(sensor, factors, mpe, layout=None, exclude_fraction=0.003, n_repeat=1, seed=0)`、台帳から引くなら `opsacceptance.get("acceptance_error_budget")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

誤差の要因を 1 つずつ入れて仮想受入試験を回し、どの要因が合否を決めるかを返す(``table``)。

One-factor-at-a-time error budget of the virtual acceptance test. The baseline is ``sensor`` with every
error source switched off (noise off, calibration errors 0, range scale 1, multipath 0, supersample 1).
``factors`` maps a name to the sensor keys that switch that factor on, e.g.
``{"noise": {"noise": True}, "fx 0.2 %": {"fx_rel_error": 0.002}, "multipath": {"multipath_amplitude": 0.05}}``.
Each factor is run alone on the baseline, then all together ("all"). With noise, ``n_repeat`` seeds are
run and the worst of the per-run maxima is kept (the verdict must hold for every run).

返す ``dict``: ``baseline``・``all``・``factors``(名前ごとに ``pf``・``ps``・``sd``・``f`` の最悪値と
``verdict``)、``decisive``(単独で MPE を超えた要因の名前、比の大きい順)、``ranking``(全要因の比の大きい順と
その量)、``interaction``(「all」の比 − 単独の比の最大。正なら要因が重なって初めて落ちる)。
基準(全部切った)の評価量は解析解の往復だけなので ≈ 0 になる(門で確かめる)。

**Raises** ``ValueError``: ``factors`` が空・dict でない、未知のセンサの鍵、``n_repeat`` が 1〜50 の外、
``mpe`` が不正(:func:`acceptance_verdict`)。

## 詳しい使い方ガイド

- [optical_3d_acceptance ファミリ ガイド](../guides/optical_3d_acceptance.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_virtual_acceptance_3d](../../../../examples/poc_virtual_acceptance_3d.py) — `py -3.11 examples/poc_virtual_acceptance_3d.py`

## 型が繋がる次の op(`table` を入力に取れる)

[acceptance_verdict](../evaluate/acceptance_verdict.md) · [acceptance_scan](../simulate/acceptance_scan.md) · [virtual_acceptance_test](../simulate/virtual_acceptance_test.md)

## 同カテゴリ(`budget`)

—

---
*Provenance: acceptance3d.py — ACCEPTANCE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
