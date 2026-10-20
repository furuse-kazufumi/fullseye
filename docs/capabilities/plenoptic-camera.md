---
id: plenoptic-camera
title: 処方から撮るプレノプティックカメラ
title_en: Prescription-based plenoptic camera
category: 描く
ops: [mla_surface, plenoptic_system, plenoptic_capture, plenoptic_mla_calibrate, plenoptic_decode, plenoptic_refocus_depth]
examples: [poc_plenoptic_camera]
version: 0.7.0
inputs: [table, image2d, lightfield]
pipeline: [mla_surface, plenoptic_system, plenoptic_capture, plenoptic_mla_calibrate, plenoptic_decode, plenoptic_refocus_depth]
alternatives: [lf_from_mla, lf_refocus, lf_depth_from_focus, trace_sensor_rays]
limits: 幾何光学のみで回折と画素間クロストークは扱わない。六角格子は面のサグと法線まで対応し、現行の復号器は長方格子だけを校正する。距離換算は主レンズの近軸量を使う。
calibration: 一様な白色場を撮り、マイクロ像のピークをサブピクセルで検出して格子のピッチ・回転・残差を求める。残差が上限を超えた校正は拒否する。
---

# 処方から撮るプレノプティックカメラ

主レンズの逐次処方、周期球面のマイクロレンズアレイ、センサを組み合わせ、一回の撮影から生のマイクロ像と 4-D 光線場を作ります。各センサ画素は一つのレンズレットと主レンズの射出瞳上の一点に対応し、その光線を `lensrender` が物体空間へ逆追跡します。

`mla_surface` は正方または六角配列のサグ、法線、レンズレット番号を定義します。境界上では法線が一意に決まらないため、件数を報告して拒否します。`plenoptic_system` は主レンズと MLA の F ナンバー、マイクロ像径、重なりまたは隙間を閉形式で報告します。

`plenoptic_capture` は生画像、白画像、画素ごとのレンズレット番号、主レンズ瞳の真値座標を返します。`plenoptic_mla_calibrate` は白画像から格子を推定し、`plenoptic_decode` は白画像で周辺減光を正規化しながら `L[v,u,y,x]` へ整流します。`plenoptic_refocus_depth` は再合焦スロープを主レンズの近軸共役からメートル単位の距離と一スロープ刻みの深度分解能へ変換します。

実行例は `py -3.11 examples/poc_plenoptic_camera.py` です。PoC は外部データを使わず、収蔵番号 2026.272 の合成場面を生成します。
