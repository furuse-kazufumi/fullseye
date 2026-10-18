---
op: sem_yield_curve
dim: generative
category: sem
in: 
out: table
examples: [poc_virtual_sem_kv_cd_bse]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# sem_yield_curve — GENERATIVE `sem` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.sem_yield_curve(material='SI', energies_kev=None, *, n_electrons: 'int' = 2000, seed: 'int' = 0) -> 'dict'` (実装を直接呼ぶなら `import sem; sem.sem_yield_curve(material='SI', energies_kev=None, *, n_electrons: 'int' = 2000, seed: 'int' = 0) -> 'dict'`、台帳から引くなら `opsgenerative.get("sem_yield_curve")`)

## 使い方

加速電圧を振って η(E) と δ(E) を MC で出し、δ の形を普遍曲線と比べる。

δ の山の位置 Emax は、山の周りの 3 点に log E の放物線を当てて求める。
``universal`` は Lin & Joy 2005 の普遍曲線を、この MC の Emax・δmax で戻した値。
``shape_rms`` は E/Emax ∈ [0.25, 8] の点での δ/δmax と普遍曲線の差の RMS。

Returns
-------
dict
    ``energies_kev`` / ``eta`` / ``se_yield`` / ``emax_kev`` / ``delta_max`` /
    ``universal`` / ``shape_rms`` / ``shape_max_abs``。

Examples
--------
>>> r = sem_yield_curve("SI", [0.2, 0.4, 0.8, 1.6, 3.2], n_electrons=300)
>>> r["emax_kev"] > 0.1 and len(r["se_yield"]) == 5
True

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_virtual_sem_kv_cd_bse](../../../../examples/poc_virtual_sem_kv_cd_bse.py) — `py -3.11 examples/poc_virtual_sem_kv_cd_bse.py`

## 型が繋がる次の op(`table` を入力に取れる)

[perpetual_step](../stream/perpetual_step.md) · [perpetual_render](../stream/perpetual_render.md)

## 同カテゴリ(`sem`)

[sem_render](sem_render.md) · [sem_electron_mc](sem_electron_mc.md) · [sem_se_universal_curve](sem_se_universal_curve.md) · [sem_line_profile](sem_line_profile.md) · [sem_cd_measure](sem_cd_measure.md) · [sem_image](sem_image.md) · [sem_se_escape_fraction](sem_se_escape_fraction.md) · [sem_charging_series](sem_charging_series.md)

---
*Provenance: sem.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
