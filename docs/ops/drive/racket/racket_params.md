---
op: racket_params
dim: drive
category: racket
in: 
out: table
examples: [poc_ball_bounce, poc_table_tennis_rally_loop]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# racket_params — DRIVE `racket` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.racket_params(width: 'float' = 0.15, height: 'float' = 0.16, e: 'float' = 0.8, mu: 'float' = 0.6, v_max: 'float' = 6.0, a_max: 'float' = 60.0) -> 'dict'` (実装を直接呼ぶなら `import racket; racket.racket_params(width: 'float' = 0.15, height: 'float' = 0.16, e: 'float' = 0.8, mu: 'float' = 0.6, v_max: 'float' = 6.0, a_max: 'float' = 60.0) -> 'dict'`、台帳から引くなら `opsdrive.get("racket_params")`)

## 使い方

ラケットの表: 板の幅・高さ [m]、ラバーの反発係数 e と摩擦係数 μ、動きの上限(速さ v_max [m/s]、加速度 a_max [m/s²])。

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

[racket_impact](racket_impact.md) · [racket_hit_check](racket_hit_check.md) · [aim_velocity](aim_velocity.md) · [racket_plan](racket_plan.md) · [racket_move](racket_move.md) · [strategy_attacker](strategy_attacker.md) · [strategy_feeder](strategy_feeder.md) · [shot_is_legal](shot_is_legal.md)

---
*Provenance: racket.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
