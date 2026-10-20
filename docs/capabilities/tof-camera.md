---
id: tof-camera
title: 同じ3次元場面を間接ToFと直接ToFで測る
title_en: Measuring one 3-D scene with indirect and direct time of flight
category: 測る
ops: [itof_capture, itof_phase_amplitude, itof_noise_budget, itof_unwrap_multifreq, itof_unwrap_error_rate, itof_multipath_separate, itof_flying_pixel_mask, itof_wiggling_correct, tof_multipath_phase, dtof_cube_simulate, dtof_cube_depth, spad_deadtime_apply, bilateral_filter_depth, depth_to_points]
examples: [poc_tof_camera]
version: 0.7.0
inputs: [depth]
pipeline: [itof_capture, itof_phase_amplitude, itof_unwrap_multifreq, bilateral_filter_depth, depth_to_points]
alternatives: [dtof_cube_simulate, dtof_cube_depth]
limits: 解析的な平面場面。間接方式は位相折返し・多経路・混合画素、直接方式は時間ビン・pile-up・光子欠乏を受ける。遮蔽面の奥は両方式とも測れない。
calibration: 間接方式は変調周波数・位相段・電子数・背景光、直接方式は時間ビン・応答幅・光子数・デッドタイムを実測値に合わせる。
---

# 同じ3次元場面を間接ToFと直接ToFで測る

## できること

`poc_tof_camera` は床、二面コーナー、箱を積んだ荷台、光沢面、透明板、細い柱、暗明市松を 70°×55° のピンホールカメラから 320×240 画素で撮ります。各画素を 3×3 本の光線で積分し、Lambert 反射、逆二乗、レンズ減光、ショット雑音、読み出し雑音、暗電位、多経路を加えます。実データは Lawin・Forssén・Ovrén (ECCV 2016) の生フレーム、壁・メッシュの反復実測、無雑音の4相 MPI レンダリングを数値だけで照合します。README に再配布許諾が明記されていないため、実フレーム自体は公開図へ転載しません。

## What it does

The runnable example compares phase-based continuous-wave ranging and photon-arrival histograms on one analytic inspection scene. It scores ambiguity, noise, harmonic wiggling, multipath, mixed edge pixels, time-bin resolution, pile-up, reflectivity and box-volume errors against closed forms.

## 展示図

`01_scene_viewer` は同じ320×240画素をIR振幅、1.5–6.0 mの色距離、斜めから見た点群で示します。合成と実測の振幅分布のW1距離は0.145で、実測シーン間0.396の1.5倍（0.594）を門とします。`02_effects_added` は理想像に減光、3×3サブ光線による混合と雑音、多経路を順に加えます。`03_noise_vs_amplitude` は距離雑音の対数傾きが実測 -0.878、合成 -1.027であることを示し、`04_corner_bow` は壁接合部の実測偏り -551 mmに対して合成 +75 mm（プロファイルの向きを揃えると同符号）を重ねます。実フレームは再配布せず、曲線と集計値だけを掲載します。

`05_glass_two_returns` は1.35 m離れた透明板の二返り、`06_pole_flying_pixels` は細い柱の輪郭で前景と背景が混ざる画素、`07_dtof_histograms_depth` は直接方式の光子到着ヒストグラムと復号距離です。`08_volume_and_limits` は既存の `bilateral_filter_depth` → `depth_to_points` 連鎖で三つの箱を測り、誤差が8 %未満であることと、遮蔽面の奥・鏡面・散乱が対象外であることを表にします。`09_dtof_light_front` は48枚、576×432画素、8 fpsで1.4–6.2 mを進む光前線です。13件の門を通し、新しいop、学習、較正はいずれも追加しません。

## 向くところ / 向かないところ

**向く**: 変調周波数や時間ビンの選定、コーナー・透明体・細線の誤差の説明、体積測定方式の比較。

**向かない**: 曲面メッシュ、波長依存、偏光、散乱、回折、回路の全状態を含む製品評価。

## 推奨パイプライン

間接方式は `itof_capture` → `itof_phase_amplitude` → `itof_unwrap_multifreq`、直接方式は `dtof_cube_simulate` → `dtof_cube_depth`。多経路は `tof_multipath_phase` と `itof_multipath_separate`、混合画素は `itof_flying_pixel_mask` で診断します。

距離を寸法へつなぐときは `bilateral_filter_depth` → `depth_to_points`。PoC はこの連鎖を facade から型変換なしで呼び、三つの箱の体積まで測ります。

## RAG recipes

```yaml
- query: "iToF の距離画像を滑らかにして点群から箱の体積を測りたい"
  input: depth
  chain: [bilateral_filter_depth, depth_to_points]
  output: points
  limit: "段差をまたがない range_sigma と、実カメラの内部パラメータが必要"
- query: "dToF の光子到着ヒストグラムから距離画像を作りたい"
  input: counts
  chain: [dtof_cube_depth, bilateral_filter_depth]
  output: depth
  limit: "pile-up 補正前は強い近距離の返りへ偏る。二つの返りは一枚の距離へ潰れる"
```

## 代替

単一画素の直接方式だけなら `tcspc_simulate` と `dtof_depth`、二経路の位相偏りだけなら `tof_multipath_phase` を使います。

## 限界

- 場面は平面と直方体の解析的な光線交差で、曲面・偏光・体積散乱は扱いません。
- 間接方式の暗部は光子・背景・読み出し雑音で荒れますが、画素間クロストークは扱いません。
- 直接方式の理想モデルは反射率による系統偏りを持ちません。実モデルではpile-upが早い側へ寄せます。
- どちらも遮蔽面の奥や光が戻らない面を復元しません。

## 実寸校正

間接方式は変調周波数と位相段を周波数基準へ、電子数と背景光を暗明の平面へ合わせます。直接方式は時間ビンと固定遅延を既知距離の平面へ、応答幅とデッドタイムを時間ヒストグラムへ合わせます。

## 最初の 1 本

```python
import numpy as np
import itof

truth = np.full((20, 50), 1.2)
raw = itof.itof_capture(truth, frequencies_hz=(20e6, 80e6, 100e6), noise=False)
phase = itof.itof_phase_amplitude(raw)
depth = itof.itof_unwrap_multifreq(phase, max_range_m=5.0)["depth"]
print(float(np.max(np.abs(depth - truth))))
```

走らせるには `py -3.11 examples/poc_tof_camera.py` を使います。
