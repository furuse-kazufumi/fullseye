---
op: no_overtaking_zones
dim: drive
category: pass
in: table
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# no_overtaking_zones — DRIVE `pass` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.no_overtaking_zones(features: 'Iterable[dict]', *, priority_road: 'bool' = False, vicinity: 'Optional[dict]' = None, steep_grade: 'float' = 0.1, zone: 'float' = 30.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.no_overtaking_zones(features: 'Iterable[dict]', *, priority_road: 'bool' = False, vicinity: 'Optional[dict]' = None, steep_grade: 'float' = 0.1, zone: 'float' = 30.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("no_overtaking_zones")`)

## 使い方

道に沿った施設から、30 条の追越し(のための進路変更・側方通過)の禁止区間を作る。場面 S081・S009・S130。

features[i] = {"kind", "start", "end"}(点の施設は "at")。kind:
``sign``(標識等で禁止された区間をそのまま)、``curve``(曲がり角、1 号「付近」= 前後 ``vicinity``、**仮定** 30 m)、
``crest``(上り坂の頂上、同)、``downhill``(下り坂、"grade" が ``steep_grade``(**仮定** 10 %)以上か grade 無しなら
1 号の「勾配の急な」)、``tunnel``(2 号。"has_lanes" が真なら除外)、``intersection``(3 号。``priority_road`` を
通行しているなら除外)、``railway_crossing`` / ``crosswalk`` / ``bicycle_crossing``(3 号)。3 号は [start − 30, end]。
返り値: ``zones`` = [(a, b, kind, 号)]、``merged`` = 重なりを併せた (k, 2)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_pass](../../../../examples/poc_driving_pass.py) — `py -3.11 examples/poc_driving_pass.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pass`)

[overtake_requirement](overtake_requirement.md) · [overtake_return_gap](overtake_return_gap.md) · [overtake_permitted](overtake_permitted.md) · [overtaken_conduct_check](overtaken_conduct_check.md) · [lane_change_follower_decel](lane_change_follower_decel.md) · [lane_change_permitted](lane_change_permitted.md) · [roundabout_entry_check](roundabout_entry_check.md) · [roundabout_signal_point](roundabout_signal_point.md)

---
*Provenance: drivepass.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
