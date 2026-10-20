---
id: water-inspection-images
title: 水が検査画像にどう写るか(プールの底のコースティクス・瓶の側面像と液面・濡れた面・船体の水中画像)
title_en: How water looks in inspection images (caustics on a pool floor, a bottle seen from the side with its fill line, a wet surface, a hull seen through water)
category: 光と色
ops: [caustic_irradiance, bottle_image, fill_level_from_image, wet_surface_appearance, wet_dry_inspection_pair, underwater_inspection_image, caustic_floor_segmentation]
examples: [poc_water_inspection_images]
version: 0.7.1
inputs: [image2d, rgbimage]
pipeline: [caustic_irradiance, caustic_floor_segmentation]
alternatives: [bottle_image, fill_level_from_image, wet_surface_appearance, wet_dry_inspection_pair, underwater_inspection_image]
limits: 瓶は水平の断面ごとに追跡するので、カメラから縦に離れた行の光線の傾きを無視する(垂直な円柱なら実効屈折率 sqrt(n² − sin²α) で厳密に扱えるが、肩の曲面では使えない。傾き 40 度で明るい帯の半幅が約 29 % 動く)。壁の内部反射は追わない(全反射は追う)。濡れた面の膜は波長より十分厚いとして干渉を無視し、被覆率の法則(膜厚 2 µm で 63 %)は仮定。コースティクスの光子法は折り目で有限の大きな値を数え、波面法は inf と旗を返す。海の傾きの絶対値は毛管波を持たないスペクトルでは決まらないので手で合わせる。ランプのベールは 1 回散乱でビームの形は仮定。
calibration: 瓶はカメラ距離・画素の大きさ(物体面)・壁厚・屈折率を実物に合わせる。背面板の放射の角度範囲(既定 ±8 度)は板の仕様に合わせる。濡れた面は膜厚と粗さを実測の光沢度から選ぶ。水中画像は水の種類(ジャーロフ型)を実測の Kd から選び、ランプの出力とカメラとの距離で SNR が決まる。
---

# 水が検査画像にどう写るか(プールの底のコースティクス・瓶の側面像と液面・濡れた面・船体の水中画像)

## できること

`watermedia` の物理を、検査カメラが記録する絵にする 7 本です。`caustic_irradiance` は波のある水面の高さの場から、平行光が水底に作る照度を 2 つの方法で作ります。光子の方法は、規則格子の光線をスネルのベクトル式で曲げて、双線形に床へ撒きます(重みの合計が保存されるので、周期境界では光子の総量が入射 × 平均透過率に一致します)。波面の方法は、水面から床への写像のヤコビアンの逆数を照度とし、折り目(行列式 → 0)では inf と旗を返します。`caustic_floor_segmentation` はその照度から明るい線・網を大津の方法か曲率の稜線で切り出します。ひび割れ検出器はコースティクスの縁をひびと取り違えるので、この分割で縁を除くか、照度で割って平坦化します。

`bottle_image` は円柱の瓶を横から見た画像で、画素ごとの光線を水平の断面で追跡します(外壁・内壁・メニスカスの縁・気泡の円、スネルの式とフレネル透過率、全反射)。背面光では、液体のある部分は円柱レンズなので中央の帯だけが明るくなり、空の部分は縁近くまで明るくなります。気泡は暗い輪(中央は細く明るい)になり、外径は 2 r × 倍率です。`fill_level_from_image` はこの画像から液面を、行平均の最大の段(edge)か 2 水準の当てはめ(brightness)で測り、水準と確信度を返します。

`wet_surface_appearance` は Lekner & Dorf(1988)の濡れた面です。水膜の水–空気界面は内側からの光を全反射で閉じ込めるので、拡散の反照率は a から a (1 − R_s)(1 − r) / (1 − a r) に下がります(r は内部反射率の半球平均、約 0.476)。a = 0.5 で濡れ / 乾 = 0.673 と、暗い面ほど相対的に大きく暗くなります。同時に、膜の滑らかな面が細い鏡面の山を作ります。`wet_dry_inspection_pair` は同じ板を乾湿で描き、局所の法線(粗さに合わせた固定の乱数の高さ)からてかりを出して、欠陥のコントラストを返します。`underwater_inspection_image` はカメラの横のランプで壁を照らす船体の検査で、直接光・後方散乱のベール・画素ごとの SNR を返します(ランプとカメラの視野が重なる中央でベールが最大)。

## What it does

Seven ops in `watervision` (category `watervision` of `opsoptics`) turn the water physics of `watermedia` into the pictures an inspection camera records. `caustic_irradiance` gives the irradiance a collimated light leaves on a floor below a wavy surface by a photon count (vector Snell refraction, bilinear splatting, energy conserved) or by the Jacobian of the surface-to-floor map (inf and a flag at the folds); `caustic_floor_segmentation` cuts the bright web out of it so that a crack detector is not fooled. `bottle_image` ray-casts the horizontal section of every image row of a bottle (glass wall, liquid with a meniscus, bubbles; Snell, Fresnel, total internal reflection) backlit or frontlit, and `fill_level_from_image` reads the fill line back. `wet_surface_appearance` is the Lekner and Dorf (1988) model of why a wet surface is darker (trapped light: a (1 - R_s)(1 - r) / (1 - a r)) and glossier; `wet_dry_inspection_pair` renders one textured plate dry and wet and returns the defect contrast; `underwater_inspection_image` is a lamp-at-the-camera hull view with the backscatter veil and the per-pixel SNR.

