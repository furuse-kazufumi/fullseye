---
id: grating-spectrometer-and-illumination
title: 回折格子の分光器と顕微鏡の照明系(帯域の幅・smile / keystone・ケーラー / クリティカル・同軸のハーフミラー)
title_en: Grating spectrometer and microscope illumination (bandwidth, smile and keystone, Koehler and critical illumination, coaxial half mirror)
category: 光と色
ops: [grating_dispersion, czerny_turner_design, spectrometer_bandpass, spectrometer_slit_image, spectrometer_spectrum, illumination_train, illumination_field, coaxial_illumination]
examples: [poc_spectrometer_illumination]
version: 0.6.1
inputs: [pairs]
pipeline: [czerny_turner_design, spectrometer_bandpass, spectrometer_spectrum]
alternatives: [grating_dispersion, spectrometer_slit_image, illumination_train, illumination_field, coaxial_illumination]
limits: 鏡とレンズは無収差、カメラは歪曲の無い直線写像なので、帯域の幅は収差を入れない下限。高次の回折効率は 1 次との比の定数(模型)、偏光と blaze は入れない。照明は近軸で cos⁴ とレンズの収差を入れない。
calibration: 較正は無い(設計値から閉形式と数値の畳み込みで出す)。実機の分光器は輝線ランプで波長を較正し、装置関数は単色の線で測って差し替える。
---

# 回折格子の分光器と顕微鏡の照明系(帯域の幅・smile / keystone・ケーラー / クリティカル・同軸のハーフミラー)

## できること

分光器の「帯域の幅」は、入口スリットの幅・格子の溝の密度と照らされた本数・鏡の焦点距離・検出器の画素から決まります。`gratingspec` の 5 本は、格子の式 mλ = d(sin α + sin β) と Czerny–Turner の幾何からそれを組み立てます。`grating_dispersion` は角分散・逆線分散・分解能 mN・自由スペクトル範囲・同じ方向へ出る他の次数の波長を、`czerny_turner_design` は帯域と検出器の長さからカメラ鏡の焦点距離とコマを消す Shafer の角を、`spectrometer_bandpass` はスリットの像 ⊗ 画素 ⊗ 回折の装置関数の FWHM とエタンデュを、`spectrometer_slit_image` は溝に沿った方向余弦を保つ 3 次元の格子の式で長いスリットの像の smile と keystone を、`spectrometer_spectrum` は入力スペクトルから画素の読み(2 次・3 次の像の重なりとロングパスのフィルタつき)を出します。クロマティック共焦点の `spectrometer_fwhm_nm` とハイパースペクトルの `band_fwhm_nm` に渡す数字を、ここで作れます。

照明では、`illumination_train` がケーラー照明とクリティカル照明の照明系(光源・コレクタと視野絞り・開口絞り・コンデンサ・標本)を近軸で並べて共役を数え、`illumination_field` が標本の点と方向から光源まで逆に追って放射照度を出します(ケーラーは光源の模様が視野に写らず、クリティカルは写る)。`coaxial_illumination` は同軸落射のハーフミラーの往復 R·T(50/50 で 1/4)と、鏡面・つや消しの部品にカメラが見る像を返します。

PoC `poc_spectrometer_illumination` は、公開論文 2 本(CC BY 4.0)の分光器の Shafer の角・像の幅・分解能、回折の床 0.886 λ/(mN)、smile の閉形式と Littrow の曲率半径、Hg ランプの紫外線の 2 次の偽の線、ケーラー照明の一様さ、E = L π NA²、同軸の R·T と長方形の Lambert 面の閉形式を門にしています。

## What it does

Five ops in `gratingspec` (category `spectrometer`): the grating equation with angular and reciprocal linear dispersion, resolving power mN, free spectral range and overlapping orders; a first-order Czerny-Turner design with Shafer's coma condition; the bandpass as the FWHM of the slit image, pixel and diffraction convolved, with the etendue; smile and keystone of a long slit from the 3-D grating equation; and the detector reading of an input spectrum including higher-order overlap and a long-pass filter. Three in `illumdesign`: Koehler and critical illumination trains with their conjugates, the specimen irradiance by paraxial backward tracing to a source radiance map, and the coaxial half mirror (round trip R·T, ghost, the image of a mirror-like or matte part).

