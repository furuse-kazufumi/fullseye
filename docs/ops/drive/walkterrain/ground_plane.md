---
op: ground_plane
dim: drive
category: walkterrain
in: depth
out: depth
gpu: なし
examples: [walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# ground_plane — DRIVE `walkterrain` op

- **データ種**: `depth` → `depth`
- **呼び出し**: `import fullseye as fs; fs.ledger.ground_plane(grid, trim: 'float' = 0.3, iters: 'int' = 3)` (実装を直接呼ぶなら `import terrain; terrain.ground_plane(grid, trim: 'float' = 0.3, iters: 'int' = 3)`、台帳から引くなら `opsdrive.get("ground_plane")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Robust least-squares ground plane ``z = a·x + b·y + c`` per cell.

Fits a plane to the (filled) elevation, then re-fits a few times after
trimming the highest-residual cells — the ones that rise above the ground and
are therefore obstacles, not ground. Recovers a flat *or* tilted (ramp) ground
exactly, with no boundary artefact, which is what obstacle detection wants
when the walkable surface is planar. *trim* is the top residual fraction
discarded each iteration.

空の入力(``grid`` が 0 要素)は形を保った空の配列を返す(理由: 当てはめる高さが無く、形だけを保つ。観測が 3 セル未満の地図は nan の平面)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`walkterrain`)

[elevation_map](elevation_map.md) · [fill_gaps](fill_gaps.md) · [elevation_traversability](elevation_traversability.md) · [foothold_score](foothold_score.md) · [ground_surface](ground_surface.md) · [detect_obstacles](detect_obstacles.md) · [fuse_elevation](fuse_elevation.md) · [roughness_map](roughness_map.md)

---
*Provenance: terrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
