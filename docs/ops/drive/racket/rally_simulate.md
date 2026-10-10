---
op: rally_simulate
dim: drive
category: racket
in: table × table × table
out: table
examples: [poc_ball_bounce, poc_table_tennis_rally_loop]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# rally_simulate — DRIVE `racket` op

- **データ種**: `table × table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.rally_simulate(bp: 'dict', rp: 'dict', tp: 'dict', *, perceive=None, strategies=None, retries: 'int' = 6, x_racket: 'float' = 1.55, hit_height=(0.05, 0.45), T_flight: 'float' = 0.42, target_x: 'float' = 0.75, max_hits: 'int' = 60, dt: 'float' = 0.0002, fps: 'float' = 100.0, seed: 'int' = 0, y_jitter: 'float' = 0.25, plan_spin: 'bool' = True, table_ip=None, replan_every: 'int' = 5) -> 'dict'` (実装を直接呼ぶなら `import racket; racket.rally_simulate(bp: 'dict', rp: 'dict', tp: 'dict', *, perceive=None, strategies=None, retries: 'int' = 6, x_racket: 'float' = 1.55, hit_height=(0.05, 0.45), T_flight: 'float' = 0.42, target_x: 'float' = 0.75, max_hits: 'int' = 60, dt: 'float' = 0.0002, fps: 'float' = 100.0, seed: 'int' = 0, y_jitter: 'float' = 0.25, plan_spin: 'bool' = True, table_ip=None, replan_every: 'int' = 5) -> 'dict'`、台帳から引くなら `opsdrive.get("rally_simulate")`)

## 使い方

2 本のラケット(x = −x_r と +x_r、板は相手を向く)で打ち合う。

各コマ(1/fps)で受け手側の知覚 ``perceive(t, p, v, ω)`` が球の状態を返し、そこから運動方程式 + 台の跳ねで自分の面
x = ±x_r への到達点・時刻を予測してラケットを動かす(上限つき)。球が面に届いたら、相手コートの (∓target_x, y*) に
T_flight で落ちる速度を狙って打つ(y* は乱数、``plan_spin`` なら打球後のスピンを込みで狙いを合わせる)。
``strategies`` = (side 0 の戦略, side 1 の戦略)(None なら両方 :func:`strategy_feeder`)。``retries`` > 0 なら打つ前に
:func:`shot_is_legal` で先読みし、外す狙いは巻き戻して別の狙い(戦略を引き直す)でやり直す。
返り値 ``{"hits", "end_reason", "shots": [...], "t", "p" (N,3), "racket_pos" (N,2,3), "hit_times", "rewinds"}``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_table_tennis_rally_loop](../../../../examples/poc_table_tennis_rally_loop.py) — `py -3.11 examples/poc_table_tennis_rally_loop.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`racket`)

[racket_params](racket_params.md) · [racket_impact](racket_impact.md) · [racket_hit_check](racket_hit_check.md) · [aim_velocity](aim_velocity.md) · [racket_plan](racket_plan.md) · [racket_move](racket_move.md) · [strategy_attacker](strategy_attacker.md) · [strategy_feeder](strategy_feeder.md)

---
*Provenance: racket.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
