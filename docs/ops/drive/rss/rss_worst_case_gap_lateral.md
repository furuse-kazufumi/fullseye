---
op: rss_worst_case_gap_lateral
dim: drive
category: rss
in: table
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# rss_worst_case_gap_lateral — DRIVE `rss` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.rss_worst_case_gap_lateral(d0: 'float', v1: 'float', v2: 'float', p1: 'dict', p2: 'Optional[dict]' = None, dt: 'float' = 0.001, t_max: 'Optional[float]' = None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import rsssafety; rsssafety.rss_worst_case_gap_lateral(d0: 'float', v1: 'float', v2: 'float', p1: 'dict', p2: 'Optional[dict]' = None, dt: 'float' = 0.001, t_max: 'Optional[float]' = None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("rss_worst_case_gap_lateral")`)

## 使い方

横方向の最悪ケース: ρ の間 互いに向かって ``lat_accel_max`` → ``lat_brake_min`` で横速度 0 まで減速。

c_1(左)は y = 0、c_2(右)は y = d0 から。+ が右向き。ρ 後の横速度が相手から離れる向きの車は
その時点で止まったと見なす(lib の stated pattern と同じ。離れる運動は間隔を狭めない)。
gap = y_2 − y_1。μ は **最終間隔** の下限(論文 Definition lateral_safe_distance)なので比較は μ を除く:
論文の前提(v_{1,ρ} ≥ 0, v_{2,ρ} ≤ 0)の下で ``min_gap = d0 − max(d_min − μ, 0)``
(μ = ½(μ_1 + μ_2)、d_min = ``rss_lateral``)。前提の外では ``min_gap`` はこの値以下になりうる
(モジュール docstring「最悪ケースの時間積分」)。
Returns ``t, y1, y2, v1, v2, gap, min_gap, t_min, collided (min_gap < 0), margin (μ),
final_gap (両車停止後の間隔 = gap[-1]、t_max で打ち切ればその時刻の間隔), margin_violated (final_gap < μ),
min_gap_closed_form (= d0 − max(d_min − μ, 0)), shortfall (= min_gap_closed_form − min_gap ≥ 0、閉形式が
安全側でない分), paper_assumption (両車の ρ 後の横速度が互いに向いているか), t_stop_1, t_stop_2``。
d0 > d_min ⇔ final_gap > μ(lib の "safe" と同値)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](rss_longitudinal_same.md)

## 同カテゴリ(`rss`)

[rss_params](rss_params.md) · [rss_stopping_distance](rss_stopping_distance.md) · [rss_longitudinal_same](rss_longitudinal_same.md) · [rss_longitudinal_opposite](rss_longitudinal_opposite.md) · [rss_lateral](rss_lateral.md) · [rss_longitudinal_check](rss_longitudinal_check.md) · [rss_lateral_check](rss_lateral_check.md) · [rss_worst_case_gap](rss_worst_case_gap.md)

---
*Provenance: rsssafety.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
