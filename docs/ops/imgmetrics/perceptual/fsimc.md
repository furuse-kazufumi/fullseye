---
op: fsimc
dim: imgmetrics
category: perceptual
in: rgbimage × rgbimage
out: scalar
examples: [poc_iqa_fsim_gmsd_vif]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# fsimc — IMGMETRICS `perceptual` op

- **データ種**: `rgbimage × rgbimage` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.fsimc(ref, dist, data_range: 'float' = 255.0) -> 'float'` (実装を直接呼ぶなら `import iqafsim; iqafsim.fsimc(ref, dist, data_range: 'float' = 255.0) -> 'float'`、台帳から引くなら `opsimgmetrics.get("fsimc")`)

## 使い方

FSIMc(彩度 I / Q を含む、1 = 同一、**higher is better**)。TID2013 の FSIMc.txt と 4 桁一致するのは色画像(RGB → YIQ full range)を渡したとき
(``iqatid.tid2013_evaluate(root, fsimc, luma="rgb")``、3,000 組 max |差| 5.0e-5)。(H, W) 入力なら FSIM と同じ値。詳細 :func:`fsim_pair`。

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

[fsim](fsim.md) · [fsim_pair](fsim_pair.md) · [gmsd](gmsd.md) · [gmsd_map](gmsd_map.md) · [vifp](vifp.md) · [phase_congruency_pc](phase_congruency_pc.md)

---
*Provenance: iqafsim.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
