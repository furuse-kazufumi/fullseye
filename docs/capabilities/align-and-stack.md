---
id: align-and-stack
title: 位置を合わせて重ねる
title_en: Align and stack
category: 組み立てる
ops: [frame_align, drizzle_resample, icp_point2point_3d, interp_scattered]
examples: [poc_astro_photometry, poc_registration_basin]
version: 0.1.11
inputs: [images]
pipeline: [align_frames, drizzle_resample, frame_quality]
alternatives: [frame_align, icp_point2point_3d, register_cross, interp_scattered]
limits: 繰り返し構造(網点・格子)では `frame_align` が `inlier_ratio` 1.00 のまま 80.85 px 外す —— `vote_margin` を併せて見る。合わせすぎると欠陥が消える(`poc_cad_scan_deviation`)。
calibration: 合わせは px のまま。変位を実寸にするなら既知寸法の的を同じ光学系で測り `mm_per_px_from_reference` → `pixel_to_world`。
---

# 位置を合わせて重ねる

## できること

画像列の平行移動を投票で合わせ、サブピクセルで再標本して重ねます。点群は ICP で合わせられます。

## What it does

Align a sequence by voting for the translation, resample sub-pixel, and stack. Point clouds are aligned with ICP.

## 向くところ / 向かないところ

**向く**: 天体スタック、時系列の差分、点群の重ね合わせ。

**向かない**: ★**繰り返し構造**(網点・格子・周期テクスチャ)。`frame_align` は網点で **`inlier_ratio` が 1.00 のまま 80.85 px 外します** ——賛成率は「答えが正しい確率」ではありません。2 番手との比 `vote_margin` を併せて見てください(網点 0.857〜1.000 / 星野 0.143)。★合わせすぎると**欠陥が消えます**(`poc_cad_scan_deviation`)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

rng = np.random.default_rng(0)

# ★対象は**星野**(frame_align は star_detect で星を取ってから合わせる)。
#   一様な雑音だけを渡すと星が 0 個で、推定せずに拒否されます。
yy, xx = np.mgrid[0:128, 0:128]
a = rng.normal(100.0, 10.0, (128, 128))
for r, c in rng.integers(12, 116, (40, 2)):
    a += 3000.0 * np.exp(-((yy - r) ** 2 + (xx - c) ** 2) / (2 * 1.6 ** 2))
b = np.roll(a, (3, -2), axis=(0, 1))

H, info = fs.frame_align(a, b)       # 返りは (3x3 の変換, 内訳の dict)
print(info["shift_row"], info["shift_col"])   # -3.0, 2.0(仕込んだずれ)
print(info["rms_px"], info["vote_margin"])    # 2.5e-14, 0.135
```

## 推奨パイプライン

`align_frames` → `drizzle_resample` → `frame_quality`

`align_frames` で列を平行移動で合わせ(投票、`vote_margin` つき)→ `drizzle_resample` でサブピクセル再標本して 1 枚に重ね → `frame_quality` で重ねた結果の鮮鋭度・雑音を数字にする。

## 代替

1 対の変位だけ要るなら `frame_align`。点群は `icp_point2point_3d` / `register_cross`。欠測を埋めるなら `interp_scattered`(外挿率つき)。

## 限界

繰り返し構造(網点・格子)では `frame_align` が `inlier_ratio` 1.00 のまま 80.85 px 外す —— `vote_margin` を併せて見る。合わせすぎると欠陥が消える(`poc_cad_scan_deviation`)。

## 実寸校正

合わせは px のまま。変位を実寸にするなら既知寸法の的を同じ光学系で測り `mm_per_px_from_reference` → `pixel_to_world`。

## 裏づけ

- op: `frame_align`(`vote_margin` つき)、`drizzle_resample`、`icp_point2point_3d`、`interp_scattered`
- 例: [`poc_astro_photometry`](../../examples/poc_astro_photometry.py)、[`poc_registration_basin`](../../examples/poc_registration_basin.py)
