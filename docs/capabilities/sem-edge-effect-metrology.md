---
id: sem-edge-effect-metrology
title: SEM の明るい縁が寸法をどれだけ太らせるかを、真値つきで測る
title_en: Measure how much the bright SEM edge inflates a dimension, with ground truth
category: 測る
ops: [sem_render, blob_label, blob_features, seg_dice_jaccard, seg_boundary_f, pod_hitmiss_fit]
examples: [poc_sem_wafer_defect_edge_bias]
version: 0.6.1
---

# SEM の明るい縁が寸法をどれだけ太らせるかを、真値つきで測る

## できること

走査電子顕微鏡(SEM)像では、二次電子が斜面でよけいに出る(放出 ∝ sec θ)ので段差の縁が明るく縁取られ、ビームの有限径(PSF)がその縁を広げます。`sem_render` は高さ場からこの SEM 像を**閉形式の真値つき**で作ります(平面で一様 / 斜面で平面比 = sec θ / 段差の明るい縁の幅 = PSF 幅)。作った像をしきい値 → `blob_label` → `blob_features` で測ると、明るい縁ごと拾って面積が系統的に太ること、その太りが **周囲長 × PSF 幅** でよく説明でき、既知の PSF 幅で引くと消えることが数で示せます。`seg_dice_jaccard` / `seg_boundary_f` で専門家マスクと採点し、`pod_hitmiss_fit` で埋め込み欠陥の検出確率 a90/95 を出します。

PoC の主図は同じ欠陥の二つの電子像に真値輪郭・検出輪郭・縁偏りを重ねます。線量を 10 倍にすると SNR は 3.16 倍になりますが、小さい欠陥ほど縁の面積偏りが大きく残ります。

## What it does

Render a ground-truth SEM image from a height field with `sem_render` (secondary-electron edge effect sec θ + Gaussian beam PSF + Poisson shot noise), then segment it with the classic chain and show that the bright edge inflates the measured area by about perimeter × PSF width — and that subtracting the known beam PSF width removes the bias. Score against expert masks with `seg_dice_jaccard` / `seg_boundary_f`, and fit the probability of detection (a90/95) of embedded defects with `pod_hitmiss_fit`.

The lead figure overlays truth, detections and edge bias on two electron-image contrasts of the same defects. Ten times the dose gives 3.16x SNR, while edge-area bias remains largest for small defects.

## 向くところ / 向かないところ

**向く**: CD-SEM / 外観検査の縁効果の切り分け、合成の真値つき欠陥の生成、面積・寸法の系統誤差の見積もりと補正、検出確率(POD)の見積もり。

**向かない**: ★**Dice が高くても面積は太ります**(`poc_sem_wafer_defect_edge_bias`、合成で Dice 中央 0.885 なのに面積比 1.09〜1.70)。1 つの指標に畳まず、**形の一致(Dice)と寸法の偏り(面積比)を別に数えてください**。★実データの欠陥は背景より暗い穴で、合成の明るい塊と**極性が逆**です。専門家マスクが明るい縁を含むか(規約)で面積比の意味が変わるので、先に規約を数えること。

## 最初の 1 本

```python
import numpy as np
import semsim

# 平らな高さ場 → SEM 像は一様。傾き θ の斜面 → 平面比はちょうど sec θ。
flat = np.zeros((32, 32))
print("平面の ptp =", float(np.ptp(semsim.sem_render(flat))))      # 0.0

ramp = np.tile(np.linspace(0, 31, 32), (32, 1))                   # 勾配 1 → 45 度
r = semsim.sem_render(ramp, pixel_nm=1.0)
print("斜面比 / sec θ =", float(r[16, 16]) / 0.25, 1 / np.cos(np.arctan(1.0)))
```
