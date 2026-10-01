---
op: roundabout_signal_check
dim: drive
category: pass
in: signal × signal
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# roundabout_signal_check — DRIVE `pass` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.roundabout_signal_check(progress, left_on, *, arm_angles: 'Sequence[float]', entry: 'int', exit: 'int', right_on=None, tol: 'float' = 0.05) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.roundabout_signal_check(progress, left_on, *, arm_angles: 'Sequence[float]', entry: 'int', exit: 'int', right_on=None, tol: 'float' = 0.05) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("roundabout_signal_check")`)

## 使い方

環状交差点の中の合図を採点する(53 条 2・4 項、教則 5-5-1(2))。場面 S069。

``progress`` = 入口から右回りに進んだ角 [rad]、単調非減少、サンプルごと、``left_on`` / ``right_on`` = 合図の状態(bool)。
* ``left_late``: 合図の角 + ``tol`` から出口の角までの間に左の合図が消えているサンプルがある。
* ``left_early``: 合図の角 − ``tol`` より手前で左の合図が点いている(手前の出口で出るように見える。53 条 4 項の
  「行為をしないのに合図」の **解釈**)。入った直後の出口(合図の角 = 0)では問わない。
* ``right_signal``: 環道の中で右の合図(53 条 2 項は出るときだけを求める。4 項の **解釈**)。

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
