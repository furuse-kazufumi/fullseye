---
op: sem_se_universal_curve
dim: generative
category: sem
in: 
out: signal
examples: [poc_virtual_sem_kv_cd_bse]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# sem_se_universal_curve — GENERATIVE `sem` op

- **データ種**: `なし` → `signal`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.sem_se_universal_curve(e_over_emax=None)` (実装を直接呼ぶなら `import sem; sem.sem_se_universal_curve(e_over_emax=None)`、台帳から引くなら `opsgenerative.get("sem_se_universal_curve")`)

## 使い方

二次電子収率の普遍曲線 δ/δmax = 1.28 (E/Emax)^−0.67 [1 − exp(−1.614 (E/Emax)^1.67)]。

Lin & Joy 2005(Surf. Interface Anal. 37:895)が 44 元素の実測をまとめた形。
最大値は E/Emax ≈ 1 で約 1.0(式の定数のまま。正規化はしない)。``e_over_emax`` を
省くと 0.1〜30 の対数等間隔 64 点で返す(``signal``)。

Examples
--------
>>> round(float(sem_se_universal_curve(1.0)), 3)
1.025

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_virtual_sem_kv_cd_bse](../../../../examples/poc_virtual_sem_kv_cd_bse.py) — `py -3.11 examples/poc_virtual_sem_kv_cd_bse.py`

## 型が繋がる次の op(`signal` を入力に取れる)

—

## 同カテゴリ(`sem`)

[sem_render](sem_render.md) · [sem_electron_mc](sem_electron_mc.md) · [sem_yield_curve](sem_yield_curve.md) · [sem_line_profile](sem_line_profile.md) · [sem_cd_measure](sem_cd_measure.md) · [sem_image](sem_image.md) · [sem_se_escape_fraction](sem_se_escape_fraction.md) · [sem_charging_series](sem_charging_series.md)

---
*Provenance: sem.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
