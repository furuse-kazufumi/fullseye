---
op: support_polygon
dim: drive
category: locomotion
in: points
out: table
gpu: なし
examples: [consumer_hillco, consumer_onocollo, physical_ai_perception, walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# support_polygon — DRIVE `locomotion` op

- **データ種**: `points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.support_polygon(contacts, ground=None, contact_tol: 'float' = 0.02) -> 'dict'` (実装を直接呼ぶなら `import locomotion; locomotion.support_polygon(contacts, ground=None, contact_tol: 'float' = 0.02) -> 'dict'`、台帳から引くなら `opsdrive.get("support_polygon")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Convex support polygon of the ground-contact points (ground x, y plane).

Returns ``{vertices (M,2 CCW), area, perimeter, centroid}``. With <3 distinct
points it degenerates gracefully (a point or a segment, ``area = 0``). This is
the base of support a static-stability check is measured against.
空の入力(``contacts`` が 0 要素)は頂点 0 個・面積 0 の多角形を返す(理由: 足が 1 つも接地していない状態そのもの。重心は nan)。

★Precondition — only feet ACTUALLY TOUCHING the floor may take part: every
contact is projected to (x, y), so a lifted foot out at some far x/y inflates
the polygon and can make a tipping robot read as statically stable.

* ``ground`` given (recommended for anti-cheat) — a floor level ``z`` or a
  plane ``[a, b, c, d]``; contacts further than ``contact_tol`` from it are
  filtered out here, so an airborne foot supports nothing.
* ``ground=None`` (default, backward-compatible) — no z check at all; the
  caller MUST pre-filter with :func:`contact_points`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [consumer_hillco](../../../../examples/consumer_hillco.py) — `py -3.11 examples/consumer_hillco.py`
- [consumer_onocollo](../../../../examples/consumer_onocollo.py) — `py -3.11 examples/consumer_onocollo.py`
- [physical_ai_perception](../../../../examples/physical_ai_perception.py) — `py -3.11 examples/physical_ai_perception.py`
- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`locomotion`)

[contact_points](contact_points.md) · [com_from_silhouette](com_from_silhouette.md) · [com_support_margin](com_support_margin.md) · [gait_phase](gait_phase.md) · [support_line_margin](support_line_margin.md) · [lipm_capture_point](lipm_capture_point.md) · [capture_margin](capture_margin.md) · [gait_step_events](gait_step_events.md)

---
*Provenance: locomotion.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
