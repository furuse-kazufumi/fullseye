---
op: elevation_step_edges
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

# elevation_step_edges — DRIVE `walkterrain` op

- **データ種**: `depth` → `mask`
- **呼び出し**: `import fullseye as fs; fs.ledger.elevation_step_edges(grid, min_rise: 'float' = 0.05, window: 'int' = 3)` (実装を直接呼ぶなら `import terrain; terrain.elevation_step_edges(grid, min_rise: 'float' = 0.05, window: 'int' = 3)`、台帳から引くなら `opsdrive.get("elevation_step_edges")`)
- **台帳経由の戻り値**: `fullseye.ledger.elevation_step_edges(...)` は**宣言 out 型 `mask` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.elevation_step_edges.raw(...)`、または `terrain.elevation_step_edges` を直接呼ぶ。
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Step edges (curbs / stair nosings) of an elevation map -> ``(edge_mask, signed_rise)`` (ledger door).

中身は :func:`step_edges` と同じで、``cell`` を持たない。``step_edges`` の ``cell`` は勾配の
**符号**を選ぶのにしか使われず(段差の高さ = 窓の max − min、向き = 勾配の大きいほうの成分の
符号。どちらも cell で割っても変わらない)効かないノブになるので、台帳の入口から外した
(素の関数の引数は公開の約束なので外さない)。台帳の宣言 out は mask(``edge_mask``)。
空の入力(``grid`` が 0 要素)は空の 2 枚の配列を返す(理由: 観測の無い地図には段差も無く、形だけを保つ)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`mask` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`walkterrain`)

[elevation_map](elevation_map.md) · [fill_gaps](fill_gaps.md) · [elevation_traversability](elevation_traversability.md) · [foothold_score](foothold_score.md) · [ground_surface](ground_surface.md) · [ground_plane](ground_plane.md) · [detect_obstacles](detect_obstacles.md) · [fuse_elevation](fuse_elevation.md)

---
*Provenance: terrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
