---
id: shape-from-polarization
title: 黒光沢とガラスの形を偏光で測る(偏光からの形状復元・曖昧さの集合・屈折率の推定)
title_en: Measure the shape of black-glossy and glass parts from polarisation (shape from polarisation, the ambiguity set, refractive index)
category: 測る
ops: [sfp_dolp_model, dolp_to_zenith, aolp_to_azimuth, sfp_render, sfp_normals, sfp_disambiguate, sfp_estimate_index, sfp_height]
examples: [poc_shape_from_polarization]
version: 0.6.1
---

# 黒光沢とガラスの形を偏光で測る(偏光からの形状復元・曖昧さの集合・屈折率の推定)

## できること

4 方位のオンチップ偏光子を持つセンサの 1 ショットから、面の**法線**と**高さ**を出します。黒い光沢の樹脂やガラスのレンズは拡散反射がほとんど無く、照明を変えても陰影が出ないので、照度差ステレオや陰影からの形状復元が拠り所を失います。けれど表面で 1 回反射した光の偏光は、面の傾きで決まっています(Fresnel の式)。

- ★**偏光度 DoLP → 天頂角**。鏡面の DoLP は Brewster 角 `atan n` で厳密に 1 になり、その両側に同じ値が 2 回出ます(2 解)。拡散の DoLP は単調で 1 解ですが弱く、最大でも `(n²−1)/(n²+1)`。閉形式は、別の式で書かれた Fresnel(`glassmirror.fresnel_dielectric` の s / p 反射率)と 1e-14 で一致します。
- ★**偏光の方位 AoLP → 方位角**。鏡面は入射面に直交、拡散は平行に偏光するので 90° ずれ、偏光子にとって ψ と ψ+180° は同じなので π の曖昧さが残ります。
- ★★**曖昧さは集合のまま返します**。`sfp_normals` は画素ごとに法線の候補(鏡面 4 本 = 天頂角 2 × 方位 2、拡散 2 本)を返し、選びません。`sfp_disambiguate` が、明示した事前情報で 1 本を選びます: 「凸」(部品の中心から外を向く方位 + Brewster の稜線の内側は浅い枝、外側は深い枝)か、粗い深度・粗い法線(候補どうしの距離より近ければ十分)。
- ★**屈折率の推定**。DoLP の最大値は屈折率によらず 1 なので、効くのは「どこで」最大になるかです。較正球のように天頂角が分かっている面の DoLP に Fresnel の曲線を当てはめます(雑音 1 % で誤差 3e-4)。DoLP 最大の位置から `n = tan θ_B` を読む近道は雑音の山を拾うので(同じ条件で 1.71)、当てはめを使います。
- ★**高さ**は `photometric.integrate_gradients`(Frankot–Chellappa)を鏡像拡張した領域で使います。周期境界のまま積分すると傾いた平面が 18 px 曲がるのに対し、鏡像拡張では 0.06 px。
- ★★**どこで壊れるかを数で出します**: 屈折率の誤り(真値 1.57 を 1.50 と仮定すると中央値 0.89°、1.40 で 2.2°、谷は真値でちょうど 0)、雑音(誤差は Brewster の輪と頂点に集まる)、拡散の混入(30 % で平均 7.4°、偏光が 90° ずれて打ち消し合う)。

## What it does

