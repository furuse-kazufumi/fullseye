---
op: contact_points
dim: drive
category: locomotion
in: points × any
out: points
gpu: なし
examples: [consumer_onocollo, walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# contact_points — DRIVE `locomotion` op

- **データ種**: `points × any` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.contact_points(points, plane, tol: 'float' = 0.02)` (実装を直接呼ぶなら `import locomotion; locomotion.contact_points(points, plane, tol: 'float' = 0.02)`、台帳から引くなら `opsdrive.get("contact_points")`)
- **台帳経由の戻り値**: `fullseye.ledger.contact_points(...)` は**宣言 out 型 `points` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.contact_points.raw(...)`、または `locomotion.contact_points` を直接呼ぶ。
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Points lying within *tol* of a ground plane ``[a,b,c,d]`` = ground contacts.

Given a cloud and the fitted ground plane (see :func:`pcseg.fit_plane_ransac`),
returns ``(contacts (M,3), mask)`` — the feet/wheels/base actually touching the
floor, the input to :func:`support_polygon`.

空の入力(``points`` が 0 要素)は(0, 3) の点と空の maskを返す(理由: 点が無ければ接地点も無い。拒否すると逐次の処理が止まる)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [consumer_onocollo](../../../../examples/consumer_onocollo.py) — `py -3.11 examples/consumer_onocollo.py`
- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`points` を入力に取れる)

[course_contains](../course/course_contains.md) · [ray_plane_range](../lidar/ray_plane_range.md) · [ray_box_ranges](../lidar/ray_box_ranges.md) · [course_distance](../terrain/course_distance.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`locomotion`)

[com_from_silhouette](com_from_silhouette.md) · [support_polygon](support_polygon.md) · [com_support_margin](com_support_margin.md) · [gait_phase](gait_phase.md) · [support_line_margin](support_line_margin.md) · [lipm_capture_point](lipm_capture_point.md) · [capture_margin](capture_margin.md) · [gait_step_events](gait_step_events.md)

---
*Provenance: locomotion.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
