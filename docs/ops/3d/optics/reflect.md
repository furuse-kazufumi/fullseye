---
op: reflect
dim: 3d
category: optics
in: vector × normals
out: vector
examples: [sensor_seg, snell_refraction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# reflect — 3D `optics` op

- **データ種**: `vector × normals` → `vector`
- **呼び出し**: `import match3d; match3d.reflect(d, n)` (または `ops3d.get("reflect")`)

## 使い方

入射方向 d を法線 n の面で鏡面反射。r = d − 2(d·n)n。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sensor_seg](../../../../examples_3d/sensor_seg.py) — `py -3.11 examples_3d/sensor_seg.py`
- [snell_refraction](../../../../examples_3d/snell_refraction.py) — `py -3.11 examples_3d/snell_refraction.py`

## 型が繋がる次の op(`vector` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [refract](refract.md) · [normal_from_reflection](normal_from_reflection.md) · [cast_shadow](../render/cast_shadow.md)

## 同カテゴリ(`optics`)

[refract](refract.md) · [fresnel_reflectance](fresnel_reflectance.md) · [normal_from_reflection](normal_from_reflection.md) · [snell_angle](snell_angle.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
