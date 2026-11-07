---
op: com_support_margin
dim: drive
category: locomotion
in: vector × points
out: measurement
gpu: なし
examples: [consumer_hillco, consumer_onocollo, physical_ai_perception, walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# com_support_margin — DRIVE `locomotion` op

- **データ種**: `vector × points` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.com_support_margin(com_xy, contacts, ground=None, contact_tol: 'float' = 0.02) -> 'float'` (実装を直接呼ぶなら `import locomotion; locomotion.com_support_margin(com_xy, contacts, ground=None, contact_tol: 'float' = 0.02) -> 'float'`、台帳から引くなら `opsdrive.get("com_support_margin")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Static stability margin: signed distance from the COM ground-projection to
the support-polygon boundary (McGhee & Frank 1968).

``com_xy`` is the COM projected onto the ground (x, y). Positive = the COM is
**inside** the support polygon by that margin (statically stable, larger =
safer); negative = outside (tipping). Returns the margin in world units
(``-inf`` if the polygon is degenerate / has no area).

★``ground`` / ``contact_tol`` are forwarded to :func:`support_polygon` — pass
them (floor level ``z`` or plane ``[a, b, c, d]``) so airborne feet are
excluded. Without them the contacts are used as given and a lifted foot can
turn a tipping robot into a "stable" one; pre-filter with
:func:`contact_points` in that case.

★2 足支持(線分)と 1 足(点)では面積が無いので ``-inf`` を返す(この値は変えない ——
変えると破壊的変更)。線分・点までの余裕が要るときは :func:`support_line_margin`。
Two-foot (segment) and one-foot support return ``-inf`` by contract; use
:func:`support_line_margin` for a finite margin there.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [consumer_hillco](../../../../examples/consumer_hillco.py) — `py -3.11 examples/consumer_hillco.py`
- [consumer_onocollo](../../../../examples/consumer_onocollo.py) — `py -3.11 examples/consumer_onocollo.py`
- [physical_ai_perception](../../../../examples/physical_ai_perception.py) — `py -3.11 examples/physical_ai_perception.py`
- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`locomotion`)

[contact_points](contact_points.md) · [com_from_silhouette](com_from_silhouette.md) · [support_polygon](support_polygon.md) · [gait_phase](gait_phase.md) · [support_line_margin](support_line_margin.md) · [lipm_capture_point](lipm_capture_point.md) · [capture_margin](capture_margin.md) · [gait_step_events](gait_step_events.md)

---
*Provenance: locomotion.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
