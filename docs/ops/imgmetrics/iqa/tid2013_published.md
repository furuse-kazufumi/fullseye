---
op: tid2013_published
dim: imgmetrics
category: iqa
in: 
out: table
examples: [poc_iqa_fsim_gmsd_vif, poc_iqa_tid2013]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# tid2013_published — IMGMETRICS `iqa` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.tid2013_published() -> 'Dict[str, Tuple[float, float]]'` (実装を直接呼ぶなら `import iqatid; iqatid.tid2013_published() -> 'Dict[str, Tuple[float, float]]'`、台帳から引くなら `opsimgmetrics.get("tid2013_published")`)

## 使い方

公表の順位相関表 {metric: (SROCC, KROCC)}(14 本)。

出典: https://www.ponomarenko.info/tid2013.htm(Last changed 2015-03-23)の「Ranking of compared metrics in accordance with
Spearman / Kendall correlation with MOS」、配布物 readme の TABLE III / IV と同一。鍵は配布物 ``metrics_values/<鍵>.txt`` の
ファイル名(小文字)。**同梱の作者値と mos.txt から、Spearman = 平均順位・Kendall = τ_b で 14 本すべて 3 桁一致**
(|差| ≤ 0.0005 / 0.00044、2026-10-04)。ページ冒頭の「PSNR … is 0.69」と使用例の「FSIMc Full : 0.666」は表と食い違う
(前者は TID2008 の名残、後者は τ_a 0.66626 に一致 —— どちらも推測)ので門には使わない。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_iqa_fsim_gmsd_vif](../../../../examples/poc_iqa_fsim_gmsd_vif.py) — `py -3.11 examples/poc_iqa_fsim_gmsd_vif.py`
- [poc_iqa_tid2013](../../../../examples/poc_iqa_tid2013.py) — `py -3.11 examples/poc_iqa_tid2013.py`

## 型が繋がる次の op(`table` を入力に取れる)

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [tid2013_index](tid2013_index.md) · [tid2013_by_distortion](tid2013_by_distortion.md)

## 同カテゴリ(`iqa`)

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [rank_spearman](rank_spearman.md) · [rank_kendall_b](rank_kendall_b.md) · [tid2013_root](tid2013_root.md) · [tid2013_index](tid2013_index.md) · [tid2013_metric_values](tid2013_metric_values.md) · [tid2013_evaluate](tid2013_evaluate.md)

---
*Provenance: iqatid.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
