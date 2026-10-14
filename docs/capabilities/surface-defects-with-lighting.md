---
id: surface-defects-with-lighting
title: 表面の凹凸欠陥を、照明の設計から検出まで
title_en: Surface relief defects, from lighting design to detection
category: 見つける
ops: [illumination_design, lighting_sweep, photometric_stereo, integrate_normals, bothat]
examples: [illumination_design_demo, photometric_stereo, poc_bump_coplanarity]
version: 0.2.0
inputs: [images]
pipeline: [illumination_design, lighting_sweep, light_source, defect_contrast, irradiance_map, illumination_uniformity, photometric_stereo, integrate_normals, surface_form_error, bothat, auto_threshold, remove_small]
alternatives: [photometric_stereo_robust, normals_from_depth, background_flatten, tophat, laplace_of_gauss, dem_slope]
limits: 照明設計は Michelson コントラストの**シミュレーション**(光沢面の峰は仰角 90° − 2×傾斜)で、実物の BRDF は代表値。フォトメトリックステレオは光源が 8 灯中 4 灯潰れると `lstsq` が 70 度外れ、頑健版でも汚染が半分を超えると壊れる。積分した高さは低周波が決まらない。
calibration: 高さは `photometric_stereo` の法線を `integrate_normals` で積分した**相対値**で、絶対 mm には mm/px と勾配の単位が要る。横方向は `mm_per_px_from_reference`、縦方向は既知段差の的で係数を出す。
---

# 表面の凹凸欠陥を、照明の設計から検出まで

## できること

打痕・バンプ・研削筋のような**形の欠陥**は、色ではなく面の傾きで見えます。だから照明を先に設計し(どの仰角の光でその傾斜が最もコントラストを出すか)、複数灯で法線を出し(フォトメトリックステレオ)、高さに積分し、そこから欠陥を切り出す —— この項目はその 4 段を 1 本に繋ぎます。

## What it does

Relief defects (dents, bumps, grinding marks) show as surface slope, not colour. Design the light first (which ring elevation gives the most contrast for that slope), recover normals from several lights (photometric stereo), integrate to height, then segment the defects — one chain.

## 向くところ / 向かないところ

**向く**: 鏡面〜半光沢の平面部品。灯を切り替えて撮れる据え置きの検査機。傾斜 2〜20° の欠陥。

**向かない**: ★1 灯 1 枚で済ませたい場面(傾斜は 1 枚からは決まらない)。★光沢の強い面で灯の一部が飽和・遮蔽される場面 —— 8 灯中 4 灯が影に落ちると `photometric_stereo` の `lstsq` は 70.52 度外れ、しかも診断は満点を報告していた(`specular_photometric.md` の「ゼロの測定は証拠ではない」)。★積分した高さの**低周波**(反り)は法線の積分では決まらない —— 反りは `poc_bump_coplanarity` のように面を当てはめて引く。

## 推奨パイプライン

`illumination_design` → `lighting_sweep` → `light_source` → `defect_contrast` → `irradiance_map` → `illumination_uniformity` → `photometric_stereo` → `integrate_normals` → `surface_form_error` → `bothat` → `auto_threshold` → `remove_small`

**設計**: `illumination_design(surface, defect, slope_deg)` で灯の族を順位づけ → `lighting_sweep` で仰角対コントラスト → 勝った `light_source` を `defect_contrast` で確かめ、`irradiance_map` → `illumination_uniformity` でむらを数字に。**計測**: 灯を切り替えた画像列を `photometric_stereo` に → `integrate_normals` で高さ → `surface_form_error` で形状誤差の 1 個の数。**検出**: 高さ(または法線の傾き)を `bothat` で局所の凹みだけに → `auto_threshold` → `remove_small`。

## 代替

灯が汚れる場面は `photometric_stereo_robust`(median / ransac)。深度センサがあるなら `normals_from_depth`。反りは `background_flatten` で先に引く。明るい凸なら `tophat`、輪郭寄りなら `laplace_of_gauss`。高さ場の傾斜は `dem_slope` でも出る(高さ格子は depth 型そのもの)。

## 限界

- 照明設計の数字は **BRDF の代表値によるシミュレーション**。`lighting_sweep` の峰(光沢面で 90° − 2×傾斜)は閉形式で固定してあるが、実物の光沢はそのまわりに幅を持つ。
- `photometric_stereo` の破綻点は「半分が汚染されたとき」で、それは直せない(`specular_photometric.md`)。生き残りが 3 灯を切った画素は NaN。
- `integrate_normals` の高さは積分定数と低周波が決まらない相対値。
- `auto_threshold` は値域 [0,1] を仮定するので、µm 単位の高さ場をそのまま渡すと 0.5 µm で切る(`poc_bump_coplanarity` の注記)—— 先に正規化する。

## 実寸校正

横方向は `mm_per_px_from_reference`。高さは法線の積分値なので、**既知段差の的**(段差ゲージ)を同じ配置で撮り、積分した高さとの比で縦の係数を出す。設計側の `light_source` / `irradiance_map` は mm で置く(`radius_mm` / `height_mm` / `size_mm`)。

## 最初の 1 本

```python
import fullseye as fs

tbl = fs.ledger.illumination_design(surface="glossy", defect="topographic", slope_deg=10.0)
print(tbl["ranking"][0])                       # 勝った灯の族と仰角
sweep = fs.ledger.lighting_sweep(surface="glossy", slope_deg=10.0)
print("峰の仰角 [deg]", float(sweep[sweep[:, 1].argmax(), 0]))   # 90 - 2*10 = 70
```

## 裏づけ

- op: `illumination_design` / `lighting_sweep` / `defect_contrast`(設計)、`photometric_stereo` / `integrate_normals`(形)、`bothat` / `auto_threshold`(検出)
- 例: [`illumination_design_demo`](../../examples/illumination_design_demo.py)、[`photometric_stereo`](../../examples_3d/photometric_stereo.py)、[`poc_bump_coplanarity`](../../examples/poc_bump_coplanarity.py)
