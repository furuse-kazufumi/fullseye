---
id: optics-and-materials
title: 光の反射・屈折・干渉を計算する
title_en: Compute reflection, refraction and interference
category: 光と色
ops: [fresnel_dielectric, thin_film_reflectance, grating_rgb, refract_rays]
examples: [glass_and_mirror_optics, appearance_structural_colour]
version: 0.1.11
inputs: [signal, normalmap]
pipeline: [fresnel_dielectric, thin_film_reflectance, thin_film_rgb]
alternatives: [fresnel_conductor, brewster_angle_deg, grating_rgb, refract_rays, fresnel_reflectance]
limits: `refract` は 1 本でも全反射があるとバッチ全体が `None`(`refract_rays` を使う)。`fresnel_dielectric` は実屈折率のみ —— 金属は `fresnel_conductor`。
calibration: 波長 [nm]・屈折率は無次元、角度は cos で渡す。画素校正は不要。
---

# 光の反射・屈折・干渉を計算する

## できること

Fresnel の反射率、薄膜干渉の色、回折格子の色、ベクトル形の屈折(光線ごとの全反射判定つき)を、実在の硝材の分散を含めて計算します。

## What it does

Fresnel reflectance, thin-film interference colour, grating colour, and vector-form refraction with a per-ray total-internal-reflection mask — with the dispersion of real glasses.

## 向くところ / 向かないところ

**向く**: 外観のシミュレーション、照明設計、透明体を通した計測の補正。

**向かない**: ★バッチで屈折させるときは `refract_rays` を使ってください。`refract` は **1 本でも全反射があるとバッチ全体が `None`** になります(2026-09-08 まで、`refract` の説明はこのことに触れながら `refract_rays` の存在を書いていませんでした)。

## 最初の 1 本

```python
import fullseye as fs

r = fs.ledger.fresnel_dielectric(0.5, n1=1.0, n2=1.5168)   # cos(入射角)=0.5
print('反射率 =', r)
```

## 推奨パイプライン

`fresnel_dielectric` → `thin_film_reflectance` → `thin_film_rgb`

`fresnel_dielectric` で界面の反射率(s/p/無偏光)→ `thin_film_reflectance` で薄膜干渉の分光反射率 → `thin_film_rgb` で法線地図の上に色として載せる。

## 代替

金属は `fresnel_conductor`(n + ik)、偏光板で消える角は `brewster_angle_deg`、回折格子の色は `grating_rgb`、光線の屈折は `refract_rays`(全反射マスクつき)。

## 限界

`refract` は 1 本でも全反射があるとバッチ全体が `None`(`refract_rays` を使う)。`fresnel_dielectric` は実屈折率のみ —— 金属は `fresnel_conductor`。

## 実寸校正

波長 [nm]・屈折率は無次元、角度は cos で渡す。画素校正は不要。

## 裏づけ

- op: `fresnel_dielectric` / `thin_film_reflectance` / `grating_rgb` / `refract_rays`
- 例: [`glass_and_mirror_optics`](../../examples/glass_and_mirror_optics.py)、[`appearance_structural_colour`](../../examples/appearance_structural_colour.py)
