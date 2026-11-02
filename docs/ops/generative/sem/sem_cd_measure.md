---
op: sem_cd_measure
dim: generative
category: sem
in: pairs
out: table
gpu: なし
examples: [poc_virtual_sem_kv_cd_bse]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# sem_cd_measure — GENERATIVE `sem` op

- **データ種**: `pairs` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sem_cd_measure(profile, *, method: 'str' = 'threshold', threshold: 'float' = 0.5, smooth_nm: 'float' = 0.0) -> 'dict'` (実装を直接呼ぶなら `import sem; sem.sem_cd_measure(profile, *, method: 'str' = 'threshold', threshold: 'float' = 0.5, smooth_nm: 'float' = 0.0) -> 'dict'`、台帳から引くなら `opsgenerative.get("sem_cd_measure")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

線プロファイル(``pairs``: x と信号)から線幅を出す(CD-SEM の 2 方式)。

1 本の線の左右の縁は、それぞれ明るい山(縁の効果)になる。各山の**外側の斜面**で:

  * ``threshold``: 外側の地の水準 b と山の高さ p の間の ``b + t·(p − b)`` を横切る位置
    (線形補間)。t = ``threshold``(既定 0.5 = 50 % しきい値)。
  * ``max_slope``: 外側の斜面で勾配の絶対値が最大になる位置(3 点放物線で詰める)。

地の水準は両端それぞれ外側 10 % の中央値。``smooth_nm > 0`` なら先にガウシアンで均す。

Returns
-------
dict
    ``width_nm`` / ``left_nm`` / ``right_nm`` / ``method`` / ``threshold`` /
    ``peak_left_nm`` / ``peak_right_nm``。

Examples
--------
>>> import numpy as np
>>> x = np.arange(-50.0, 51.0)
>>> y = 0.2 + np.exp(-0.5 * ((x + 20) / 3) ** 2) + np.exp(-0.5 * ((x - 20) / 3) ** 2)
>>> r = sem_cd_measure(np.stack([x, y], axis=1), method="threshold", threshold=0.5)
>>> bool(abs(r["width_nm"] - 2 * (20 + 3 * np.sqrt(2 * np.log(2)))) < 0.2)
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

[sem_render](sem_render.md) · [sem_electron_mc](sem_electron_mc.md) · [sem_se_universal_curve](sem_se_universal_curve.md) · [sem_yield_curve](sem_yield_curve.md) · [sem_line_profile](sem_line_profile.md) · [sem_image](sem_image.md) · [sem_se_escape_fraction](sem_se_escape_fraction.md) · [sem_charging_series](sem_charging_series.md)

---
*Provenance: sem.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
