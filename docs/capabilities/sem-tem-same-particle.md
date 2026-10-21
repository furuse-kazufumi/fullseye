---
id: sem-tem-same-particle
title: 同じ粒子を走査像と透過像で測り、二つの寸法偏りを比べる
title_en: Measure the same particles in scanning and transmission images and compare both size biases
category: 測る
ops: [sem_render, sem_image, tem_projected_potential, tem_image_weak_phase, tem_multislice, tem_power_spectrum, watersheds_marker, radon_transform, filtered_backprojection]
examples: [poc_sem_tem_same_particle]
version: 0.6.1
inputs: [image2d]
pipeline: [sem_render, tem_power_spectrum]
alternatives: [sem_image, tem_image_weak_phase, watersheds_marker, radon_transform, filtered_backprojection]
limits: 二次電子像は内部構造を示さず、透過像には薄い支持膜が要る。厚い粒子では弱位相近似が崩れ、限定角再構成は欠落角方向へ伸びる。
calibration: 画素寸法を既知寸法試料で校正し、走査像はビーム幅、透過像は電子波長と焦点外れを記録する。PoCは既知のnm格子なので追加較正0。
---

# 同じ粒子を二つの電子像で測る

## できること

`examples/poc_sem_tem_same_particle.py` は、20〜80 nmの球形・ファセット粒子14個を一つの真値台帳で持ち、同じ位置・径・材料から走査像と透過像を作ります。ISO 13322-1型の面積相当径、最大傾斜の縁、距離変換と`watersheds_marker`による接触粒子分離を同じ真値に照合します。

## What it does

One truth ledger of fourteen 20–80 nm spherical and faceted particles drives both scanning and transmission images. Area-equivalent diameter, maximum-slope edges, distance-transform watershed splitting, stereo height and limited-angle reconstruction are compared against that shared truth.

52 nm粒子の実行値は、走査像のしきい値で+4.16 nm、透過像の正焦点で-0.18 nm、焦点外れ12000 nmで+9.82 nmです。前者はガウス縁の半値幅、後者はフレネル間隔`sqrt(lambda defocus)`で説明します。反射信号の材料比、±5°の視差高さ、±60°の限定角再構成も、それぞれ公表値・閉形式・完全角の第2再構成で採点します。

## 向くところ / 向かないところ

向く用途は、二つの画像から得た粒径が食い違ったときの原因分解、測定条件の記録、接触粒子を含む粒径分布の比較です。走査像の二次電子だけでは内部構造が分からず、透過像には薄い支持膜が必要です。厚い粒子では弱位相近似が崩れるため、最大粒子についてマルチスライスとの差も数値で残します。

## 最初の 1 本

```python
import numpy as np
import semsim
import temsim

height_nm = np.zeros((32, 32))
scanning_image = semsim.sem_render(height_nm, pixel_nm=1.0)
power = temsim.tem_power_spectrum(scanning_image)
print(scanning_image.shape, power.shape)
```

## 推奨パイプライン

`sem_render` → `tem_power_spectrum`

## 代替

材料差まで要る走査像は`sem_image`、透過像の結像は`tem_image_weak_phase`、接触対は`watersheds_marker`、限定角は`radon_transform`と`filtered_backprojection`を使います。

## 限界

二次電子像は内部構造を示しません。透過像には薄い支持膜が必要で、厚い粒子では弱位相近似が崩れます。限定角再構成は欠落角方向へ伸びます。

## 実寸校正

画素寸法を既知寸法試料で校正し、走査像はビーム幅、透過像は電子波長と焦点外れを記録します。このPoCは既知のnm格子なので追加較正は0です。
