---
op: rss_longitudinal_opposite
dim: drive
category: rss
in: table
out: scalar
examples: [poc_ttc_rss]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# rss_longitudinal_opposite — DRIVE `rss` op

- **データ種**: `table` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.rss_longitudinal_opposite(v1: 'float', v2: 'float', p1: 'dict', p2: 'Optional[dict]' = None) -> 'float'` (実装を直接呼ぶなら `import rsssafety; rsssafety.rss_longitudinal_opposite(v1: 'float', v2: 'float', p1: 'dict', p2: 'Optional[dict]' = None) -> 'float'`、台帳から引くなら `opsdrive.get("rss_longitudinal_opposite")`)

## 使い方

対向(論文 Lemma two_way / lib ``calculateSafeLongitudinalDistanceOppositeDirection``)の最小安全距離 [m]。

c_1 は正しい車線(v1 ≥ 0、``p1`` の ``brake_min_correct`` で減速)、c_2 は逆走(v2 は負でも大きさでも受けて
``abs``、``p2`` の ``brake_min`` で減速)。両車とも ρ の間 ``accel_max`` で加速。
``d_min = S(v1; ρ_1, a_1, b_correct,1) + S(|v2|; ρ_2, a_2, b_min,2) + max(min_distance_1, min_distance_2)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [road_eval](../long/road_eval.md) · [long_simulate](../long/long_simulate.md) · [stopping_distance_grade](../long/stopping_distance_grade.md) · [stop_line_plan](../long/stop_line_plan.md) · [hill_hold_brake_min](../long/hill_hold_brake_min.md) · [hill_start_rollback](../long/hill_start_rollback.md) · [hill_start_command](../long/hill_start_command.md)

## 同カテゴリ(`rss`)

[rss_params](rss_params.md) · [rss_stopping_distance](rss_stopping_distance.md) · [rss_longitudinal_same](rss_longitudinal_same.md) · [rss_lateral](rss_lateral.md) · [rss_longitudinal_check](rss_longitudinal_check.md) · [rss_lateral_check](rss_lateral_check.md) · [rss_worst_case_gap](rss_worst_case_gap.md) · [rss_worst_case_gap_opposite](rss_worst_case_gap_opposite.md)

---
*Provenance: rsssafety.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
