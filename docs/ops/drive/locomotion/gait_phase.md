---
op: gait_phase
dim: drive
category: locomotion
in: matrix
out: table
gpu: なし
examples: [consumer_hillco, consumer_onocollo, walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# gait_phase — DRIVE `locomotion` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gait_phase(foot_heights, stance_frac: 'float' = 0.25, ground=None, contact_tol=None)` (実装を直接呼ぶなら `import locomotion; locomotion.gait_phase(foot_heights, stance_frac: 'float' = 0.25, ground=None, contact_tol=None)`、台帳から引くなら `opsdrive.get("gait_phase")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Classify each foot as stance (planted) or swing per frame from its height.

``foot_heights`` is ``(T, F)`` — the height of each of ``F`` feet over ``T``
frames. Returns ``{stance (T,F bool), duty_factor (F,), n_contacts (T,),
double_support}`` (duty factor, Alexander 1984; how many feet are down each
frame; fraction of frames with >=2 feet down).

★Stance is defined against a ground reference:

* ``ground`` given (recommended for anti-cheat) — a foot is stance only when it
  is within ``contact_tol`` of the absolute floor level ``ground``. This is the
  honest test: an airborne / hopping / frozen-in-air foot is correctly NOT
  stance.  ``contact_tol`` defaults to ``stance_frac`` × the foot's own range.
* ``ground=None`` (default, backward-compatible) — stance is inferred from each
  foot's OWN height range (within ``stance_frac`` of its per-foot minimum).
  ★This heuristic CANNOT tell a foot planted on the floor from a foot at the
  bottom of an airborne trajectory, so it must NOT be used as a stability /
  cheat gate — pass ``ground`` for that.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [consumer_hillco](../../../../examples/consumer_hillco.py) — `py -3.11 examples/consumer_hillco.py`
- [consumer_onocollo](../../../../examples/consumer_onocollo.py) — `py -3.11 examples/consumer_onocollo.py`
- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`locomotion`)

[contact_points](contact_points.md) · [com_from_silhouette](com_from_silhouette.md) · [support_polygon](support_polygon.md) · [com_support_margin](com_support_margin.md) · [support_line_margin](support_line_margin.md) · [lipm_capture_point](lipm_capture_point.md) · [capture_margin](capture_margin.md) · [gait_step_events](gait_step_events.md)

---
*Provenance: locomotion.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
