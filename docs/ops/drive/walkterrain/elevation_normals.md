---
op: elevation_normals
dim: drive
category: walkterrain
in: depth
out: normalmap
gpu: なし
examples: [walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# elevation_normals — DRIVE `walkterrain` op

- **データ種**: `depth` → `normalmap`
- **呼び出し**: `import fullseye as fs; fs.ledger.elevation_normals(grid, cell: 'float' = 0.05)` (実装を直接呼ぶなら `import terrain; terrain.elevation_normals(grid, cell: 'float' = 0.05)`、台帳から引くなら `opsdrive.get("elevation_normals")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Unit up-pointing normals (H, W, 3) of an elevation map — ledger door of :func:`surface_normals`.

地形の高さ図の単位法線(+z 向き)。中身は :func:`surface_normals` と同じ。台帳の名前を
変えたのは、``surface_normals`` が 3-D の測光(ops3d)の op 名で、``terrain_surface_normals`` は
facade の正式名(別名の表 opnames)として既に使われているため(op 名は全体で 1 つ)。
空の入力(``grid`` が 0 要素)は (0, W, 3) の空の配列を返す(理由: 観測の無い地図は法線も無く、形だけを保つ)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`normalmap` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`walkterrain`)

[elevation_map](elevation_map.md) · [fill_gaps](fill_gaps.md) · [elevation_traversability](elevation_traversability.md) · [foothold_score](foothold_score.md) · [ground_surface](ground_surface.md) · [ground_plane](ground_plane.md) · [detect_obstacles](detect_obstacles.md) · [fuse_elevation](fuse_elevation.md)

---
*Provenance: terrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
