---
op: normal_from_reflection
dim: 3d
category: optics
in: vector × vector
out: normals
examples: [sensor_seg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# normal_from_reflection — 3D `optics` op

- **データ種**: `vector × vector` → `normals`
- **呼び出し**: `import match3d; match3d.normal_from_reflection(incident, reflected)` (または `ops3d.get("normal_from_reflection")`)

## 使い方

入射+反射から鏡面の法線を復元(deflectometry)。n ∝ (r − d)、入射に逆らう向きへ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sensor_seg](../../../../examples_3d/sensor_seg.py) — `py -3.11 examples_3d/sensor_seg.py`

## 型が繋がる次の op(`normals` を入力に取れる)

[icp_point2plane](../refine/icp_point2plane.md) · [compute_fpfh](../feature_register/compute_fpfh.md) · [shot_descriptor](../feature_register/shot_descriptor.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [reflect](reflect.md) · [refract](refract.md) · [render_shaded](../render/render_shaded.md) · [phong_shade](../render/phong_shade.md)

## 同カテゴリ(`optics`)

[reflect](reflect.md) · [refract](refract.md) · [fresnel_reflectance](fresnel_reflectance.md) · [snell_angle](snell_angle.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
