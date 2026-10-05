---
op: strategy_feeder
dim: drive
category: racket
in: table
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# strategy_feeder — DRIVE `racket` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.strategy_feeder(side: 'int', ctx: 'dict', rng, step: 'float' = 0.06) -> 'dict'` (実装を直接呼ぶなら `import racket; racket.strategy_feeder(side: 'int', ctx: 'dict', rng, step: 'float' = 0.06) -> 'dict'`、台帳から引くなら `opsdrive.get("strategy_feeder")`)

## 使い方

前回に近いがわずかにずらした位置へ返す(相手が取りやすい球): 前回の自分の狙いから ±step の一様乱数で動かし、
コートの内側(端から 12 cm)に収める。滞空時間はゆっくり 0.42 s。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`racket`)

[racket_params](racket_params.md) · [racket_impact](racket_impact.md) · [racket_hit_check](racket_hit_check.md) · [aim_velocity](aim_velocity.md) · [racket_plan](racket_plan.md) · [racket_move](racket_move.md) · [strategy_attacker](strategy_attacker.md) · [shot_is_legal](shot_is_legal.md)

---
*Provenance: racket.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
