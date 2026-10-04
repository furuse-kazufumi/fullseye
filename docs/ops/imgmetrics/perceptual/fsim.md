---
op: fsim
dim: imgmetrics
category: perceptual
in: image2d × image2d
out: scalar
examples: [poc_iqa_fsim_gmsd_vif]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# fsim — IMGMETRICS `perceptual` op

- **データ種**: `image2d × image2d` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.fsim(ref, dist, data_range: 'float' = 255.0) -> 'float'` (実装を直接呼ぶなら `import iqafsim; iqafsim.fsim(ref, dist, data_range: 'float' = 255.0) -> 'float'`、台帳から引くなら `opsimgmetrics.get("fsim")`)

## 使い方

FSIM(輝度のみ、1 = 同一、**higher is better**)。TID2013 の FSIM.txt と 4 桁一致するのは **Y′ limited の灰色画像**を渡したとき
(``iqatid.tid2013_evaluate(root, fsim, luma="limited_u8")``、3,000 組 max |差| 5.0e-5)。詳細 :func:`fsim_pair`。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_iqa_fsim_gmsd_vif](../../../../examples/poc_iqa_fsim_gmsd_vif.py) — `py -3.11 examples/poc_iqa_fsim_gmsd_vif.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[luma_limited_u8](../iqa/luma_limited_u8.md) · [rank_data](../iqa/rank_data.md) · [tid2013_index](../iqa/tid2013_index.md)

## 同カテゴリ(`perceptual`)

[fsimc](fsimc.md) · [fsim_pair](fsim_pair.md) · [gmsd](gmsd.md) · [gmsd_map](gmsd_map.md) · [vifp](vifp.md) · [phase_congruency_pc](phase_congruency_pc.md)

---
*Provenance: iqafsim.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
