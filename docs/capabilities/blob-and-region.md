---
id: blob-and-region
title: 領域を切り出して、選んで、数える
title_en: Segment regions, select them, and count
category: 見つける
ops: [blob_label, blob_select, blob_count, watersheds]
examples: [poc_cell_counting, poc_particle_sizing, poc_real_coin_metrology]
version: 0.1.11
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
print('個数 =', fs.ledger.blob_count(mask))
```

## 裏づけ

- op: `blob_label` / `blob_select` / `blob_count` / `watersheds`
- 例: [`poc_cell_counting`](../../examples/poc_cell_counting.py)、[`poc_particle_sizing`](../../examples/poc_particle_sizing.py)
