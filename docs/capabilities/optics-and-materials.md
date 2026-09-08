---
id: optics-and-materials
title: 光の反射・屈折・干渉を計算する
title_en: Compute reflection, refraction and interference
category: 光と色
ops: [fresnel_dielectric, thin_film_reflectance, grating_rgb, refract_rays]
examples: [glass_and_mirror_optics, appearance_structural_colour]
version: 0.1.11
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

## 裏づけ

- op: `fresnel_dielectric` / `thin_film_reflectance` / `grating_rgb` / `refract_rays`
- 例: [`glass_and_mirror_optics`](../../examples/glass_and_mirror_optics.py)、[`appearance_structural_colour`](../../examples/appearance_structural_colour.py)
