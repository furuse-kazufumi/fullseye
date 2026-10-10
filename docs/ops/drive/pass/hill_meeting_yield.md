---
op: hill_meeting_yield
dim: drive
category: pass
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# hill_meeting_yield — DRIVE `pass` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.hill_meeting_yield(ego_direction: 'str', *, ego_refuge_distance: 'Optional[float]' = None, other_refuge_distance: 'Optional[float]' = None, near: 'float' = 30.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.hill_meeting_yield(ego_direction: 'str', *, ego_refuge_distance: 'Optional[float]' = None, other_refuge_distance: 'Optional[float]' = None, near: 'float' = 30.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("hill_meeting_yield")`)

## 使い方

坂道の狭い所での行き違い: どちらが譲るか(教則 6-2-1(6)。**法の明文なし**)。場面 S128。

原則は下りの車が上りの車に譲る(上り坂の発進が難しいため)。ただし上りの車の近く(``near``、**仮定** 30 m 以内)に
待避所があれば上りの車がそこに入って待つ。``ego_direction`` = "up" / "down"、``*_refuge_distance`` = その車から前方の
待避所までの距離(無ければ None)。返り値: ``yielder`` ∈ {"ego", "other"}、``where`` ∈ {"refuge", "stop"}、``basis``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pass`)

[overtake_requirement](overtake_requirement.md) · [overtake_return_gap](overtake_return_gap.md) · [no_overtaking_zones](no_overtaking_zones.md) · [overtake_permitted](overtake_permitted.md) · [overtaken_conduct_check](overtaken_conduct_check.md) · [lane_change_follower_decel](lane_change_follower_decel.md) · [lane_change_permitted](lane_change_permitted.md) · [roundabout_entry_check](roundabout_entry_check.md)

---
*Provenance: drivepass.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
