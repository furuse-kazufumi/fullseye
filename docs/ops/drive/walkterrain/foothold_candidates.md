---
op: foothold_candidates
dim: drive
category: walkterrain
in: depth
out: table
gpu: なし
examples: [consumer_hillco, physical_ai_perception, walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# foothold_candidates — DRIVE `walkterrain` op

- **データ種**: `depth` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.foothold_candidates(grid, cell: 'float' = 0.05, window: 'int' = 3, min_score: 'float' = 0.6, min_dist: 'float' = 0.15, max_n: 'int' = 50, extent=None)` (実装を直接呼ぶなら `import terrain; terrain.foothold_candidates(grid, cell: 'float' = 0.05, window: 'int' = 3, min_score: 'float' = 0.6, min_dist: 'float' = 0.15, max_n: 'int' = 50, extent=None)`、台帳から引くなら `opsdrive.get("foothold_candidates")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Pick discrete safe stepping targets from the terrain.

Scores every cell with :func:`foothold_score`, keeps local maxima above
*min_score*, and greedily suppresses candidates within *min_dist* (world units)
of a better one — turning the continuous flatness field into a short list of
"here are places you may put a foot". Returns a list of dicts sorted best-first,
each with ``cell`` (row, col), ``score``, and ``xy`` (world) when *extent* is
given. The actionable output a foot-placement planner consumes.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [consumer_hillco](../../../../examples/consumer_hillco.py) — `py -3.11 examples/consumer_hillco.py`
- [physical_ai_perception](../../../../examples/physical_ai_perception.py) — `py -3.11 examples/physical_ai_perception.py`
- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`walkterrain`)

[elevation_map](elevation_map.md) · [fill_gaps](fill_gaps.md) · [elevation_traversability](elevation_traversability.md) · [foothold_score](foothold_score.md) · [ground_surface](ground_surface.md) · [ground_plane](ground_plane.md) · [detect_obstacles](detect_obstacles.md) · [fuse_elevation](fuse_elevation.md)

---
*Provenance: terrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
