---
op: support_line_margin
dim: drive
category: locomotion
in: vector × points
out: measurement
gpu: なし
examples: [walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# support_line_margin — DRIVE `locomotion` op

- **データ種**: `vector × points` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.support_line_margin(com, contacts, ground=None, contact_tol: 'float' = 0.02) -> 'float'` (実装を直接呼ぶなら `import locomotion; locomotion.support_line_margin(com, contacts, ground=None, contact_tol: 'float' = 0.02) -> 'float'`、台帳から引くなら `opsdrive.get("support_line_margin")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Support margin that is defined for EVERY support set, including two-foot (segment) support.

支持の形がどれでも値を持つ静的安定余裕。:func:`com_support_margin` は支持多角形に面積が
無いとき(2 足支持 = 線分、1 足 = 点)``-inf`` を返す ―― 2 足で立つ人型の大半の時間が
「測れない」になる穴がある。既存の値を変えると破壊的変更なので、この op を別に足した。

* 面積のある多角形: :func:`com_support_margin` と同じ符号つき距離(+ = 内側)。
* 線分(2 足、または一直線に並んだ足): COM の地面への射影から閉じた線分までの距離に
  **負号を付けた値**(``-dist``)。線分の上でちょうど 0、離れるほど負。線分には内側が
  無いので正にはならない(刃の上で釣り合うのが最良)。点と線分の距離は閉形式
  ``t = clip(((p-a)·(b-a))/|b-a|², 0, 1)``。
* 点(1 足): ``-|p - foot|``。

``com`` は (x, y) か (x, y, z)(z は使わない)。``contacts`` は (N, 2) / (N, 3)。
``ground`` / ``contact_tol`` は :func:`support_polygon` に渡す(宙に浮いた足を外す)。
単位は入力の世界単位。足が 1 つも無い(フィルタ後も含む)ときは ``ValueError``
(支えが無いことを ``-inf`` で黙って返さない)。

English: polygon with area -> the same signed distance as :func:`com_support_margin`;
segment -> ``-distance`` to the closed segment (0 on it, never positive: a line has no
interior); single foot -> ``-distance`` to that foot; no foot -> ``ValueError``.
The first source of the segment rule is ``fullseye_shows/common/measure.py``
(``support_line_margin``, same author).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`locomotion`)

[contact_points](contact_points.md) · [com_from_silhouette](com_from_silhouette.md) · [support_polygon](support_polygon.md) · [com_support_margin](com_support_margin.md) · [gait_phase](gait_phase.md) · [lipm_capture_point](lipm_capture_point.md) · [capture_margin](capture_margin.md) · [gait_step_events](gait_step_events.md)

---
*Provenance: locomotion.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
