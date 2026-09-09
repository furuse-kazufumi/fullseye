---
op: snell_angle
dim: 3d
category: optics
in: measurement
out: measurement
examples: [snell_refraction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# snell_angle — 3D `optics` op

- **データ種**: `measurement` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.snell_angle(theta_i_deg, eta1=1.0, eta2=1.5)` (実装を直接呼ぶなら `import match3d; match3d.snell_angle(theta_i_deg, eta1=1.0, eta2=1.5)`、台帳から引くなら `ops3d.get("snell_angle")`)

## 使い方

入射角(度)→ 屈折角(度)。n1 sinθi = n2 sinθt。臨界角超は NaN(全反射)。

``θt = arcsin((eta1/eta2)·sin θi)`` を度で返す(float)。``theta_i_deg`` は実数スカラー(配列・
None は ValueError)。符号は保たれる(負の入射角は負の屈折角)。``|(eta1/eta2) sin θi| > 1`` なら
``nan``(全反射。``eta1 > eta2`` のときだけ起きる)。臨界角は ``degrees(arcsin(eta2/eta1))``。
``eta1 == eta2`` なら入射角そのまま。
ベクトルで曲げるなら ``refract``(バッチは :func:`glassmirror.refract_rays`。
``refract`` は 1 本でも TIR があるとバッチ全体が ``None`` になる)、反射率は
``fresnel_reflectance(cos(radians(θi)))``。**角度を配列でまとめて曲げる口は無い** ——
音響のように屈折率でなく速度で考える場合は ``eta = 1/c`` を渡す(n ∝ 1/c)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [snell_refraction](../../../../examples_3d/snell_refraction.py) — `py -3.11 examples_3d/snell_refraction.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](fresnel_reflectance.md)

## 同カテゴリ(`optics`)

[reflect](reflect.md) · [refract](refract.md) · [fresnel_reflectance](fresnel_reflectance.md) · [normal_from_reflection](normal_from_reflection.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
