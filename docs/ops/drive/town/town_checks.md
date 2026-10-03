---
op: town_checks
dim: drive
category: town
in: table × table
out: table
examples: [poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# town_checks — DRIVE `town` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.town_checks(run, layout, *, car_length: 'float' = 4.5, tol: 'float' = 1e-09) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivetown; drivetown.town_checks(run, layout, *, car_length: 'float' = 4.5, tol: 'float' = 1e-09) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("town_checks")`)

## 使い方

通し走行の採点(閉形式の門 + 既存の踏切の採点 op)。

``stops``: 目標になった停止線ごと(弧長順)に ``{"kind", "s_line", "s_stop", "before" = s_line − s_stop, "ok" (0 ≤ before ≤ 1.0),
"crossing": crossing_stop_check の結果(踏切だけ。``train`` があれば警報中の区間を forbidden_intervals に渡す),
"skipped": 動的な目標で止まらなかった}``。``count_ok`` = 停止の回数 = 静的な停止線 + 止まった動的な停止線の数。
``kinematics``: ``{"a_max_abs", "v_max", "v_min", "integral_gap" = max|台形則 ∫v dt − (s − s0)|, "ok"}``
(|a| ≤ max(a_max, b_max)、0 ≤ v ≤ v_max、integral_gap ≤ dt·v_max)。``braking``: 停止ごとに減速を始めた速度 v_b と制動距離 d_b、
定理 d_b ≥ v_b²/(2 b_max) の ok。``train``(列車があれば): ``{"inside_while_forbidden_s"(警報中に車体が踏切面にかかっていた
時間)、"go_after_clear"(踏切の発進が警報停止 + 上昇の後)、"timing_meets_minimum", "ok"}``。``ok`` = 全部。

**Raises** ``ValueError``: run が town_run の物でない、layout が town_chain の物でない、car_length が正でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_town](../../../../examples/poc_driving_town.py) — `py -3.11 examples/poc_driving_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`town`)

[town_chain](town_chain.md) · [town_layout](town_layout.md) · [town_world](town_world.md) · [town_centerline](town_centerline.md) · [town_stop_lines](town_stop_lines.md) · [town_rules](town_rules.md) · [town_crossing_state](town_crossing_state.md) · [town_run](town_run.md)

---
*Provenance: drivetown.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
