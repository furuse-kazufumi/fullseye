---
op: racket_hit_check
dim: drive
category: racket
in: table
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# racket_hit_check — DRIVE `racket` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.racket_hit_check(p_ball, center, normal, rp: 'dict', radius: 'float', up=(0.0, 0.0, 1.0)) -> 'dict'` (実装を直接呼ぶなら `import racket; racket.racket_hit_check(p_ball, center, normal, rp: 'dict', radius: 'float', up=(0.0, 0.0, 1.0)) -> 'dict'`、台帳から引くなら `opsdrive.get("racket_hit_check")`)

## 使い方

球の中心が板の面から ``radius`` 以内で、板の枠(幅 × 高さ + 半径)の中にあるか。``{"hit", "dist", "u", "v"}``
(u = 幅方向、v = 高さ方向の板の中心からのずれ)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`racket`)

[racket_params](racket_params.md) · [racket_impact](racket_impact.md) · [aim_velocity](aim_velocity.md) · [racket_plan](racket_plan.md) · [racket_move](racket_move.md) · [strategy_attacker](strategy_attacker.md) · [strategy_feeder](strategy_feeder.md) · [shot_is_legal](shot_is_legal.md)

---
*Provenance: racket.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
