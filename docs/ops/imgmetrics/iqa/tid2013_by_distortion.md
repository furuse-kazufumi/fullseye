---
op: tid2013_by_distortion
dim: imgmetrics
category: iqa
in: any × table
out: table
examples: [poc_iqa_fsim_gmsd_vif, poc_iqa_tid2013]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# tid2013_by_distortion — IMGMETRICS `iqa` op

- **データ種**: `any × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tid2013_by_distortion(values, index: 'dict', idx=None) -> 'List[dict]'` (実装を直接呼ぶなら `import iqatid; iqatid.tid2013_by_distortion(values, index: 'dict', idx=None) -> 'List[dict]'`、台帳から引くなら `opsimgmetrics.get("tid2013_by_distortion")`)

## 使い方

歪み種(24)ごとの、指標と MOS の順位相関。

``values`` は ``idx``(台帳の行番号、省略 = 3000 行全部)に対応する値。各行: ``type``(1 始まり)、``name``(readme TABLE I)、
``n``、``n_inf``、``srocc``、``krocc``(τ_b)。1 種 = 25 参照 × 5 段 = 125 組。組が 2 未満の種は nan。歪み 18(彩度変化)は
Y′ の PSNR が 106 / 125 組で inf(同順位)なので、その種の順位相関は低く出る —— 指標の欠陥でなく輝度だけを見る指標の限界。
**Raises** ``ValueError``: 長さ不一致・nan。

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

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [tid2013_index](tid2013_index.md)

## 同カテゴリ(`iqa`)

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [rank_spearman](rank_spearman.md) · [rank_kendall_b](rank_kendall_b.md) · [tid2013_published](tid2013_published.md) · [tid2013_root](tid2013_root.md) · [tid2013_index](tid2013_index.md) · [tid2013_metric_values](tid2013_metric_values.md)

---
*Provenance: iqatid.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
