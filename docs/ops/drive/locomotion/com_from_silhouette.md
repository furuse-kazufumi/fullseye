---
op: com_from_silhouette
dim: drive
category: locomotion
in: mask
out: keypoints
gpu: なし
examples: [consumer_hillco, walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# com_from_silhouette — DRIVE `locomotion` op

- **データ種**: `mask` → `keypoints`
- **呼び出し**: `import fullseye as fs; fs.ledger.com_from_silhouette(mask)` (実装を直接呼ぶなら `import locomotion; locomotion.com_from_silhouette(mask)`、台帳から引くなら `opsdrive.get("com_from_silhouette")`)
- **台帳経由の戻り値**: `fullseye.ledger.com_from_silhouette(...)` は**宣言 out 型 `keypoints` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.com_from_silhouette.raw(...)`、または `locomotion.com_from_silhouette` を直接呼ぶ。
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Centre of mass (centroid) of a binary silhouette, as ``(row, col)`` in
image coordinates. A cheap proxy for the body COM projection when a full mass
model is unavailable (evis/hillco posture). Returns ``(nan, nan)`` for an
empty mask.

空の入力(``mask`` が 0 要素)は ``(nan, nan)`` を返す(理由: 画素の無いシルエットには重心が無く、0 で埋めると原点に人がいることになる)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [consumer_hillco](../../../../examples/consumer_hillco.py) — `py -3.11 examples/consumer_hillco.py`
- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`keypoints` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`locomotion`)

[contact_points](contact_points.md) · [support_polygon](support_polygon.md) · [com_support_margin](com_support_margin.md) · [gait_phase](gait_phase.md) · [support_line_margin](support_line_margin.md) · [lipm_capture_point](lipm_capture_point.md) · [capture_margin](capture_margin.md) · [gait_step_events](gait_step_events.md)

---
*Provenance: locomotion.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