## 向くところ / 向かないところ

**向く**: 水槽・プール・水面越しの検査で、コースティクスが欠陥検出に与える偽陽性の見積りと除去、透明容器(瓶・チューブ)の液面と気泡の検査の設計(背面板の角度範囲・カメラ距離・画素の大きさの選び方)、濡れた金属・塗装面の検査で湿りが欠陥のコントラストをどう変えるかの見積り、船体や水中構造物の点検でランプの位置と距離による SNR の見積り。

**向かない**: 肩や底のある実物の瓶の全体の像(断面ごとの追跡なので縦の曲面は扱えない)、壁の内部反射が作るゴースト、膜厚が波長程度の薄膜の干渉、乱流・泡・粒子の多い水の多重散乱、時間とともに動く波のコースティクスの時系列(静止した 1 コマのみ)。

## 推奨パイプライン

`caustic_irradiance` → `caustic_floor_segmentation`

波の高さの場(`ocean_height_field` など)と底の深さと光の向きから床の照度を作り、分割の mask を膨張させて検出器の出力から除きます。強い波では検出器の相対しきい値がコースティクスの勾配に負けて欠陥を見失うので、mask で除いても戻りません。そのときは床の照度(推定または計算)で画像を割って平坦化します。

## 代替

瓶の液面だけなら `bottle_image` と `fill_level_from_image`、濡れの影響だけなら `wet_surface_appearance`(1 点)か `wet_dry_inspection_pair`(画像)、水中の色と SNR は `underwater_inspection_image`(より素朴な画像形成は `watermedia.underwater_image`)。

## 限界

- 瓶は水平の断面ごとの追跡で、カメラから縦に離れた行の光線の傾きを無視する。垂直な円柱の傾きは実効屈折率 sqrt(n² − sin²α) に置き換えて厳密に扱え、本設定(カメラ 500 mm、高さ 150 mm)の最大の傾き 8.5 度では明るい帯の半幅が約 2 % 動く。傾き 40 度では約 29 % 動き、肩の曲面ではこの置き換えも使えない。
- 壁や界面の内部反射は(全反射を除いて)追わない。前面光では外壁の最初の反射(R × 環境の放射輝度)だけを足す。
- 濡れた面の膜は波長より十分厚いとして干渉を無視する。被覆率 1 − exp(−膜厚 / 2 µm) は仮定で、てかりの山の幅(ガウス、0.03 rad)と膜による狭まり(半分)も仮定。
- コースティクスは静止した 1 コマ。折り目では波面法が inf、光子法が有限の大きな値を返し、2 つは折り目でだけ食い違う。折り目の判定は 1 画素膨張させ、補間が信頼できない領域を含む。
- ランプのベールは 1 回散乱の近似で、ビームの形(cos^6)とランプ–カメラの重なり(1 / (1 + (基線 / 距離)²))は仮定。

## 実寸校正

瓶の半径・壁厚・高さ・屈折率・カメラ距離・物体面の画素の大きさ(`pixel_pitch_um`)を実物に合わせます。背面板の放射の角度範囲は `PANEL_HALF_ANGLE_DEG`(既定 8 度)で、板の仕様に合わせます。濡れた面の膜厚と粗さは実測の光沢度に合わせ、水中画像の水の種類は実測の Kd(またはディスク透視度)から最も近いジャーロフ型を選びます。

## 最初の 1 本

```python
import numpy as np
import watervision as WV

# 水を半分入れた瓶(半径 30 mm、壁 2.5 mm、高さ 150 mm)を背面光で撮り、液面を画像から測る
img = WV.bottle_image(30.0, 2.5, 150.0, 0.5, 1.52, 1.333, pixel_pitch_um=200.0)
lv = WV.fill_level_from_image(img["image"], 200.0)
print(round(lv["level_mm"], 1))                                            # 75.0

# 濡れた面: 反照率 0.5 の面は水膜の下で 0.673 倍になる(Lekner & Dorf)
w = WV.wet_surface_appearance(0.5, 0.2, 50.0, 30.0, 30.0)
print(round(float(w["ratio"]), 3))                                         # 0.673

# 平らな水面の下の床は、cos θ · T の一様な照度
c = WV.caustic_irradiance(np.zeros((16, 16)), 3.0, 1.0, (0.0, 0.0))
print(round(float(c["irradiance"].mean()), 4))                             # 0.9794
```

走らせて見るなら `py -3.11 examples/poc_water_inspection_images.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
