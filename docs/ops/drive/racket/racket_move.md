---
op: racket_move
dim: drive
category: racket
in: table
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# racket_move — DRIVE `racket` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.racket_move(pos, vel, target, dt: 'float', rp: 'dict') -> 'tuple'` (実装を直接呼ぶなら `import racket; racket.racket_move(pos, vel, target, dt: 'float', rp: 'dict') -> 'tuple'`、台帳から引くなら `opsdrive.get("racket_move")`)

## 使い方

ラケットを target へ動かす(速さ・加速度の上限つきの bang-bang: 止まれる距離を見て減速)。返り値 (pos, vel)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`racket`)

[racket_params](racket_params.md) · [racket_impact](racket_impact.md) · [racket_hit_check](racket_hit_check.md) · [aim_velocity](aim_velocity.md) · [racket_plan](racket_plan.md) · [strategy_attacker](strategy_attacker.md) · [strategy_feeder](strategy_feeder.md) · [shot_is_legal](shot_is_legal.md)

---
*Provenance: racket.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