## 向くところ / 向かないところ

**向く**: 分光器のスリット・格子・焦点距離・画素の選定(分解能と光の量の取引)、ハイパースペクトルの帯域の幅や smile / keystone の見積り、迷光の次数とフィルタの要否、照明系の視野絞り・開口絞りの配置の確認、同軸照明のハーフミラーの反射率の選定とパネルの大きさの見積り。

**出典と模型の区別**: 格子の式・分散・分解能・帯域の目安は Palmer の *Diffraction Grating Handbook*(8th ed.)、コマの条件は Shafer ほか 1964(公開論文の値で照合)、照明の共役は Köhler 1893 と教科書。高次の回折効率は 1 次との比の定数(模型)です。

**向かない**: 鏡とレンズは無収差(非点収差・球面収差・デフォーカスによる端の分解能の悪化は出ない、値は下限)、カメラは歪曲の無い直線写像、偏光と格子の効率(blaze)は入れていません。照明は近軸で cos⁴ とレンズの収差を入れていません。

## 最初の 1 本

```python
import gratingspec as G
import illumdesign as I

D = G.czerny_turner_design()                     # 1200 本/mm、500〜750 nm、検出器 28.7 mm
B = G.spectrometer_bandpass(D, slit_width_um=25.0, pixel_um=14.0, input_na=0.11)
print(round(float(B["fwhm_nm"][2]), 3), B["regime"][2])   # 0.397 slit —— 帯域の幅はスリットで決まる

S = G.spectrometer_slit_image(D, slit_height_mm=4.0)
print(round(float(S["smile_um"][2]), 1))         # 51.4 —— スリットの端の像は長い波長の側へ曲がる

K = I.illumination_train("kohler")
print(round(K["field_diameter_mm"], 3), round(K["illumination_na"], 3))   # 1.0 0.2
print(I.coaxial_illumination()["round_trip"])    # 0.25 —— 50/50 のハーフミラーの往復
```

走らせて見るなら `py -3.11 examples/poc_spectrometer_illumination.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。

## 推奨パイプライン

`czerny_turner_design` → `spectrometer_bandpass` → `spectrometer_spectrum`

格子・入射角・帯域・検出器の長さから設計表を作り(`czerny_turner_design`、カメラの焦点距離と Shafer の角)→ スリット・画素・NA から波長ごとの帯域の幅とエタンデュを出し(`spectrometer_bandpass`)→ 入力スペクトルを画素の読みにする(`spectrometer_spectrum`、2 次・3 次の重なりとロングパスのフィルタ)。帯域の幅はそのままクロマティック共焦点の `spectrometer_fwhm_nm` やハイパースペクトルの `band_fwhm_nm` に渡せる。

## 代替

格子 1 枚の分散と分解能だけなら `grating_dispersion`。長いスリット(撮像分光)の smile と keystone は `spectrometer_slit_image`。照明系は `illumination_train` で共役を数え、`illumination_field` で視野の放射照度を出す。同軸落射のハーフミラーの往復 R·T と部品の像は `coaxial_illumination`。

## 限界

鏡とレンズは無収差、カメラは歪曲の無い直線写像なので、帯域の幅は収差を入れない下限(公表の分光器の端の分解能の悪化は出ない)。高次の回折効率は 1 次との比の定数(模型)で、偏光と blaze は入れていない。照明は近軸で、cos⁴ とレンズの収差を入れていない。

## 実寸校正

較正は無い(設計値から閉形式と数値の畳み込みで出す)。実機の分光器は輝線ランプ(Hg など)で波長を較正し、装置関数は単色の線で測って差し替える。

## 裏づけ

- op: `grating_dispersion`、`czerny_turner_design`、`spectrometer_bandpass`、`spectrometer_slit_image`、`spectrometer_spectrum`、`illumination_train`、`illumination_field`、`coaxial_illumination`
- 例: [`poc_spectrometer_illumination`](../../examples/poc_spectrometer_illumination.py)
- 文献: Palmer, Diffraction Grating Handbook 8th ed. (2020)、Shafer ほか 1964、Fastie 1952、Köhler 1893、Feng ほか 2021 と M 型 2025(Sensors、CC BY 4.0)
