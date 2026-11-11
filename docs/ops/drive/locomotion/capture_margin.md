---
op: capture_margin
dim: drive
category: locomotion
in: vector × vector × scalar × points
out: measurement
gpu: なし
examples: [walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# capture_margin — DRIVE `locomotion` op

- **データ種**: `vector × vector × scalar × points` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.capture_margin(com, com_vel, com_height, contacts, gravity: 'float' = 9.81, ground=None, contact_tol: 'float' = 0.02) -> 'float'` (実装を直接呼ぶなら `import locomotion; locomotion.capture_margin(com, com_vel, com_height, contacts, gravity: 'float' = 9.81, ground=None, contact_tol: 'float' = 0.02) -> 'float'`、台帳から引くなら `opsdrive.get("capture_margin")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Signed distance of the LIPM capture point to the support set (0-step capturability).

捕捉点 ξ(:func:`lipm_capture_point`)の、支持の形(:func:`support_line_margin` と同じ規則)
までの符号つき余裕。正 = ξ が支持多角形の内側で、**踏み出さずに止まれる**(足圧中心を ξ に
置ける。Koolen ほか 2012 の 0 歩捕捉可能)。負 = どこに足圧中心を置いても重心は止まらない
ので、踏み出すか倒れる。静的な :func:`com_support_margin` は速度を見ないので、前へ
走っている重心を「安定」と読む ―― この op はそれを負にする。

``com`` / ``com_vel`` は 1 時刻の (3,) か (2,)。``com_height`` [m] は正の有限値。
足が 1 つも無いときは ``ValueError``。空の入力(``com`` が 0 要素)も ValueError で拒否する。

English: positive = the capture point lies inside the support polygon, so the robot can
stop without stepping (0-step capturable); negative = it must step. Segment / single-foot
support follows :func:`support_line_margin` (never positive).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`locomotion`)

[contact_points](contact_points.md) · [com_from_silhouette](com_from_silhouette.md) · [support_polygon](support_polygon.md) · [com_support_margin](com_support_margin.md) · [gait_phase](gait_phase.md) · [support_line_margin](support_line_margin.md) · [lipm_capture_point](lipm_capture_point.md) · [gait_step_events](gait_step_events.md)

---
*Provenance: locomotion.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
