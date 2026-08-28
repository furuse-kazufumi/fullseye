---
op: snell_angle
dim: 3d
category: optics
in: measurement
out: measurement
examples: [snell_refraction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# snell_angle — 3D `optics` op

- **データ種**: `measurement` → `measurement`
- **呼び出し**: `import match3d; match3d.snell_angle(theta_i_deg, eta1=1.0, eta2=1.5)` (または `ops3d.get("snell_angle")`)

## 使い方

入射角(度)→ 屈折角(度)。n1 sinθi = n2 sinθt。臨界角超は NaN(全反射)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [snell_refraction](../../../../examples_3d/snell_refraction.py) — `py -3.11 examples_3d/snell_refraction.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](fresnel_reflectance.md)

## 同カテゴリ(`optics`)

[reflect](reflect.md) · [refract](refract.md) · [fresnel_reflectance](fresnel_reflectance.md) · [normal_from_reflection](normal_from_reflection.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
