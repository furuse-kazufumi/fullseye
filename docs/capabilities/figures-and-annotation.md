---
id: figures-and-annotation
title: 結果を人が読める図にする
title_en: Turn results into figures people can read
category: 見せる
ops: [annotate_figure_grid, colorize_height, render_beauty]
examples: [poc_colormap_readability, poc_dem_terrain]
version: 0.1.11
---

# 結果を人が読める図にする

## できること

パネルを並べた図、寸法や矢印の注釈、高さの疑似カラー、SDF から起こした立体のレンダリングまで、**fullseye 自身の op** で作れます。外部の作図ライブラリを挟まずに、出力そのものを図にできます。

## What it does

Panel grids, dimension and pointer annotations, height pseudo-colour, and a full SDF renderer — all from Fullseye operators, so a result becomes a figure without a plotting library in between.

## 向くところ / 向かないところ

**向く**: 報告書、記事、Studio の画面、そのまま貼れる図。

**向かない**: ★疑似カラーの選び方で**無い境目が見えます**。`poc_colormap_readability` が、その「無い境目」を数え、崖を先に当てています。★`annotate_figure_grid` は `letters=True` で `(a)` を自動で付けるので、自分でも書くと二重になります。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

h = np.linspace(0, 1, 64)[None, :] * np.ones((64, 1))
img = fs.colorize_height(h)
print('カラー画像', np.asarray(img).shape)
```

## 裏づけ

- op: `annotate_figure_grid` / `colorize_height` / `render_beauty`
- 例: [`poc_colormap_readability`](../../examples/poc_colormap_readability.py)、[`poc_dem_terrain`](../../examples/poc_dem_terrain.py)
