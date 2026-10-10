---
op: racket_plan
dim: drive
category: racket
in: table × table
out: table
examples: [poc_table_tennis_rally_loop]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# racket_plan — DRIVE `racket` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.racket_plan(v_in, omega_in, v_out, bp: 'dict', rp: 'dict', refine: 'int' = 8) -> 'dict'` (実装を直接呼ぶなら `import racket; racket.racket_plan(v_in, omega_in, v_out, bp: 'dict', rp: 'dict', refine: 'int' = 8) -> 'dict'`、台帳から引くなら `opsdrive.get("racket_plan")`)

## 使い方

望む v_out を出すラケットの法線 n と速度 v_r(法線方向)。摩擦 0 の閉形式 n ∝ v_out − v_in、
v_r·n = |Δv|/(1+e) + v_in·n を初期値に、実際の衝突(摩擦・スピン込み)で ``refine`` 回反復。
返り値 ``{"normal", "v_racket", "v_out_actual", "omega_out", "residual"}``。Δv ≈ 0 なら ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_table_tennis_rally_loop](../../../../examples/poc_table_tennis_rally_loop.py) — `py -3.11 examples/poc_table_tennis_rally_loop.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`racket`)

[racket_params](racket_params.md) · [racket_impact](racket_impact.md) · [racket_hit_check](racket_hit_check.md) · [aim_velocity](aim_velocity.md) · [racket_move](racket_move.md) · [strategy_attacker](strategy_attacker.md) · [strategy_feeder](strategy_feeder.md) · [shot_is_legal](shot_is_legal.md)

---
*Provenance: racket.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
