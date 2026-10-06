---
op: rss_worst_case_gap_opposite
dim: drive
category: rss
in: table
out: table
examples: [poc_ttc_rss]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# rss_worst_case_gap_opposite — DRIVE `rss` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.rss_worst_case_gap_opposite(d0: 'float', v1: 'float', v2: 'float', p1: 'dict', p2: 'Optional[dict]' = None, dt: 'float' = 0.001, t_max: 'Optional[float]' = None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import rsssafety; rsssafety.rss_worst_case_gap_opposite(d0: 'float', v1: 'float', v2: 'float', p1: 'dict', p2: 'Optional[dict]' = None, dt: 'float' = 0.001, t_max: 'Optional[float]' = None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("rss_worst_case_gap_opposite")`)

## 使い方

対向の最悪ケース: 両車 ρ の間 ``accel_max`` で加速 → c_1 は ``brake_min_correct``、c_2 は ``brake_min`` で停止。

c_1 は x = 0 から +x へ、c_2 は x = d0 から −x へ(v2 は絶対値)。gap = x_2 − x_1。
Returns ``t, x1, x2, v1, v2, gap, min_gap, t_min, collided, t_stop_1, t_stop_2``。
``min_gap = d0 − (d_min − max(min_distance))`` が成り立つ(d_min = ``rss_longitudinal_opposite``)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](rss_longitudinal_same.md)

## 同カテゴリ(`rss`)

[rss_params](rss_params.md) · [rss_stopping_distance](rss_stopping_distance.md) · [rss_longitudinal_same](rss_longitudinal_same.md) · [rss_longitudinal_opposite](rss_longitudinal_opposite.md) · [rss_lateral](rss_lateral.md) · [rss_longitudinal_check](rss_longitudinal_check.md) · [rss_lateral_check](rss_lateral_check.md) · [rss_worst_case_gap](rss_worst_case_gap.md)

---
*Provenance: rsssafety.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
