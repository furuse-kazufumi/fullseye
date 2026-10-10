---
op: roundabout_signal_point
dim: drive
category: pass
in: any
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# roundabout_signal_point — DRIVE `pass` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.roundabout_signal_point(arm_angles: 'Sequence[float]', entry: 'int', exit: 'int') -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.roundabout_signal_point(arm_angles: 'Sequence[float]', entry: 'int', exit: 'int') -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("roundabout_signal_point")`)

## 使い方

環状交差点を出るときの左の合図を始める位置(右回りに進んだ角)。場面 S069。

教則 5-5-1(2)・5-7-2(4): 出ようとする地点の直前の出口の側方を通過したとき、入った直後の出口を出るなら入ったとき
(53 条 2 項。時期の政令 = 施行令 21 条は未確認)。``arm_angles`` = 各枝の角、``entry`` / ``exit`` = 番号。
右回りに入口から測った各枝の角 d_i = (θ_entry − θ_i) mod 2π(出口 = 入口なら 2π、転回)。合図の角 = 目的の出口の角より
小さい d_i の最大値(無ければ 0 = 入ったとき)。返り値: ``signal_angle``、``exit_angle``、``exits_before``(通り過ぎる出口の数)、
``signal_theta``(環道の上の角)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_pass](../../../../examples/poc_driving_pass.py) — `py -3.11 examples/poc_driving_pass.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pass`)

[overtake_requirement](overtake_requirement.md) · [overtake_return_gap](overtake_return_gap.md) · [no_overtaking_zones](no_overtaking_zones.md) · [overtake_permitted](overtake_permitted.md) · [overtaken_conduct_check](overtaken_conduct_check.md) · [lane_change_follower_decel](lane_change_follower_decel.md) · [lane_change_permitted](lane_change_permitted.md) · [roundabout_entry_check](roundabout_entry_check.md)

---
*Provenance: drivepass.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
