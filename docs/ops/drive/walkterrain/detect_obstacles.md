---
op: detect_obstacles
dim: drive
category: walkterrain
in: depth
out: mask
gpu: なし
examples: [walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# detect_obstacles — DRIVE `walkterrain` op

- **データ種**: `depth` → `mask`
- **呼び出し**: `import fullseye as fs; fs.ledger.detect_obstacles(grid, cell: 'float' = 0.05, clearance: 'float' = 0.12, ground: 'str' = 'plane', ground_radius: 'float' = 0.4, trim: 'float' = 0.3, min_area: 'float' = 0.01, extent=None)` (実装を直接呼ぶなら `import terrain; terrain.detect_obstacles(grid, cell: 'float' = 0.05, clearance: 'float' = 0.12, ground: 'str' = 'plane', ground_radius: 'float' = 0.4, trim: 'float' = 0.3, min_area: 'float' = 0.01, extent=None)`、台帳から引くなら `opsdrive.get("detect_obstacles")`)
- **台帳経由の戻り値**: `fullseye.ledger.detect_obstacles(...)` は**宣言 out 型 `mask` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.detect_obstacles.raw(...)`、または `terrain.detect_obstacles` を直接呼ぶ。
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Segment cells rising more than *clearance* above the walkable ground.

The ground model isolates obstacles from a sloped surface: ``ground='plane'``
(default) fits a robust :func:`ground_plane` (best when the ground is planar —
flat or ramp); ``ground='opening'`` uses the morphological
:func:`ground_surface` envelope (best for rough/curved terrain); or pass a
precomputed ground height array. So a ramp is not an obstacle but a box, curb,
or rock on it is. Returns ``(mask, obstacles)``: a boolean obstacle mask and a
list of per-obstacle dicts sorted largest-first, each with ``area_cells`` /
``area`` (m²) / ``height`` (peak rise above ground) / ``centroid_cell``
(row, col) / ``bbox_cells`` (i0, j0, i1, j1), plus ``centroid_xy`` in world
units when *extent* (from :func:`elevation_map`) is given. Blobs smaller than
*min_area* (m²) are dropped as noise.

★``ground_radius`` は ``ground='opening'`` のときだけ読まれ、``trim`` は ``'plane'`` のときだけ。
空の入力(``grid`` が 0 要素)は空の mask と空の listを返す(理由: 観測の無い地図には障害物も無く、形だけを保つ)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`mask` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`walkterrain`)

[elevation_map](elevation_map.md) · [fill_gaps](fill_gaps.md) · [elevation_traversability](elevation_traversability.md) · [foothold_score](foothold_score.md) · [ground_surface](ground_surface.md) · [ground_plane](ground_plane.md) · [fuse_elevation](fuse_elevation.md) · [roughness_map](roughness_map.md)

---
*Provenance: terrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
