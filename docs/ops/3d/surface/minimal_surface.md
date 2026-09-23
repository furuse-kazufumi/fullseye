---
op: minimal_surface
dim: 3d
category: surface
in: 
out: mesh
examples: [minimal_surfaces]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# minimal_surface — 3D `surface` op

- **データ種**: `なし` → `mesh`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.minimal_surface(kind='catenoid', nu=80, nv=120, extent=1.5, scale=1.0)` (実装を直接呼ぶなら `import render3d; render3d.minimal_surface(kind='catenoid', nu=80, nv=120, extent=1.5, scale=1.0)`、台帳から引くなら `ops3d.get("minimal_surface")`)

## 使い方

A classical minimal surface, from its exact parametrisation.

``catenoid`` ``(c cosh(u/c) cos v, c cosh(u/c) sin v, u)``, ``helicoid``
``(u cos v, u sin v, c v)``, ``enneper``
``(u - u^3/3 + u v^2, v - v^3/3 + v u^2, u^2 - v^2)`` and ``scherk``
``z = log(cos y / cos x)`` (the doubly periodic surface, over one cell).

★★**Why this earns its place — the definition is the gate.** A minimal surface
is one whose **mean curvature vanishes everywhere**, and the existing
``vertex_curvature`` op measures exactly that. So the claim "this is a minimal
surface" is checked by an op that knows nothing about how the surface was
built. ★A trap worth naming: the catenoid and the helicoid are *isometric*, so
their **Gaussian** curvatures agree pointwise — but that is a **necessary, not
sufficient** condition for minimality (a sphere and a plane differ in K, yet
matching K would not make either minimal). Grade on H.

Parameters
----------
kind : str
    One of ``MINIMAL_SURFACES``.
nu, nv : int
    Grid resolution along the two parameters.
extent : float
    Half-range of the first parameter (how much of the surface to take).
scale : float
    The surface's own scale parameter (``c`` for catenoid and helicoid).

Returns a ``mesh``: ``(vertices, faces)``.

**Raises** ``ValueError``: unknown kind; a grid below 4x4 or over the cap;
non-positive scale; an extent that reaches the singularity (Scherk's surface
is only defined where ``cos x`` and ``cos y`` share a sign, so an extent at or
beyond ``pi/2`` is refused rather than silently clipped to infinity).

HALCON: no operator.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [minimal_surfaces](../../../../examples_3d/minimal_surfaces.py) — `py -3.11 examples_3d/minimal_surfaces.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`surface`)

[minimal_surface_bend](minimal_surface_bend.md) · [gyroid_isosurface](gyroid_isosurface.md) · [gyroid_solid_mask](gyroid_solid_mask.md) · [curve3d_tube_mesh](curve3d_tube_mesh.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
