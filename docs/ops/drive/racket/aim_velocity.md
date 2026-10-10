---
op: aim_velocity
dim: drive
category: racket
in: table
out: table
examples: [poc_table_tennis_rally_loop]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# aim_velocity — DRIVE `racket` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.aim_velocity(p, target, T: 'float', bp: 'dict', omega=(0.0, 0.0, 0.0), refine: 'int' = 6, dt: 'float' = 0.001) -> 'dict'` (実装を直接呼ぶなら `import racket; racket.aim_velocity(p, target, T: 'float', bp: 'dict', omega=(0.0, 0.0, 0.0), refine: 'int' = 6, dt: 'float' = 0.001) -> 'dict'`、台帳から引くなら `opsdrive.get("aim_velocity")`)

## 使い方

点 p から時間 T で target に届く初速。真空の閉形式 v = (Δxy/T, (Δz + ½gT²)/T) を初期値に、抗力 + マグヌス(ω)の
運動方程式で ``refine`` 回 Gauss–Newton(有限差分)。``{"v", "residual"}``(residual = 到達点のずれ [m])。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_table_tennis_rally_loop](../../../../examples/poc_table_tennis_rally_loop.py) — `py -3.11 examples/poc_table_tennis_rally_loop.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`racket`)

[racket_params](racket_params.md) · [racket_impact](racket_impact.md) · [racket_hit_check](racket_hit_check.md) · [racket_plan](racket_plan.md) · [racket_move](racket_move.md) · [strategy_attacker](strategy_attacker.md) · [strategy_feeder](strategy_feeder.md) · [shot_is_legal](shot_is_legal.md)

---
*Provenance: racket.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
