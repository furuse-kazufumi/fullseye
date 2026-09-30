---
op: mor_from_beta
dim: drive
category: env
in: scalar
out: scalar
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# mor_from_beta — DRIVE `env` op

- **データ種**: `scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.mor_from_beta(beta: 'float', contrast: 'float' = 0.05) -> 'float'` (実装を直接呼ぶなら `import driveenv; driveenv.mor_from_beta(beta: 'float', contrast: 'float' = 0.05) -> 'float'`、台帳から引くなら `opsdrive.get("mor_from_beta")`)

## 使い方

減衰係数 β [1/m] → 視程 = −ln(contrast)/β。既定 0.05 = WMO の気象光学距離(MOR ≈ 2.996/β)、0.02 = Koschmieder(3.912/β)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`scalar` を入力に取れる)

[road_eval](../long/road_eval.md) · [long_simulate](../long/long_simulate.md) · [stopping_distance_grade](../long/stopping_distance_grade.md) · [stop_line_plan](../long/stop_line_plan.md) · [hill_hold_brake_min](../long/hill_hold_brake_min.md) · [hill_start_rollback](../long/hill_start_rollback.md) · [hill_start_command](../long/hill_start_command.md) · [julian_day](julian_day.md)

## 同カテゴリ(`env`)

[julian_day](julian_day.md) · [sun_at](sun_at.md) · [sun_events](sun_events.md) · [sun_vector](sun_vector.md) · [sun_illuminance](sun_illuminance.md) · [koschmieder](koschmieder.md) · [beta_from_mor](beta_from_mor.md) · [road_row_distance](road_row_distance.md)

---
*Provenance: driveenv.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
