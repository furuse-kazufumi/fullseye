---
op: voxel_to_mips
dim: 3d
category: transform
in: voxel
out: images
examples: [transforms_repr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# voxel_to_mips — 3D `transform` op

- **データ種**: `voxel` → `images`
- **呼び出し**: `import match3d; match3d.voxel_to_mips(vol)` (または `ops3d.get("voxel_to_mips")`)

## 使い方

3D → 直交 3 方向の最大値投影(MIP)。2D 手法(accel の 2D NCC 等)を適用する入口。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`

## 型が繋がる次の op(`images` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [photometric_stereo](../photometric/photometric_stereo.md) · [wrapped_phase](../structured_light/wrapped_phase.md) · [graycode_decode](../structured_light/graycode_decode.md) · [decode_fringe](../structured_light/decode_fringe.md) · [carve](../space_carving/carve.md) · [visual_hull](../space_carving/visual_hull.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mesh](voxel_to_mesh.md) · [tsdf_from_depth](tsdf_from_depth.md) · [signed_distance_field](signed_distance_field.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
