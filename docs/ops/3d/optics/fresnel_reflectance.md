---
op: fresnel_reflectance
dim: 3d
category: optics
in: measurement
out: measurement
examples: [snell_refraction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fresnel_reflectance — 3D `optics` op

- **データ種**: `measurement` → `measurement`
- **呼び出し**: `import match3d; match3d.fresnel_reflectance(cos_i, eta1=1.0, eta2=1.5)` (または `ops3d.get("fresnel_reflectance")`)

## 使い方

Fresnel 反射率(無偏光=s/p 平均)。透明体界面で反射/透過に分かれる割合。

垂直入射で ((n1−n2)/(n1+n2))²(air→glass=0.04)。臨界角超で 1.0(全反射)。透明体レンダ/検査に。

``cos_i`` は入射角の余弦(実数スカラー。配列・None は ValueError)。符号は捨てる(``|cos_i|``)。
``eta1`` は入射側、``eta2`` は透過側の屈折率。s 偏光 ``rs`` と p 偏光 ``rp`` の平均を float で
返す(**[0, 1]**)。Brewster 角では ``rp = 0`` になるが平均は 0 にならない。``cos_i = 0``(かすめ
入射)で 1.0。透過率は ``1 −`` 反射率(吸収なし)。
用途: ``refract`` で曲げた光線の重み、透明体の輝度予測。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [snell_refraction](../../../../examples_3d/snell_refraction.py) — `py -3.11 examples_3d/snell_refraction.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [snell_angle](snell_angle.md)

## 同カテゴリ(`optics`)

[reflect](reflect.md) · [refract](refract.md) · [normal_from_reflection](normal_from_reflection.md) · [snell_angle](snell_angle.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
