---
op: gmsd
dim: imgmetrics
category: perceptual
in: image2d × image2d
out: scalar
examples: [poc_iqa_fsim_gmsd_vif]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# gmsd — IMGMETRICS `perceptual` op

- **データ種**: `image2d × image2d` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.gmsd(ref, dist, data_range: 'float' = 255.0, c: 'float' = 170.0) -> 'float'` (実装を直接呼ぶなら `import iqafsim; iqafsim.gmsd(ref, dist, data_range: 'float' = 255.0, c: 'float' = 170.0) -> 'float'`、台帳から引くなら `opsimgmetrics.get("gmsd")`)

## 使い方

GMSD = GMS 地図の標準偏差(N−1、原実装の ``std2``、論文 式 5)。0 = 同一、大きいほど劣化(**lower is better** —— MOS との順位相関は負で、
公表表は |ρ| を載せる: TID2013 全体 |SROCC| 0.8038、二次資料 0.8044)。入力 (H, W) か (H, W, 3)(3-ch は Y)。
``iqatid.tid2013_evaluate(root, gmsd, luma="rgb")``。**Raises** ``ValueError``: :func:`gmsd_map` と同じ、地図が 1 画素(分散が定義されない)。

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

[fsim](fsim.md) · [fsimc](fsimc.md) · [fsim_pair](fsim_pair.md) · [gmsd_map](gmsd_map.md) · [vifp](vifp.md) · [phase_congruency_pc](phase_congruency_pc.md)

---
*Provenance: iqafsim.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
