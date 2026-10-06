---
op: shot_is_legal
dim: drive
category: racket
in: table × table × table
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# shot_is_legal — DRIVE `racket` op

- **データ種**: `table × table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.shot_is_legal(p, v, w, bp, ip, tp, x_racket: 'float', side: 'int', hit_height=(0.05, 0.45)) -> 'dict'` (実装を直接呼ぶなら `import racket; racket.shot_is_legal(p, v, w, bp, ip, tp, x_racket: 'float', side: 'int', hit_height=(0.05, 0.45)) -> 'dict'`、台帳から引くなら `opsdrive.get("shot_is_legal")`)

## 使い方

打球 (p, v, ω) を真の物理で先読みして、ネットを越え・相手コートに 1 度だけ落ち・相手の面 x = ∓x_r に打てる高さで
届くかを判定する。``{"legal", "reason", "p_arrive", "t_arrive"}``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`racket`)

[racket_params](racket_params.md) · [racket_impact](racket_impact.md) · [racket_hit_check](racket_hit_check.md) · [aim_velocity](aim_velocity.md) · [racket_plan](racket_plan.md) · [racket_move](racket_move.md) · [strategy_attacker](strategy_attacker.md) · [strategy_feeder](strategy_feeder.md)

---
*Provenance: racket.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
