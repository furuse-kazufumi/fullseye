---
op: rss_lateral
dim: drive
category: rss
in: table
out: scalar
examples: [poc_ttc_rss]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# rss_lateral — DRIVE `rss` op

- **データ種**: `table` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.rss_lateral(v1: 'float', v2: 'float', p1: 'dict', p2: 'Optional[dict]' = None) -> 'float'` (実装を直接呼ぶなら `import rsssafety; rsssafety.rss_lateral(v1: 'float', v2: 'float', p1: 'dict', p2: 'Optional[dict]' = None) -> 'float'`、台帳から引くなら `opsdrive.get("rss_lateral")`)

## 使い方

横方向(論文 Lemma lateral / lib ``calculateSafeLateralDistance``)の最小安全距離 [m]。c_1 が左。

横速度は **+ が右向き**(左の車が相手へ向かう向き)。``d_min = [ 左のオフセット − 右のオフセット
+ ½(μ_1 + μ_2) ]_+`` で、左 = ``S(v1; ρ_1, +a_lat,1, b_lat,1, direction=+1)``、
右 = ``S(v2; ρ_2, −a_lat,2, b_lat,2, direction=−1)``。
ρ 後の横速度が互いに向いている範囲(v_{1,ρ} ≥ 0, v_{2,ρ} ≤ 0、かつ 左 − 右 ≥ 0)では論文の式
``μ + [ (v_1 + v_{1,ρ})/2 ρ + v_{1,ρ}²/(2b) − ((v_2 + v_{2,ρ})/2 ρ − v_{2,ρ}²/(2b)) ]_+`` と一致する。
それ以外では lib に従う(モジュール docstring「論文と ad-rss-lib が違う所」)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[road_eval](../long/road_eval.md) · [long_simulate](../long/long_simulate.md) · [stopping_distance_grade](../long/stopping_distance_grade.md) · [stop_line_plan](../long/stop_line_plan.md) · [hill_hold_brake_min](../long/hill_hold_brake_min.md) · [hill_start_rollback](../long/hill_start_rollback.md) · [hill_start_command](../long/hill_start_command.md)

## 同カテゴリ(`rss`)

[rss_params](rss_params.md) · [rss_stopping_distance](rss_stopping_distance.md) · [rss_longitudinal_same](rss_longitudinal_same.md) · [rss_longitudinal_opposite](rss_longitudinal_opposite.md) · [rss_longitudinal_check](rss_longitudinal_check.md) · [rss_lateral_check](rss_lateral_check.md) · [rss_worst_case_gap](rss_worst_case_gap.md) · [rss_worst_case_gap_opposite](rss_worst_case_gap_opposite.md)

---
*Provenance: rsssafety.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
