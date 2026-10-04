---
op: events_to_frames
dim: drive
category: motion_io
in: table
out: voxel
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# events_to_frames — DRIVE `motion_io` op

- **データ種**: `table` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.events_to_frames(events: 'dict', n_frames: 'int' = 32, shape=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import motionio; motionio.events_to_frames(events: 'dict', n_frames: 'int' = 32, shape=None) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("events_to_frames")`)

## 使い方

イベントを時間で n_frames に等分し、画素ごとに極性を足したコマ (T, H, W) にする(ON = +1、OFF = −1)。

全イベントの極性の和はコマの総和と一致する(落とすイベントは無い)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`voxel` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`motion_io`)

[read_bvh](read_bvh.md) · [read_events](read_events.md)

---
*Provenance: motionio.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
