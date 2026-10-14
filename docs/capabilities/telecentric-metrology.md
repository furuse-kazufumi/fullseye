---
id: telecentric-metrology
title: テレセントリックレンズと寸法計測(主光線の傾き → 高さで変わる倍率 → ケラレとぼけ)
title_en: Telecentric lenses for dimensional metrology (chief-ray angle, magnification versus height, vignetting and blur)
category: 測る
ops: [telecentric_lens, chief_ray_angle, magnification_vs_depth, telecentricity_error, defocus_spot_vs_depth, vignetting_vs_field, lens_equivalent_pinhole]
examples: [poc_telecentric_metrology]
version: 0.6.1
---

# テレセントリックレンズと寸法計測(主光線の傾き → 高さで変わる倍率 → ケラレとぼけ)

## できること

段差のある部品(ボンディングのダイ、コネクタのピン、穴)の寸法を 1 枚の画像で測るとき、通常のレンズは近い面ほど大きく写すので、高さの違う面で同じ寸法が違う長さに写ります。`telecentric` の 7 本は `raytrace` の処方(`lens_system` の table)を実光線で追い、この誤差がどれだけ出てどれだけ消えるかを数字で返します。

`telecentric_lens` は同じ単レンズの絞りの位置だけを変えた 3 種(通常 / 物体側テレセン / 両側テレセン)を作り、`stop_shift_mm` で絞りをずらしてテレセン度を崩せます。`chief_ray_angle` は絞りの中心を通る主光線を Newton 法で探し、物体側の傾き(テレセン度)・像の高さ・実光線の入射瞳までの距離を返します。光線は入射瞳でなく絞りを狙うので、入射瞳が無限遠の物体側テレセンでも動きます(`raytrace.chief_ray` はここで止まります)。`magnification_vs_depth` は像面を固定して物体を動かしたときの倍率、`telecentricity_error` は段差の上下で寸法の読みが何 % 狂うかを主光線の幾何 Δz·tanθ と並べて返します。`defocus_spot_vs_depth` は瞳を総当たりで埋めた光線束のぼけの RMS、`vignetting_vs_field` は前玉で光束が欠ける割合(テレセンの視野は前玉径で決まる)、`lens_equivalent_pinhole` は主光線の幾何を `render3d.render_mesh` のピンホール(入射瞳の位置)に写します。

PoC `poc_telecentric_metrology` は、倍率の変化が閉形式 L/(L − Δz) と 7e-5 で一致すること、絞りのずれが Newton の式どおりに入射瞳を動かすこと、ぼけの RMS の傾きが |m|·NA/√2 になることを採点し、ピン・ダイ・穴を 3 種のレンズで描いて、画像から測った寸法の読みと穴の底の見える割合を閉形式と突き合わせます。

## What it does

Seven ops in `telecentric` (category `telecentric` of `opsoptics`) on top of the `raytrace` prescriptions: a generator of the same singlet with the stop moved (entocentric, object-side telecentric, bi-telecentric, plus a stop shift that spoils telecentricity), the real chief ray found by aiming at the stop itself rather than at the entrance pupil (so it works with the pupil at infinity), the magnification versus object height on a fixed image plane, the dimensional error across a step, the RMS defocus blur from a brute-force pupil bundle, the vignetting set by the front lens, and a pinhole camera at the entrance pupil for `render3d`. The PoC gates the magnification against L/(L − Δz), the stop shift against Newton's equation, the blur slope against |m|·NA/√2, and measurements taken from rendered images against circle-overlap closed forms.

## 向くところ / 向かないところ

**向く**: 寸法検査のレンズ選び(段差の高さと視野の位置から、通常のレンズで何 % 狂うか)、テレセン度の仕様(0.1° なら段差 1 mm で 1.75 µm)の意味の確認、テレセンの視野と前玉径の見積り、被写界深度と NA の取引、検査の画像を正しい幾何で合成するためのカメラ。

**向かない**: ★処方は単レンズの組み合わせで、実機のテレセン(5〜10 枚)の瞳収差と歪曲の補正は入っていません(物体側テレセンの単レンズは物高 8 mm で歪曲 3 %、テレセン度 0.05° が残ります)。カタログの処方があれば `lens_system` に面を並べて同じ op を使えます。物体が無限遠の処方は拒否します。`lens_equivalent_pinhole` は近軸の幾何の写しで、歪曲・瞳収差・ハイパーセントリック(入射瞳が物体の裏)は描画に入りません(後者は ValueError)。回折は扱わず、ぼけは幾何光学の光線束です。

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
