---
op: mesh_subdivide
dim: 3d
category: terrain
in: mesh
out: mesh
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# mesh_subdivide — 3D `terrain` op

- **データ種**: `mesh` → `mesh`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_subdivide(V, F, *, levels: 'int' = 1, target_edge=None, max_faces: 'int' = 4000000)` (実装を直接呼ぶなら `import render3d; render3d.mesh_subdivide(V, F, *, levels: 'int' = 1, target_edge=None, max_faces: 'int' = 4000000)`、台帳から引くなら `ops3d.get("mesh_subdivide")`)

## 使い方

Refine a triangle mesh → ``(V, F)``: uniform midpoint subdivision (``levels`` passes,

×4 faces each) or **adaptive tessellation to a target edge length** (``target_edge``:
median edge = target, edge segments ≤ 1.5×target, in-face Delaunay edges < 2×target).

The geometry is *unchanged* — every new vertex lies on an old facet, so surface area
and enclosed volume are preserved exactly (tests pin this) and nothing is ever
decimated; only the facet size changes, so a later :func:`mesh_displace_spectrum` can
carry short wavelengths without aliasing.

Adaptive mode cuts each edge into ``n = round(length / target_edge)`` (≥ 1) segments
— a per-*edge* count, hence conforming across neighbours (no T-junctions) — and fills
each face with a **hexagonal lattice at spacing ``target_edge`` in the face plane**,
triangulated by a per-face 2-D Delaunay (Qhull). The interior therefore has edges
≈ ``target_edge`` *whatever the shape of the source face* (the Gaskell Itokawa faces
have a median longest/shortest edge ratio of 1.83, so a per-face lattice pattern
inherits that anisotropy; repeated midpoint bisection additionally leaves a factor-2
spread ``(target/2, target]``). Measured on the Itokawa model (edge p5/median/p95 =
2.6/4.7/7.2 m, target 1.5 m): see ``examples_3d/itokawa_regolith_hero.py`` — the test
pins p95/p5 ≤ 1.5 on a graded plane. ``max_faces`` (default
``MAX_SUBDIVIDE_FACES``) is a memory guard: if the plan would exceed it the call
raises ``ValueError`` (fail-closed) rather than silently under-refining.
Deterministic. Fail-closed: degenerate mesh, ``levels < 0``, non-positive
``target_edge`` / caps → ``ValueError``.

2 つのモードがあり、``target_edge`` の有無で切り替わる。

- ``target_edge=None``(一様): 全辺を中点で割る細分を ``levels`` 回繰り返す(面数は
  1 回ごとに 4 倍)。``levels=0`` は入力をそのまま返す。各回の前に ``面数×4 > max_faces``
  なら ``ValueError``。
- ``target_edge`` 指定(適応): 辺ごとに分割数 ``n = round(長さ / target_edge)``
  (最小 1)を決め、隣接面で共有するので T 字接合は出ない。分割数は内部上限 64 に
  **無言でクランプ** されるため、``target_edge`` の 64 倍を超える長さの辺は目標に届かない。
  どの辺も分割不要なら入力のコピーを返す。面数の見積り
  ``Σ(3 辺の分割数の和 + 平均分割数²)`` が ``max_faces`` を超えると計算前に
  ``ValueError``。``levels`` はこのモードでは使わない。

返り値 ``(V (N',3) float64, F (M',3) int64)``。新頂点は必ず元の面の上に置くので面積と
体積は変わらない(平滑化ではない)。適応モードは面ごとに 2-D Delaunay(scipy Qhull)を
使うので、極端に細長い面では品質が落ちる。細分後に ``mesh_edge_lengths`` で辺長分布を
確かめ、``mesh_displace_spectrum`` へ渡す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_regolith_hero](../../../../examples_3d/itokawa_regolith_hero.py) — `py -3.11 examples_3d/itokawa_regolith_hero.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`terrain`)

[mesh_displace_fbm](mesh_displace_fbm.md) · [terrain_region_mask](terrain_region_mask.md) · [mesh_scatter_boulders](mesh_scatter_boulders.md) · [mesh_edge_lengths](mesh_edge_lengths.md) · [displacement_band_weights](displacement_band_weights.md) · [mesh_displace_spectrum](mesh_displace_spectrum.md) · [bump_normals_fbm](bump_normals_fbm.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
