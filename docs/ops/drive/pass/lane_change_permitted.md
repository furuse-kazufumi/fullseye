---
op: lane_change_permitted
dim: drive
category: pass
in: table
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# lane_change_permitted — DRIVE `pass` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lane_change_permitted(*, follower: 'Optional[dict]' = None, boundary: 'str' = 'none', exception: 'Optional[str]' = None, signal_events: 'Optional[Sequence[dict]]' = None, sudden: 'float' = 2.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.lane_change_permitted(*, follower: 'Optional[dict]' = None, boundary: 'str' = 'none', exception: 'Optional[str]' = None, signal_events: 'Optional[Sequence[dict]]' = None, sudden: 'float' = 2.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("lane_change_permitted")`)

## 使い方

進路変更をしてよいか(条文の判定)。場面 S067・S072・S073。

* ``follower_sudden_decel``(26 条の 2 第 2 項): ``follower`` = {"gap", "v_follow", "v_ego", "reaction"[, "accel_ego",
  "min_gap"]} に ``lane_change_follower_decel`` で要る減速度が ``sudden`` を超える。
* ``no_lane_change_marking``(26 条の 2 第 3 項): ``boundary`` = "yellow"(進路変更の禁止を表示する道路標示)を越える。
  ``exception`` = "article40"(緊急自動車に譲る)/ "obstruction"(道路の損壊・工事その他の障害)なら除外(同項 1・2 号)。
* ``signal_*``(53 条 1 項・教則 5-5-1「約 3 秒前」): ``signal_events`` を ``drivedecide.check_sequence_score``
  (maneuver="lane_change")で採点した違反をそのまま足す(施行令 21 条は未確認)。
26 条の 2 第 1 項「みだりに」は数値にできないので判定しない。返り値: ``ok``、``reasons``、``decel``、``sequence``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_pass](../../../../examples/poc_driving_pass.py) — `py -3.11 examples/poc_driving_pass.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pass`)

[overtake_requirement](overtake_requirement.md) · [overtake_return_gap](overtake_return_gap.md) · [no_overtaking_zones](no_overtaking_zones.md) · [overtake_permitted](overtake_permitted.md) · [overtaken_conduct_check](overtaken_conduct_check.md) · [lane_change_follower_decel](lane_change_follower_decel.md) · [roundabout_entry_check](roundabout_entry_check.md) · [roundabout_signal_point](roundabout_signal_point.md)

---
*Provenance: drivepass.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