Shape from polarisation for a 4-direction on-chip polariser sensor: the Fresnel DoLP of specular reflection (exactly 1 at Brewster's angle, two zenith solutions straddling it) and of diffuse emission (monotone, one solution), checked against the s/p reflectances of `glassmirror` written in a different form to 1e-14; AoLP to the two candidate azimuths (diffuse and specular 90° apart, the π ambiguity kept); the explicit candidate set of normals per pixel; disambiguation by a stated prior (convexity with Brewster-ridge segmentation, or a coarse depth / normal map); refractive-index estimation from DoLP at known zenith angles; and integration to height with a mirror-extended Frankot–Chellappa. Round trips through an independent Mueller-matrix forward path (`optics.mueller_element` / `mueller_apply`) recover analytic spheres, cylinders and rotated ellipsoids to 1e-9° (diffuse) and to 0.1° on the discrete Brewster ridge (specular). Where it breaks is measured: a wrong index, noise concentrated on the Brewster ring and at the apex, and a diffuse component mixed into a specular pixel.

## 向くところ / 向かないところ

- 単一の界面・単一の反射・正射影・一様な無偏光の環境光です。**透明体の裏面反射**(ガラスの裏から戻る光)と相互反射は入っていません。実物のガラスでは裏面反射が DoLP を下げ、天頂角を浅く読ませます。
- 金属(複素屈折率)は扱いません。拡散と鏡面が混ざった画素は、どちらのモデルで読んでも誤ります(混合比を推定する op はありません)。
- 凸の事前情報は部品ごとの mask に 1 つです。凹んだ部品や、Brewster の稜線が雑音で途切れた部品では効かないので、粗い深度(`prior="depth"`)を使います。
- 頂点付近(DoLP → 0)は方位が定まらず、Brewster の輪の上は天頂角の逆算が不安定です(DoLP の頂上が平ら)。
- 式は Fresnel の反射・透過係数から自分で導いて照合しました。Atkinson & Hancock(2006)の閉形式と同じ形ですが、**原論文の本文は読めていません**。Brewster の稜線で領域を分ける考えは Miyazaki ら(2003)に帰されますが、これも本文は未確認で、手順はこのライブラリで決めて測ったものです。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

# 球冠(半径 40 px の球の、像面の半径 36 px まで)の解析的な法線
yy, xx = np.mgrid[0:96, 0:96].astype(float)
x, y = (xx - 47.5) / 40.0, (yy - 47.5) / 40.0
mask = x * x + y * y < 0.9 ** 2
nz = np.sqrt(np.clip(1.0 - x * x - y * y, 0.0, 1.0))
normals = np.where(mask[..., None], np.dstack([x, y, nz]), [0.0, 0.0, 1.0])
normals /= np.linalg.norm(normals, axis=-1, keepdims=True)

sweep = fs.ledger.sfp_render(normals, 1.5, mask=mask)                 # 0/45/90/135° の 4 枚(黒光沢)
cands = fs.ledger.sfp_normals(sweep, 1.5, "specular")                 # 画素ごとに候補 4 本
est = fs.ledger.sfp_disambiguate(cands, "convex", mask=mask)          # 凸 + Brewster の稜線で 1 本
height = fs.ledger.sfp_height(est, mask=mask)
err = np.degrees(np.arccos(np.clip((est * normals).sum(-1), -1.0, 1.0)))[mask]
print("候補 %d 本、法線の誤差 最大 %.3f°、高さ %.1f px" % (cands["candidates"].shape[0], err.max(), height.max()))
```

## 裏づけ

- op: `sfp_dolp_model` / `dolp_to_zenith` / `aolp_to_azimuth` / `sfp_render` / `sfp_normals` / `sfp_disambiguate` / `sfp_estimate_index` / `sfp_height`
- 例: [`poc_shape_from_polarization`](../../examples/poc_shape_from_polarization.py) —— 黒光沢樹脂のドームとガラスのレンズを生のモザイク 1 枚から: 法線の誤差の中央値 0.53° / 1.09°、ドームの高さの RMS 誤差 0.62 px(高さ 37.9 px)。同じドームの照度差ステレオは中央値 26.4°(50 倍)。較正球で屈折率 1.5691(真値 1.57)。
- 既存 op と組む: `optics.polarization_demosaic`(センサのモザイク → 4 枚)・`specularity.polarization_dolp_map` / `polarization_separate`(同じ正弦波の当てはめ)・`glassmirror.fresnel_dielectric` / `brewster_angle_deg`・`photometric.integrate_gradients`
- 先行: M. Born & E. Wolf, *Principles of Optics*(Fresnel の式); G. A. Atkinson & E. R. Hancock, *IEEE Trans. Image Processing* 15(6):1653 (2006)(本文未確認); D. Miyazaki ほか, ICCV 2003(本文未確認)。
