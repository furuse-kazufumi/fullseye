---
op: gyroid_solid_mask
dim: 3d
category: surface
in: 
out: voxel
examples: [minimal_surfaces]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# gyroid_solid_mask — 3D `surface` op

- **データ種**: `なし` → `voxel`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.gyroid_solid_mask(shape=(64, 64, 64), level=0.0, periods=1.0, thickness=0.3)` (実装を直接呼ぶなら `import render3d; render3d.gyroid_solid_mask(shape=(64, 64, 64), level=0.0, periods=1.0, thickness=0.3)`、台帳から引くなら `ops3d.get("gyroid_solid_mask")`)

## 使い方

The gyroid as a printable **solid**: the shell within ±*thickness* of the level set.

Returns a ``volume`` (float 0/1), so it feeds the existing voxel ops
(``vol_label`` / ``skeletonize_vol`` / ``mesh_slice_stack``) directly and needs
no marching cubes —— this form works on bare numpy, while
:func:`gyroid_isosurface` needs scikit-image.

★**Why this earns its place**: at ``level = 0`` the field is odd under the
body-centred inversion, so the solid fraction of the two sides is *exactly*
equal —— a symmetry fact the mask can be checked against (the measured
fraction above 0 converges on 0.5 as the grid refines), and the shell volume
grows linearly in *thickness* for small *thickness* because the level set has
finite area. Both are independent of how the field was sampled.

**Raises** ``ValueError``: a grid below 8 per axis or over the cap;
non-positive periods; a non-finite level; a negative thickness.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [minimal_surfaces](../../../../examples_3d/minimal_surfaces.py) — `py -3.11 examples_3d/minimal_surfaces.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`surface`)

[minimal_surface](minimal_surface.md) · [minimal_surface_bend](minimal_surface_bend.md) · [gyroid_isosurface](gyroid_isosurface.md) · [curve3d_tube_mesh](curve3d_tube_mesh.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
