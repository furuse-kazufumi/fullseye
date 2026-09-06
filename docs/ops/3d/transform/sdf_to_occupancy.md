---
op: sdf_to_occupancy
dim: 3d
category: transform
in: sdf
out: voxel
examples: [transforms_repr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# sdf_to_occupancy — 3D `transform` op

- **データ種**: `sdf` → `voxel`
- **呼び出し**: `import match3d; match3d.sdf_to_occupancy(sdf, iso=0.0)` (または `ops3d.get("sdf_to_occupancy")`)

## 使い方

SDF → occupancy voxel(iso 以下=内側=1)。SDF から voxel へ戻す。

``(sdf <= iso).astype(float64)`` だけの op。``signed_distance_field`` の規約(内側 <0)なら
``iso=0.0`` で内側=1、外側=0。**等号を含む**ので、ちょうど ``iso`` の voxel は内側に入る。
``iso`` を正にすると外側へ ``iso`` voxel ぶん膨らんだ占有、負にすると縮んだ占有になる
(SDF が真の距離なら等方 dilation/erosion と同じ)。``tsdf_from_depth`` の出力(表面手前 +・
奥 −・未観測 +1)にも同じ ``iso=0.0`` で使えるが、未観測領域は 0 側(外)になる。
入力の形は問わず、返り値は同形の float64(0.0 / 1.0)。NaN は比較が偽なので 0 になる
(警告なし)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [signed_distance_field](signed_distance_field.md) · [to_points](to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [tsdf_from_depth](tsdf_from_depth.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
