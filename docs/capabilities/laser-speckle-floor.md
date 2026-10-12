---
id: laser-speckle-floor
title: レーザー光切断の誤差の床はスペックルが決める(コヒーレント結像・スペックルの統計・三角測量の不確かさ)
title_en: Speckle sets the error floor of laser sheet-of-light (coherent imaging, speckle statistics and triangulation uncertainty)
category: 測る
ops: [coherent_image, speckle_field, speckle_statistics, laser_line_coherent, triangulation_speckle_limit, speckle_reduction]
examples: [poc_laser_line_speckle_floor]
version: 0.6.1
---

# レーザー光切断の誤差の床はスペックルが決める(コヒーレント結像・スペックルの統計・三角測量の不確かさ)

## できること

レーザーで照らした粗面を、**コヒーレント結像**で撮ります。面の凹凸が波長より大きいと反射光の位相は場所ごとにでたらめになり、カメラの開口(瞳)で帯域を切られた**複素振幅**が干渉して粒々の模様(スペックル)になります。光切断やレーザー変位計の高さの誤差の下限は、画素の雑音ではなくこの粒で決まります。

- ★**コヒーレント結像は振幅で線形です**。位相格子の 0 次だけを瞳に通すと強度は一様な `J0(a)²`、0 と ±1 次を通すと `J0² + 4 J1² sin²` の縞になり、どちらも閉形式と 1e-12 で一致します(インコヒーレントなら位相物体は何も写りません)。
- ★★**Goodman の定理どおりのスペックル**です。完全発達・単一偏光の強度は指数分布(コントラスト C = 0.993、KS p ≥ 0.24)、偏光 2 本や独立な N 枚の和は N 次のガンマ分布(C·√N = 0.990〜1.003)。粗さが波長に比べて小さいときは「定数の位相子 + 非円形のガウス雑音」の閉形式と 2.4 % 以内で合い、円形を仮定した Rice の式は 22〜46 % 外れます。
- ★**粒の大きさ**は強度の自己相関の半値全幅 `0.5145 λ / sin u` で、瞳の半径に対する log-log の傾きは −0.997、自己相関の断面は円形瞳の `|2 J1(x)/x|²` と 0.02 以内で重なります。
- ★**画素の積分**でコントラストが下がる量は、Goodman の積分スペックルの定義式(正方形画素の重なり関数 × Airy²)を数値積分した値と 1.2 % 以内で一致します。粒が画素よりずっと小さいときは `πρc²C² → 1`(相関面積 / 画素面積)に近づきます。
- ★★**三角測量の誤差の床** `δz = C·λ / (2π sin u sin θ)`(Dorsch, Häusler & Herrmann 1994)を返し、スペックル込みで描いた光条から実測した中心の標準偏差が λ に +1、sin u と sin θ に −1 の指数で比例することを確かめてあります。比例定数(実測 / 式)は 0.84〜0.91 で、門にはせず開示しています。
- ★**重心の誤差は画素の大きさによりません**。箱で積分した強度の重心は元の強度の重心と同じなので、画素を 4 倍にして見た目のコントラストが 1.02 → 0.80 に鈍っても、重心は 1.6e-13 µm しか動きません。式の C は「見た目のコントラスト」ではありません。

## What it does

Coherent imaging of rough surfaces under laser light: an amplitude/phase object through the coherent transfer function (verified against Bessel closed forms to 1e-12), laser speckle from a random phase screen with finite roughness, polarisation and pattern diversity and pixel integration, speckle statistics (contrast, Kolmogorov–Smirnov against the exponential and gamma laws, autocorrelation width compared with the Airy pattern), a speckled sheet-of-light laser line, and the speckle-limited height uncertainty of triangulation, δz = C·λ/(2π sin u sin θ). The exponents (+1 in wavelength, −1 in the observation aperture and the triangulation angle) are gated against centroids measured on rendered lines; the constant is disclosed (measured / formula = 0.84–0.91), because the primary paper's text was not available to check its 2π factor. Static speckle does not average away over frames; a moving part does, as 1/√N.

## 向くところ / 向かないところ

- スカラ回折・近軸・倍率 1(物体側の座標)・**焦点の合った平面**の粗面です。前縮み(斜めから見た光条の見かけの幅が cos θ 倍になる)・Scheimpflug・デフォーカス・体積散乱・多重散乱は入っていません。
- 粗面は物体側の細格子の 1 点ごとに独立な位相(相関長 0)。観察開口が相関長より粗く切っていれば統計は同じですが、細格子が粗すぎる(1 粒に 2 点)と三角測量の指数が 1.13 まで反ることを実測しています。1 粒に 4 点以上で使ってください(`pixel_oversample`)。
- 重心の誤差は光条の幅 w と平均する長さ L に √(w/L) で依存します。「スポットの大きさによらない」という Dorsch の言い方は L ≈ w の場合に当たります。
- Dorsch らの式は**原論文の本文を読めていません**(抄録のみ)。2π の係数は二次文献の引用の形です。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

# 完全発達のスペックル: コントラスト 1、指数分布、粒径 0.5145/ρc 画素
st = fs.ledger.speckle_statistics(fs.ledger.speckle_field((256, 256), cutoff=0.1, seed=0))
print("C = %.3f / KS p = %.2f / 粒 %.2f 画素(式 %.2f)"
      % (st["contrast"], st["ks_p_exponential"], st["speckle_fwhm_px"], 0.5145 / 0.1))

# 光切断の光条(λ 0.65 µm、sin u 0.03、θ 30°、物体側の画素 5 µm)と誤差の床
img = fs.ledger.laser_line_coherent(shape=(49, 256), wavelength_um=0.65, sin_u_obs=0.03,
                                    pixel_um=5.0, line_width_um=14.0, sin_theta=0.5, seed=1)
lim = fs.ledger.triangulation_speckle_limit(0.65, 0.03, 0.5)
print("δz の床 %.2f µm、粒 %.1f µm" % (lim["delta_z_um"], lim["speckle_fwhm_um"]))
```

## 裏づけ

- op: `coherent_image` / `speckle_field` / `speckle_statistics` / `laser_line_coherent` / `triangulation_speckle_limit` / `speckle_reduction`
- 例: [`poc_laser_line_speckle_floor`](../../examples/poc_laser_line_speckle_floor.py) —— 加法雑音で輝度最大の画素より 8.6 倍良かった 3 点当てはめが、スペックルでは輝度最大と同じ誤差(12.7 vs 13.1 µm)に落ち、重心(6.4 µm、Dorsch の床の 0.93 倍)の 2 倍悪い。静止した部品は 100 枚平均しても 0.98 倍、部品を動かすと 0.099 倍。
- 既存 op と組む: `lensimage` の `psf_from_opd` / `render_through_lens`(インコヒーレント結像)・`optscene` の `light_spec`(光源の `coherent` の印)・`measure_profile_sheet_of_light`(光切断の処理)
- 先行: J. W. Goodman, *Speckle Phenomena in Optics*, 2007; J. W. Goodman, *Introduction to Fourier Optics*, 3rd ed., 2005; R. G. Dorsch, G. Häusler, J. M. Herrmann, *Appl. Opt.* 33(7):1306 (1994)。
