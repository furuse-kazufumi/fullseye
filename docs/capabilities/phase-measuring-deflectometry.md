---
id: phase-measuring-deflectometry
title: 光沢面の µm の凹みを縞の鏡像で測る(位相計測デフレクトメトリ: 縞 → 位相 → 傾き → 曲率)
title_en: Find micrometre dents on glossy surfaces from the mirror image of a fringe screen (phase-measuring deflectometry)
category: 測る
ops: [deflectometry_rig, deflectometry_screen_pattern, deflectometry_render, deflectometry_phase_to_slope, slope_to_curvature, deflectometry_sensitivity]
examples: [poc_phase_measuring_deflectometry]
version: 0.6.1
---

# 光沢面の µm の凹みを縞の鏡像で測る(位相計測デフレクトメトリ: 縞 → 位相 → 傾き → 曲率)

## できること

塗装面・カバーガラス・鏡面研磨品の凹み、うねり、研磨ムラを、面の前に置いた画面の縞の**鏡像**から測ります。光沢面は鏡なので、照明を当てて撮った写真には照明しか写らず、深さ数 µm の凹みはまず見えません。画面に位相シフト縞を出して鏡像を撮ると、面が α 傾くだけで反射は 2α 曲がり、距離 d 先の画面では 2dα ずれます。傾きを、画面までの距離をてこにして測る方法です(Knauer ら 2004)。

- `deflectometry_rig` が装置の幾何(入射角、カメラと画面までの距離、視野、開口、画面の大きさと画素ピッチ)を 1 つの表にし、他の op は `rig=` で受けます。手で書き換えたベクトルはスカラーと食い違うとして拒否します。
- `deflectometry_render` は順方向のシミュレーションです。高さ場の各画素の視線を面に当てて鏡面反射し(`match3d.reflect`)、画面の縞を読みます。拡散成分(縞の振幅が 1 − k_d 倍)、鏡面ローブの散乱、カバーガラスの裏面反射(`glassmirror.refract_rays` と Fresnel)、ピントの位置(面にピントなら画面側の円板の MTF、それ以外は開口の点ごとに光線を追う開口積分)、雑音と量子化を入れられます。
- `deflectometry_phase_to_slope` は画面の絶対位相 2 枚(`fringe.wrapped_phase` と `fringe.absolute_phase` で出したもの)から、面の格子上の法線マップを作ります(`match3d.normal_from_reflection`)。法線マップは `photometric` と同じ規約なので、`sfp_height` や `photometric.integrate_normals` で高さに、`slope_to_curvature` で曲率になります。
- `slope_to_curvature` は傾きを 1 回微分して平均曲率・ガウス曲率・ラプラシアンを出します。積分しないので、面全体の傾きや一定の傾きの誤差は消え、局所の凹みだけが立ちます。
- `deflectometry_sensitivity` は撮る前に閉形式を出します: 画面の画素 / (2d)、位相の雑音 √(2/N)·σ/b、傾きの雑音 σ_u/(2d) と σ_u/(2d cos θ)、高さと傾きの不定性の係数 sin θ / d、ピントのぼけ。

## What it does

Phase-measuring deflectometry for glossy surfaces: a rig table, the screen patterns, a forward renderer from a height field to the camera's image of the screen's mirror reflection (diffuse fraction, specular-lobe scatter, the back reflection of a transparent plate, thin-lens focus by aperture integration, noise and quantisation), absolute screen phases to a normal map on the surface grid, slopes to mean or Gaussian curvature without integrating, and the closed-form sensitivity before measuring (slope noise σ_u/(2d), the height-slope coupling sin θ / d, focus blur). The PoC finds 3 µm and 1 µm dents on a painted panel that a lit photograph cannot show and scores every number against the analytic surface.

## 向くところ / 向かないところ

**向く**: 塗装・樹脂・ガラス・研磨金属の外観検査で、高さは µm でも傾きなら測れる欠陥(凹み、うねり、研磨ムラ、オレンジピール)の検出と、検査系の設計の見積り(画面の距離・縞の周期・開口・ピントの位置を変えたときの感度と壊れ方)。

**向かない**: ★1 台のカメラと 1 枚の画面では、面の高さと傾きを分けられません(面が Δz ずれると傾きが Δz sin θ / d 狂う)。局所の凹みの形はほとんど影響を受けませんが、面全体の形を測るには高さの手がかり(2 台目のカメラ、画面を動かす、偏光)が要ります。カメラはピンホール + 薄レンズのぼけ、画面は平らで輝度は角度に依らず、画面の画素の格子と液晶の階調の非線形は入れていません(Wu ら 2015 が挙げる位相誤差の主因)。拡散成分は画面の平均輝度を一様に足す近似、ガラスの裏面は平らで表と平行です。無反射コートの無いカバーガラスでは、裏面の光が凹みの斜面(くさび)で逆向きに曲がり、凹みが 1/4 の深さにしか見えません(PoC の門で閉形式と照合)。装置の幾何は既知とし、較正の op はありません。

## 最初の 1 本

```python
import numpy as np
import fringe
import fullseye as fs

rig = fs.ledger.deflectometry_rig()                   # θ 20°、カメラ 400 mm、画面 300 mm、視野 40 mm
x = np.linspace(-20, 20, 161)
X, Y = np.meshgrid(x, x)
g = np.exp(-(X ** 2 + Y ** 2) / (2 * 1.2 ** 2))
h = -3e-3 * g                                          # 深さ 3 µm の凹み [mm]
phase = {}
for d in ("x", "y"):
    fine = fs.ledger.deflectometry_render(h, rig, 10.0, 4, d)
    coarse = fs.ledger.deflectometry_render(h, rig, 160.0, 4, d)
    phase[d] = fringe.absolute_phase(fringe.wrapped_phase(fine), fringe.wrapped_phase(coarse) * 16)
normals = fs.ledger.deflectometry_phase_to_slope(phase["x"], phase["y"], rig, 10.0)
curv = fs.ledger.slope_to_curvature(normals, x[1] - x[0], "mean")   # 格子 0.25 mm の差分で 5 % ほど低く出る
print("凹みの中心の平均曲率 %.2e /mm(真値 %.2e)" % (curv[80, 80], 3e-3 / 1.2 ** 2))
print(fs.ledger.deflectometry_sensitivity(rig)["slope_noise_x"])
```

走らせて見るなら `py -3.11 examples/poc_phase_measuring_deflectometry.py`(図は `FULLSEYE_FIGURE_DIR` か既定の `out/figures/<PoC 名>/`)。

## 裏づけ

- op: `deflectometry_rig` / `deflectometry_screen_pattern` / `deflectometry_render` / `deflectometry_phase_to_slope` / `slope_to_curvature` / `deflectometry_sensitivity`
- 門: `tests/test_deflectometry.py`(傾いた平面の往復 4e-7、凹みの傾きが格子とともに収束、放物面の曲率 = 1/R、位相雑音と傾きの雑音の閉形式、Δz sin θ / d、拡散・散乱・開口積分の MTF、ガラスのくさびの閉形式、fail-closed)と PoC の 22 門。
- 出典: Knauer, Kaminski & Häusler, Proc. SPIE 5457, 366 (2004) / Wu ら, Opt. Eng. 54(6), 064103 (2015) / Frankot & Chellappa, IEEE PAMI 10(4), 439 (1988) / Wang, Cossairt & Willomitzer, Optica 12 (2025)。
