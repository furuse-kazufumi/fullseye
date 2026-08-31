---
op: vol_resize
dim: 3d
category: geom_transform
in: voxel
out: voxel
examples: [vol_geometry_transform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# vol_resize — 3D `geom_transform` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import volxform; volxform.vol_resize(vol, factor=None, shape=None, order=1, spacing=None)` (または `ops3d.get("vol_resize")`)

## 使い方

Resample a volume to a new grid (``scipy.ndimage.zoom``, cell semantics).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [vol_geometry_transform](../../../../examples_3d/vol_geometry_transform.py) — `py -3.11 examples_3d/vol_geometry_transform.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`geom_transform`)

[vol_rotate](vol_rotate.md) · [vol_affine](vol_affine.md)

---
*Provenance: volxform.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
