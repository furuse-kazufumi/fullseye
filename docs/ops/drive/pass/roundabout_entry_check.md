---
op: roundabout_entry_check
dim: drive
category: pass
in: table
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# roundabout_entry_check — DRIVE `pass` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.roundabout_entry_check(entry_theta: 'float', ring_radius: 'float', circulating: 'Sequence[dict]', *, t_clear: 'float', entry_speed: 'float', crawl: 'float' = 2.7777777777777777, sudden: 'float' = 2.0, side_friction: 'Optional[float]' = None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.roundabout_entry_check(entry_theta: 'float', ring_radius: 'float', circulating: 'Sequence[dict]', *, t_clear: 'float', entry_speed: 'float', crawl: 'float' = 2.7777777777777777, sudden: 'float' = 2.0, side_friction: 'Optional[float]' = None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("roundabout_entry_check")`)

## 使い方

環状交差点に入ってよいか(37 条の 2 第 1・2 項、35 条の 2)。場面 S102。

環道(中心 = 原点、半径 ``ring_radius``)を右回りに走る車 circulating[i] = {"theta", "speed"} が、入口の角 ``entry_theta``
(衝突の点)まで進む弧 = R·((θ − θ_e) mod 2π)、着く時刻 = 弧 / speed。入る車が衝突の点を抜けるのに ``t_clear`` 秒かかる
とき、環道の車が t_clear まで点に入らないために要る減速度(``drivecrossing.obstruction_decel``)が ``sudden``
(**仮定**)を超えれば進行妨害 → ``must_yield``(37 条の 2 第 1 項)。``entry_speed`` > ``crawl``(**仮定** 10 km/h)は
``not_crawling``(同 2 項・35 条の 2 の徐行)。``side_friction`` を渡すと環道の曲線の上限速度
(``drivelateral.curve_speed_limit``)も返す。返り値: ``ok``、``reasons``、``cars`` = [{"arc", "t_arrive", "decel",
"obstructs"}]、``ring_speed_limit``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_pass](../../../../examples/poc_driving_pass.py) — `py -3.11 examples/poc_driving_pass.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pass`)

[overtake_requirement](overtake_requirement.md) · [overtake_return_gap](overtake_return_gap.md) · [no_overtaking_zones](no_overtaking_zones.md) · [overtake_permitted](overtake_permitted.md) · [overtaken_conduct_check](overtaken_conduct_check.md) · [lane_change_follower_decel](lane_change_follower_decel.md) · [lane_change_permitted](lane_change_permitted.md) · [roundabout_signal_point](roundabout_signal_point.md)

---
*Provenance: drivepass.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
