---
id: figures-and-annotation
title: 結果を人が読める図にする
title_en: Turn results into figures people can read
category: 見せる
ops: [annotate_figure_grid, colorize_height, render_beauty]
examples: [poc_colormap_readability, poc_dem_terrain]
version: 0.1.11
inputs: [images, image2d]
pipeline: [annotate_figure_grid, annotate_panel_label, annotate_scale_bar, annotate_colorbar]
alternatives: [colorize_height, render_beauty, annotate_legend, annotate_inset]
limits: 疑似カラーの選び方で**無い境目**が見える(`poc_colormap_readability`)。`annotate_figure_grid` の `letters=True` と手書きの (a) が二重になる。
calibration: `annotate_scale_bar` の `units_per_pixel` は `mm_per_px_from_reference` で**実測**した mm/px を渡す(公称倍率で描いたスケールバーは嘘の長さになる)。
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

## 推奨パイプライン

`annotate_figure_grid` → `annotate_panel_label` → `annotate_scale_bar` → `annotate_colorbar`

`annotate_figure_grid` でパネルを並べ → `annotate_panel_label` で (a)(b) → `annotate_scale_bar` で実寸の目盛 → `annotate_colorbar` で疑似カラーの凡例。

## 代替

高さ場の疑似カラーは `colorize_height`、SDF の立体は `render_beauty`。凡例と拡大図は `annotate_legend` / `annotate_inset`。

## 限界

疑似カラーの選び方で**無い境目**が見える(`poc_colormap_readability`)。`annotate_figure_grid` の `letters=True` と手書きの (a) が二重になる。

## 実寸校正

`annotate_scale_bar` の `units_per_pixel` は `mm_per_px_from_reference` で**実測**した mm/px を渡す(公称倍率で描いたスケールバーは嘘の長さになる)。

## 裏づけ

- op: `annotate_figure_grid` / `colorize_height` / `render_beauty`
- 例: [`poc_colormap_readability`](../../examples/poc_colormap_readability.py)、[`poc_dem_terrain`](../../examples/poc_dem_terrain.py)
