---
op: sem_line_profile
dim: generative
category: sem
in: 
out: table
examples: [poc_virtual_sem_kv_cd_bse]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# sem_line_profile — GENERATIVE `sem` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.sem_line_profile(line_material='PMMA', substrate='SI', energy_kev: 'float' = 1.0, *, width_nm: 'float' = 40.0, height_nm: 'float' = 40.0, sidewall_deg: 'float' = 88.0, beam_sigma_nm: 'float' = 1.0, x_half_range_nm=None, x_step_nm: 'float' = 1.0, electrons_per_point: 'int' = 200, buried=None, seed: 'int' = 0) -> 'dict'` (実装を直接呼ぶなら `import sem; sem.sem_line_profile(line_material='PMMA', substrate='SI', energy_kev: 'float' = 1.0, *, width_nm: 'float' = 40.0, height_nm: 'float' = 40.0, sidewall_deg: 'float' = 88.0, beam_sigma_nm: 'float' = 1.0, x_half_range_nm=None, x_step_nm: 'float' = 1.0, electrons_per_point: 'int' = 200, buried=None, seed: 'int' = 0) -> 'dict'`、台帳から引くなら `opsgenerative.get("sem_line_profile")`)

## 使い方

1 本の線(台形の断面)を横切って電子線を走査した線プロファイルを MC で出す(CD-SEM)。

線は y に一様。底辺の幅 ``width_nm``・高さ ``height_nm``・側壁角 ``sidewall_deg``
(90 = 垂直)の台形で、材料 ``line_material`` が基板 ``substrate`` の上に乗る
(``height_nm = 0`` なら平らな基板)。ビームは幅 ``beam_sigma_nm`` のガウシアン、
位置ごとに ``electrons_per_point`` 個を撃つ。``buried`` は基板に埋もれた矩形の列
``[(材料名, x0, x1, 上端の深さ, 下端の深さ), ...]`` [nm]。

Returns
-------
dict
    ``x_nm`` / 検出器ごとの信号 ``se_total``・``inlens``・``everhart``・``bse``
    (電子 1 個あたり)/ ``eta`` / ``profile``(``pairs``: x と inlens)/
    真の寸法 ``width_bottom_nm``・``width_top_nm``・``width_mid_nm``。

Examples
--------
>>> r = sem_line_profile(energy_kev=1.0, width_nm=30, height_nm=20, x_half_range_nm=30,
...                      x_step_nm=10, electrons_per_point=40)
>>> r["profile"].shape
(7, 2)

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

[sem_render](sem_render.md) · [sem_electron_mc](sem_electron_mc.md) · [sem_se_universal_curve](sem_se_universal_curve.md) · [sem_yield_curve](sem_yield_curve.md) · [sem_cd_measure](sem_cd_measure.md) · [sem_image](sem_image.md) · [sem_se_escape_fraction](sem_se_escape_fraction.md) · [sem_charging_series](sem_charging_series.md)

---
*Provenance: sem.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
