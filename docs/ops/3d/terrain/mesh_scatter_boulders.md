---
op: mesh_scatter_boulders
dim: 3d
category: terrain
in: mesh
out: mesh
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# mesh_scatter_boulders — 3D `terrain` op

- **データ種**: `mesh` → `mesh`
- **呼び出し**: `import render3d; render3d.mesh_scatter_boulders(V, F, *, density: 'float', d_min: 'float', d_max=None, exponent: 'float' = 3.1, seed: 'int' = 0, region_weights=None, aspect=(1.0, 0.7, 0.5), embed: 'float' = 0.35, subdiv: 'int' = 1, shape: 'str' = 'ellipsoid', orientation: 'str' = 'normal', burial=(0.3, 0.6), max_count=None, hull_points=None, return_info: 'bool' = False)` (または `ops3d.get("mesh_scatter_boulders")`)

## 使い方

Scatter partly-buried boulders on a mesh (power-law sizes, seeded) → ``(V, F)``

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_regolith_hero](../../../../examples_3d/itokawa_regolith_hero.py) — `py -3.11 examples_3d/itokawa_regolith_hero.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`terrain`)

[mesh_displace_fbm](mesh_displace_fbm.md) · [terrain_region_mask](terrain_region_mask.md) · [mesh_edge_lengths](mesh_edge_lengths.md) · [mesh_subdivide](mesh_subdivide.md) · [displacement_band_weights](displacement_band_weights.md) · [mesh_displace_spectrum](mesh_displace_spectrum.md) · [bump_normals_fbm](bump_normals_fbm.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
