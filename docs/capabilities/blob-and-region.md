---
id: blob-and-region
title: 領域を切り出して、選んで、数える
title_en: Segment regions, select them, and count
category: 見つける
ops: [blob_label, blob_select, blob_count, watersheds, blob_count_interval]
examples: [poc_cell_counting, poc_particle_sizing, poc_real_coin_metrology, poc_dense_bubble_count]
version: 0.1.11
inputs: [image]
pipeline: [auto_threshold, blob_label, blob_select, blob_features]
alternatives: [watersheds, blob_seeds, blob_count, blob_count_interval, remove_small, select_shape, otsu]
limits: 計数が合っていて分割が全部外れる点がある(`poc_cell_counting`)—— 数と形を別に数える。粒度分布で D50 が合う点は「正確」ではなく融合と縁切れの打ち消し(`poc_particle_sizing`)。
calibration: 面積は mm/px の **2 乗**。`mm_per_px_from_reference` で mm/px を出し、面積には自分で 2 乗して掛ける(`table_px_to_mm` が換算するのは長さ列だけ)。
---

# 領域を切り出して、選んで、数える

## できること

連結成分にラベルを付け、面積・形・位置で選び、数えます。接触している対象は分水嶺で分けられます。

## What it does

Label connected components, select them by area, shape or position, and count them. Touching objects can be separated with a watershed.

## 向くところ / 向かないところ

**向く**: 個数・面積・粒度分布。前景と背景がはっきり分かれる場面。

**向かない**: ★**計数が合っていて分割が全部外れる点があります**(`poc_cell_counting`)。1 つの指標に畳まず、**数と形を別に数えてください**。粒度分布では D50 が合う点が「正確」ではなく**打ち消し**であることも実測されています(`poc_particle_sizing`)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

mask = np.zeros((64, 64), bool)
mask[10:20, 10:20] = True
mask[40:46, 40:46] = True
# ★`blob_count` は**台帳 op ではなく 2-D の進化 op** です。
#   `fs.ledger.<name>` で見つからないときは `fs.op_find("<name>")` を引くと、どの層に居るかが返ります。
print('個数 =', fs.op.blob_count(mask))          # 2.0
```

## 推奨パイプライン

`auto_threshold` → `blob_label` → `blob_select` → `blob_features`

`auto_threshold` で前景の 2 値マスク → `blob_label` で連結成分にラベル → `blob_select` で面積・形・位置で絞り → `blob_features` で個々の面積・重心・主軸を表にする。

## 代替

接触した対象は `watersheds`(種は `blob_seeds`)。個数だけなら `blob_count`。重なりが深くて個数が決まらないかもしれないときは `blob_count_interval` —— 山の突出度を測り、決まらなければ個数ではなく区間を返す(`poc_dense_bubble_count`)。2-D レジストリ側で済ませるなら `otsu` → `remove_small` → `select_shape`。

## 限界

計数が合っていて分割が全部外れる点がある(`poc_cell_counting`)—— 数と形を別に数える。粒度分布で D50 が合う点は「正確」ではなく融合と縁切れの打ち消し(`poc_particle_sizing`)。

## 実寸校正

面積は mm/px の **2 乗**。`mm_per_px_from_reference` で mm/px を出し、面積には自分で 2 乗して掛ける(`table_px_to_mm` が換算するのは長さ列だけ)。

## 裏づけ

- op: `blob_label` / `blob_select` / `blob_count` / `watersheds`
- 例: [`poc_dense_bubble_count`](../../examples/poc_dense_bubble_count.py)、[`poc_cell_counting`](../../examples/poc_cell_counting.py)、[`poc_particle_sizing`](../../examples/poc_particle_sizing.py)
