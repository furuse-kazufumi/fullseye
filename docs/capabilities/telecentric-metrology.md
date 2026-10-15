---
id: telecentric-metrology
title: テレセントリックレンズと寸法計測(主光線の傾き → 高さで変わる倍率 → ケラレとぼけ)
title_en: Telecentric lenses for dimensional metrology (chief-ray angle, magnification versus height, vignetting and blur)
category: 測る
ops: [telecentric_lens, chief_ray_angle, magnification_vs_depth, telecentricity_error, defocus_spot_vs_depth, vignetting_vs_field, lens_equivalent_pinhole]
examples: [poc_telecentric_metrology]
version: 0.6.1
inputs: []
pipeline: [telecentric_lens, chief_ray_angle, telecentricity_error, magnification_vs_depth, defocus_spot_vs_depth, vignetting_vs_field]
alternatives: [lens_system, paraxial_trace, lens_equivalent_pinhole, relative_illumination]
limits: 処方は単レンズの組み合わせで、実機のテレセン(5〜10 枚)の瞳収差・歪曲の補正は無い(物体側テレセンの単レンズは物高 8 mm で歪曲 3 %、テレセン度 0.05° が残る)。回折は扱わず、ぼけは幾何光学の光線束。物体が無限遠の処方は拒否する。
calibration: 画像の寸法を mm にする尺度は、両側テレセンなら高さに依らない(視野 4 mm・段差 5 mm で読みの差 −0.01 %)ので 1 枚の校正板でよい。通常のレンズでは同じ条件で 6.89 % 狂うので、測る面の高さで校正する。
---

# テレセントリックレンズと寸法計測(主光線の傾き → 高さで変わる倍率 → ケラレとぼけ)

## できること

段差のある部品(ボンディングのダイ、コネクタのピン、穴)の寸法を 1 枚の画像で測るとき、通常のレンズは近い面ほど大きく写すので、高さの違う面で同じ寸法が違う長さに写ります。`telecentric` の 7 本は `raytrace` の処方(`lens_system` の table)を実光線で追い、この誤差がどれだけ出てどれだけ消えるかを数字で返します。

`telecentric_lens` は同じ単レンズの絞りの位置だけを変えた 3 種(通常 / 物体側テレセン / 両側テレセン)を作り、`stop_shift_mm` で絞りをずらしてテレセン度を崩せます。`chief_ray_angle` は絞りの中心を通る主光線を Newton 法で探し、物体側の傾き(テレセン度)・像の高さ・実光線の入射瞳までの距離を返します。光線は入射瞳でなく絞りを狙うので、入射瞳が無限遠の物体側テレセンでも動きます(`raytrace.chief_ray` はここで止まります)。`magnification_vs_depth` は像面を固定して物体を動かしたときの倍率、`telecentricity_error` は段差の上下で寸法の読みが何 % 狂うかを主光線の幾何 Δz·tanθ と並べて返します。`defocus_spot_vs_depth` は瞳を総当たりで埋めた光線束のぼけの RMS、`vignetting_vs_field` は前玉で光束が欠ける割合(テレセンの視野は前玉径で決まる)、`lens_equivalent_pinhole` は主光線の幾何を `render3d.render_mesh` のピンホール(入射瞳の位置)に写します。

PoC `poc_telecentric_metrology` は、倍率の変化が閉形式 L/(L − Δz) と 7e-5 で一致すること、絞りのずれが Newton の式どおりに入射瞳を動かすこと、ぼけの RMS の傾きが |m|·NA/√2 になることを採点し、ピン・ダイ・穴を 3 種のレンズで実物の質感(アルミの削り目・金めっき・樹脂モールド、影と AO)で描いて、画像から測った寸法の読みと穴の底の見える割合を閉形式と突き合わせ、照明を同軸落射・ドーム・低角リングに変えても寸法の読みが閉形式を追うことを確かめます。

**実画像で確かめたこと**(PoC の主役の章): 論文(Stark ほか, Sci. Rep. 15, 28690, 2025、CC BY 4.0)のテレセン生画像を Fullseye の計測 op で測り、論文の値と突き合わせる。29.5° 傾いたアライメント板(円の間隔 1 mm)の 8 本のリングを、放射状の測定線(measure_pos)で取った線の中心へ「中心と形を共有する楕円の族」で当てると、長軸の伸びは 252.13 ± 0.04 px/mm で論文の K1 = 252.0 px/mm と +0.05 %(論文自身の K1・K2 が ±0.25 % 散っているので、それより細かい一致とは読まない)。★テレセンの証拠: 傾いた板の同心円の中心は r² に比例してずれない(β = 0.0035 ± 0.0034 px/mm²。同じ板を通常 f=25 で写すと 1.40 で、外側のリングの中心が 101 px ずれる)—— 入射瞳は 10.5 m より遠い。★リングごとに自由な楕円を当てると、影で弧が 36〜180° しか見えない外側のリングの長半径が外挿で狂う(弧 36° のリングで 768 px、正しくは 2142 px)。★樹脂の 3D プリント球(公称半径 2.5 mm)は輪郭の閾値で半径が 8 % 動き、真値にならない(2.400 / 2.452 mm。論文の計量級の球の生画像は公開データに無い)。画像: figshare doi:10.6084/m9.figshare.c.7652423(A. Stark、CC BY 4.0、改変あり)。

## What it does

