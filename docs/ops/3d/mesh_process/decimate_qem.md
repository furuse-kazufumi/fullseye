---
op: decimate_qem
dim: 3d
category: mesh_process
in: mesh
out: mesh
examples: [mesh_decimate, mesh_lod_download, mesh_resolution_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# decimate_qem — 3D `mesh_process` op

- **データ種**: `mesh` → `mesh`
- **呼び出し**: `import meshrepair; meshrepair.decimate_qem(V, F, target_faces, protect=None)` (または `ops3d.get("decimate_qem")`)

## 使い方

Quadric-error-metric edge-collapse decimation toward *target_faces*.

*protect* (optional, (nv,) bool): vertices that must survive untouched —
no edge incident to a protected vertex is collapsed, so the faces around a
crater rim, a boulder or any region you flagged keep their exact geometry
(``meshres.mesh_decimate_preserving`` derives the mask from the detail map
and reports what the rest of the reduction lost).

Garland & Heckbert 1997: each vertex carries the sum of the squared-distance
quadrics of its incident face planes; the cheapest edge is collapsed to the
position minimising that quadric (a midpoint/endpoint fallback when the 3x3
system is singular, e.g. on a flat face), quadrics are accumulated onto the
surviving vertex, and incident edge costs are re-queued. Collapses that would
flip a face normal or land on a non-manifold edge are skipped, so the result
stays a sane surface.

Honest scope: this is a **practical** QEM, not production-grade. It has no
boundary-preservation term, no attribute (colour/UV) quadrics and no
aggressive validity recovery, so on awkward meshes a few non-ideal collapses
can survive and the collapse may stop a little short of *target_faces* when
every remaining candidate is blocked by the flip/manifold guard. Good enough
for a cheap collision proxy; not a replacement for a dedicated remesher.

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_decimate](../../../../examples_3d/mesh_decimate.py) — `py -3.11 examples_3d/mesh_decimate.py`
- [mesh_lod_download](../../../../examples_3d/mesh_lod_download.py) — `py -3.11 examples_3d/mesh_lod_download.py`
- [mesh_resolution_demo](../../../../examples_3d/mesh_resolution_demo.py) — `py -3.11 examples_3d/mesh_resolution_demo.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`mesh_process`)

[laplacian_smooth](laplacian_smooth.md) · [taubin_smooth](taubin_smooth.md) · [face_normals](face_normals.md) · [vertex_normals](vertex_normals.md) · [mesh_area](mesh_area.md) · [vertex_curvature](vertex_curvature.md)

---
*Provenance: meshrepair.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
