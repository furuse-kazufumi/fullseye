---
op: elevation_map
dim: drive
category: walkterrain
in: points
out: depth
gpu: なし
examples: [perception_pipeline, physical_ai_perception, walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# elevation_map — DRIVE `walkterrain` op

- **データ種**: `points` → `depth`
- **呼び出し**: `import fullseye as fs; fs.ledger.elevation_map(points, cell: 'float' = 0.05, agg: 'str' = 'max', bounds=None)` (実装を直接呼ぶなら `import terrain; terrain.elevation_map(points, cell: 'float' = 0.05, agg: 'str' = 'max', bounds=None)`、台帳から引くなら `opsdrive.get("elevation_map")`)
- **台帳経由の戻り値**: `fullseye.ledger.elevation_map(...)` は**宣言 out 型 `depth` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.elevation_map.raw(...)`、または `terrain.elevation_map` を直接呼ぶ。
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Bin a point cloud into a 2.5-D elevation grid.

Parameters
----------
points : (N, 3) array of (x, y, z), z = height.
cell   : grid resolution in world units.
agg    : 'max' (canopy / obstacle-safe, default), 'min' (ground), or 'mean'.
bounds : optional (xmin, xmax, ymin, ymax); defaults to the data extent.

Returns ``(grid, extent)`` where ``grid[i, j]`` is the aggregated height of
cell (row i = y, col j = x) and empty cells are ``nan``. ``extent`` is
``(xmin, xmax, ymin, ymax)``.

空の入力(``points`` が 0 要素)は ``bounds`` があれば全セル nan の格子を返す(理由: 観測の無い範囲は nan = 観測していない。``bounds`` が無ければ範囲が決まらないので ValueError)。
An empty cloud with ``bounds`` gives an all-``nan`` grid; without ``bounds`` it raises
``ValueError`` (no extent).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [perception_pipeline](../../../../examples/perception_pipeline.py) — `py -3.11 examples/perception_pipeline.py`
- [physical_ai_perception](../../../../examples/physical_ai_perception.py) — `py -3.11 examples/physical_ai_perception.py`
- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`walkterrain`)

[fill_gaps](fill_gaps.md) · [elevation_traversability](elevation_traversability.md) · [foothold_score](foothold_score.md) · [ground_surface](ground_surface.md) · [ground_plane](ground_plane.md) · [detect_obstacles](detect_obstacles.md) · [fuse_elevation](fuse_elevation.md) · [roughness_map](roughness_map.md)

---
*Provenance: terrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
