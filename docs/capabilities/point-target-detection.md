---
id: point-target-detection
title: 小さな点状の目標を見つけて、副画素で位置を出す
title_en: Find small point-like targets and locate them below the pixel
category: 見つける
ops: [star_detect, peak_subbin, find_peaks, noise_sigma]
examples: [poc_search_sweep_width, poc_astro_photometry]
version: 0.1.11
---

# 小さな点状の目標を見つけて、副画素で位置を出す

## できること

頑健に推定した背景と雑音から `背景 + kσ` を超える局所最大を拾い、重心で副画素の位置を返します。名前は天体ですが**中身は分野中立**で、漂流物・微小欠陥・蛍光輝点・粒子に同じものが使えます。

## What it does

Pick local maxima above a robustly estimated background plus k sigma, and return sub-pixel centroids. The name is astronomical but the method is domain-neutral: drifting objects, small defects, fluorescent puncta, particles.

## 向くところ / 向かないところ

**向く**: 目標が点広がり関数と同じ大きさのとき。密度が低く、重なりが少ないとき。

**向かない**: 目標が広がっている場合(領域として測る `blob_label` 系へ)。★**検出率だけを見ると誤検出が見えません** —— 空撮では誤検出は画面の端でなく**直下に集中**します(`poc_search_sweep_width` で 0-32 m 帯 113 件 / 最外帯 0 件)。閾値だけで走査幅は 406 m から 170 m まで動くので、**検出性能は誤検出率と対でしか語れません**。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

img = np.random.default_rng(0).normal(0.0, 0.01, (128, 128))
img[40, 70] += 1.0                              # 点目標を 1 つ植える
pts = fs.star_detect(img, threshold_sigma=5.0)
print(pts)                                      # (row, col) の副画素座標
```

## 裏づけ

- op: `star_detect`(検出 + 重心)、`peak_subbin`(1-D の頂点)、`find_peaks`、`noise_sigma`(頑健な雑音推定)
- 例: [`poc_search_sweep_width`](../../examples/poc_search_sweep_width.py)、[`poc_astro_photometry`](../../examples/poc_astro_photometry.py)
