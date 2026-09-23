---
op: geodesic_dome
dim: 3d
category: polyhedron
in: 
out: mesh
examples: [geodesic_dome]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# geodesic_dome — 3D `polyhedron` op

- **データ種**: `なし` → `mesh`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.geodesic_dome(frequency=3, radius=1.0, hemisphere=False)` (実装を直接呼ぶなら `import render3d; render3d.geodesic_dome(frequency=3, radius=1.0, hemisphere=False)`、台帳から引くなら `ops3d.get("geodesic_dome")`)

## 使い方

Geodesic sphere from a subdivided icosahedron — Euler decides the shape.

Each icosahedron face is cut into ``frequency**2`` triangles and every vertex
is pushed out to the sphere. The counts are then **forced**, not chosen:
``F = 20*f**2``, ``E = 30*f**2``, ``V = 10*f**2 + 2``, and Euler's formula
``V - E + F == 2`` holds exactly.

★**Why this earns its place**: Euler also forces the *irregularity*. If every
vertex had degree 6 then ``2E = 6V``, which contradicts ``V - E + F = 2``;
counting degrees gives ``sum(6 - deg(v)) == 12`` over all vertices, so a
triangulated sphere built from hexagons must contain **exactly twelve**
pentagons — no more, no fewer, at any frequency. That is why a football has
twelve black patches, and it is an integer this operator must reproduce
exactly. Nothing about the drawing can be "close enough".

Returns a ``mesh`` ``(V, F)``: ``V`` is ``(n, 3)`` float, ``F`` is ``(m, 3)``
int. With ``hemisphere=True`` the vertices below ``z = 0`` and the faces
touching them are dropped (then Euler no longer gives 2, and the
twelve-pentagon count applies to the full sphere only — said here rather
than letting the gate quietly change meaning).

**Raises** ``ValueError``: ``frequency < 1``; ``radius <= 0``; the mesh would
exceed the cap.

HALCON: no operator (``gen_sphere_object_model_3d`` makes a UV sphere, whose
poles are degenerate — a different object).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geodesic_dome](../../../../examples_3d/geodesic_dome.py) — `py -3.11 examples_3d/geodesic_dome.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`polyhedron`)

—

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
