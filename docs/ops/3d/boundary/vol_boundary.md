---
op: vol_boundary
dim: 3d
category: boundary
in: voxel
out: voxel
examples: [roi_domain_boundary]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_boundary — 3D `boundary` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_boundary(vol_binary, connectivity=6, side='inner')` (実装を直接呼ぶなら `import volops; volops.vol_boundary(vol_binary, connectivity=6, side='inner')`、台帳から引くなら `ops3d.get("vol_boundary")`)

## 使い方

Boundary shell of a binary volume (the 3-D ``region_boundary``).

``side='inner'`` keeps the foreground voxels that touch background:
``mask & ~erode(mask)``. ``side='outer'`` keeps the background voxels that
touch foreground: ``dilate(mask) & ~mask``. *connectivity* (6/18/26) decides
which neighbours count as "touching" — 6 uses face neighbours only (the
thinnest shell); 26 also counts a diagonal background contact, so shells at
convex corners come out thicker. The volume border counts as background
for the *inner* shell (a mask reaching the border has a boundary there —
the same convention as the surface-area estimate in
:func:`vol_region_props`); the *outer* shell can only occupy voxels that
exist, so a mask filling the whole volume has an empty outer boundary.

A solid region's interior drops out entirely: the shell of a solid ball of
radius ``r`` voxels is roughly a ``3/r`` fraction of it (surface over
volume), so the saving grows with size — which is exactly why boundary
representations (and :func:`vol_boundary_points`) are the memory-frugal way
to hand a shape to the point-cloud / metrology operators.

Returns a ``(D, H, W)`` float64 ``{0, 1}`` volume (chainable into
:func:`vol_label`, :func:`vol_boundary_points`, ...).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [roi_domain_boundary](../../../../examples_3d/roi_domain_boundary.py) — `py -3.11 examples_3d/roi_domain_boundary.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`boundary`)

[vol_boundary_points](vol_boundary_points.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
