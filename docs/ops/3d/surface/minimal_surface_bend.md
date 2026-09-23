---
op: minimal_surface_bend
dim: 3d
category: surface
in: 
out: mesh
examples: [minimal_surfaces]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# minimal_surface_bend — 3D `surface` op

- **データ種**: `なし` → `mesh`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.minimal_surface_bend(t=0.0, nu=80, nv=120, extent=1.5, scale=1.0)` (実装を直接呼ぶなら `import render3d; render3d.minimal_surface_bend(t=0.0, nu=80, nv=120, extent=1.5, scale=1.0)`、台帳から引くなら `ops3d.get("minimal_surface_bend")`)

## 使い方

The catenoid-helicoid bend — every member of the family is still minimal.

The *associate family* ``cos(t) * helicoid + sin(t) * catenoid`` (in the
Weierstrass sense) deforms one into the other **without stretching**: the
surfaces are isometric at every ``t``, and every one of them is minimal.
``t = 0`` is the helicoid, ``t = pi/2`` the catenoid.

★**Why this earns its place**: it turns "minimal" from a property of two
named surfaces into a **one-parameter claim that must hold throughout**. If
an implementation is only accidentally right at the endpoints, the middle of
the family exposes it — and the intrinsic geometry (first fundamental form)
must not change along the way, which is a second, independent check.

Returns a ``mesh``.

**Raises** ``ValueError``: the same shape/scale contracts as
:func:`minimal_surface`; a non-finite ``t``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [minimal_surfaces](../../../../examples_3d/minimal_surfaces.py) — `py -3.11 examples_3d/minimal_surfaces.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`surface`)

[minimal_surface](minimal_surface.md) · [gyroid_isosurface](gyroid_isosurface.md) · [gyroid_solid_mask](gyroid_solid_mask.md) · [curve3d_tube_mesh](curve3d_tube_mesh.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
