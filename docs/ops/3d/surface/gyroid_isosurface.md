---
op: gyroid_isosurface
dim: 3d
category: surface
in: 
out: mesh
examples: [minimal_surfaces]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# gyroid_isosurface — 3D `surface` op

- **データ種**: `なし` → `mesh`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.gyroid_isosurface(shape=(64, 64, 64), level=0.0, periods=1.0)` (実装を直接呼ぶなら `import render3d; render3d.gyroid_isosurface(shape=(64, 64, 64), level=0.0, periods=1.0)`、台帳から引くなら `ops3d.get("gyroid_isosurface")`)

## 使い方

The gyroid — a triply periodic surface from its nodal approximation.

Samples ``sin x cos y + sin y cos z + sin z cos x`` over ``periods`` unit
cells and extracts the level set. At ``level = 0`` the field is **odd under
the body-centred inversion**, so the two sides have exactly equal volume —
a symmetry fact, independent of the meshing, that the existing
``mesh_volume`` can be pointed at.

★**Honest limit, stated in the contract**: this is the *nodal approximation*
to the gyroid, not the exact triply periodic minimal surface. Schoen's gyroid
has ``H = 0`` everywhere; the nodal surface has a residual mean curvature
(measured, not hidden) of about **12 % of the principal-curvature scale** at a
64³ grid —— compare the exact families in :func:`minimal_surface`, whose
``|H|`` median is 1e-4 against a curvature scale of order 1. Use the gyroid as
a scaffold and a picture, not as a claim of minimality.

Parameters
----------
shape : (nz, ny, nx)
level : float
    Iso value. 0 gives the balanced surface; non-zero splits the volume.
periods : float
    Unit cells along each axis.
Returns a ``mesh`` (vertices, faces).

★The thickened **solid** form lives in :func:`gyroid_solid_mask`, not behind
a keyword here —— one function that returns a mesh or a volume depending on an
argument cannot be given a single declared output type, and a ledger row that
lies about its output is the defect class this library keeps catching
(``indices_to_labels``: one word covering a 1-D mask and a 3-D volume).

**Raises** ``ValueError``: a grid below 8 per axis or over the cap;
non-positive periods; a level outside the field's range (no surface exists
there — reported rather than returning an empty mesh); negative thickness.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [minimal_surfaces](../../../../examples_3d/minimal_surfaces.py) — `py -3.11 examples_3d/minimal_surfaces.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`surface`)

[minimal_surface](minimal_surface.md) · [minimal_surface_bend](minimal_surface_bend.md) · [gyroid_solid_mask](gyroid_solid_mask.md) · [curve3d_tube_mesh](curve3d_tube_mesh.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