Seven ops in `telecentric` (category `telecentric` of `opsoptics`) on top of the `raytrace` prescriptions: a generator of the same singlet with the stop moved (entocentric, object-side telecentric, bi-telecentric, plus a stop shift that spoils telecentricity), the real chief ray found by aiming at the stop itself rather than at the entrance pupil (so it works with the pupil at infinity), the magnification versus object height on a fixed image plane, the dimensional error across a step, the RMS defocus blur from a brute-force pupil bundle, the vignetting set by the front lens, and a pinhole camera at the entrance pupil for `render3d`. The PoC gates the magnification against L/(L − Δz), the stop shift against Newton's equation, the blur slope against |m|·NA/√2, and measurements taken from rendered images against circle-overlap closed forms. The lead chapter measures the paper's raw telecentric images (Stark et al., Sci. Rep. 15, 28690, 2025, CC BY 4.0) with Fullseye's metrology ops and checks them against the paper: a family of ellipses sharing one centre and shape, fitted to the eight rings of an alignment plate (1 mm spacing) tilted by 29.5°, gives 252.13 ± 0.04 px/mm along the major axis, +0.05 % from the paper's K1 = 252.0 px/mm (the paper's own K1 and K2 spread by ±0.25 %, so the match is not read as finer than that). The telecentric signature: the centres of the concentric rings on the tilted plate do not drift with r² (β = 0.0035 ± 0.0034 px/mm², where a 25 mm entocentric lens would give 1.40 and move the outer centre by 101 px), so the entrance pupil lies beyond 10.5 m. Fitting a free ellipse to each ring instead fails on the outer rings whose arcs are shadowed down to 36–180°. A 3D-printed resin sphere (nominal radius 2.5 mm) is not a usable reference: its outline radius moves 8 % with the threshold.

## 向くところ / 向かないところ

**向く**: 寸法検査のレンズ選び(段差の高さと視野の位置から、通常のレンズで何 % 狂うか)、テレセン度の仕様(0.1° なら段差 1 mm で 1.75 µm)の意味の確認、テレセンの視野と前玉径の見積り、被写界深度と NA の取引、検査の画像を正しい幾何で合成するためのカメラ。

**向かない**: ★処方は単レンズの組み合わせで、実機のテレセン(5〜10 枚)の瞳収差と歪曲の補正は入っていません(物体側テレセンの単レンズは物高 8 mm で歪曲 3 %、テレセン度 0.05° が残ります)。カタログの処方があれば `lens_system` に面を並べて同じ op を使えます。物体が無限遠の処方は拒否します。`lens_equivalent_pinhole` は近軸の幾何の写しで、歪曲・瞳収差・ハイパーセントリック(入射瞳が物体の裏)は描画に入りません(後者は ValueError)。回折は扱わず、ぼけは幾何光学の光線束です。

## 推奨パイプライン

`telecentric_lens` → `chief_ray_angle` → `telecentricity_error` → `magnification_vs_depth` → `defocus_spot_vs_depth` → `vignetting_vs_field`

`telecentric_lens` で同じ単レンズの絞りだけを動かした 3 種(通常 / 物体側 / 両側)の処方を作り(実機の処方があれば `lens_system` の table を代わりに)→ `chief_ray_angle` で主光線の物体側の傾き(テレセン度)→ `telecentricity_error` で段差の上下の寸法の読みの差 → `magnification_vs_depth` で物体を動かしたときの倍率 → `defocus_spot_vs_depth` でぼけの RMS → `vignetting_vs_field` で前玉が決める視野。どれも処方の table を受ける。

## 代替

近軸の量だけで足りるなら `paraxial_trace`。検査の画像を正しい幾何で合成したいなら `lens_equivalent_pinhole` で入射瞳の位置のピンホールにして `render3d` へ(近軸の写しで、歪曲・瞳収差は入らない)。無限遠の物体の照度は `relative_illumination`。

## 限界

- 単レンズの処方なので、物体側テレセンの単レンズは物高 8 mm で歪曲 3 %、テレセン度 0.05° が残る。実機の値はカタログの処方を `lens_system` に並べて同じ op に渡す。
- 回折は扱わない。ぼけは瞳を総当たりで埋めた光線束の RMS(PoC で傾きが |m|·NA/√2 と一致)。
- `lens_equivalent_pinhole` はハイパーセントリック(入射瞳が物体の裏)を拒否する。

## 実寸校正

寸法の尺度(mm/px)は既知寸法の校正板で取る。両側テレセンは倍率が高さに依らない(`telecentricity_error`: 視野 4 mm・段差 5 mm で −0.01 %)ので、校正板を置く高さを気にしなくてよい。通常のレンズ(f 25 mm、作動距離 75 mm)では同じ条件で 6.89 % 狂うので、測る面と同じ高さで校正し、段差の上下は別の尺度にする。テレセン度の仕様 0.1° は段差 1 mm あたり 1.75 µm の読みの差に当たる。

## 最初の 1 本

```python
import telecentric as T

ento = T.telecentric_lens("entocentric", focal_mm=25.0, front_aperture_mm=6.0)   # 作動距離 75 mm の FA レンズ
tele = T.telecentric_lens("bi")                                                    # 両側テレセン(倍率 -0.5)
for lens in (ento, tele):
    e = T.telecentricity_error(lens, field_mm=4.0, step_height_mm=5.0)
    print(round(e["object_angle_deg"], 3), round(100 * e["relative_size_error"], 2))   # -2.951 6.89 / 0.006 -0.01
```

走らせて見るなら `py -3.11 examples/poc_telecentric_metrology.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
