---
op: town_chain
dim: drive
category: town
in: any
out: table
examples: [poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# town_chain — DRIVE `town` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.town_chain(elements, *, start=(0.0, 0.0, 0.0), overlap: 'float' = 0.05) -> 'dict'` (実装を直接呼ぶなら `import drivetown; drivetown.town_chain(elements, *, start=(0.0, 0.0, 0.0), overlap: 'float' = 0.05) -> 'dict'`、台帳から引くなら `opsdrive.get("town_chain")`)

## 使い方

要素を順に継いで配置する: 要素 k+1 の entry を要素 k の exit(の ``overlap`` 手前)に合わせる剛体配置を閉形式で求め、
:func:`drivecourse.course_layout` に渡す。

Parameters
----------
elements : drivecourse の要素(dict)の列。順に継ぐ。
start : 最初の要素の entry を置く世界姿勢 (x, y, yaw)。
overlap : 継ぎ目の食い込み [m] (≥ 0。3-D 化で継ぎ目に縁石が立たないため)。要素の中心線より短いこと。

Returns
-------
dict : course_layout の dict に ``"chain"`` を足したもの。``chain = {"overlap", "s_start" (n,) 各要素の entry の
弧長, "lengths" (n,) 各要素の centerline_length, "polyline_lengths" (n,) 中心線の折線長, "total_length"
(= Σ 折線長 − overlap × (n − 1)), "joints": [(exit_k, entry_k+1), ...] 世界姿勢}``。

**Raises** ``ValueError``: 要素が空・layout の入れ子・entry/exit/centerline が無い、start/overlap が非有限、overlap が負、
overlap が要素の中心線より長い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_town](../../../../examples/poc_driving_town.py) — `py -3.11 examples/poc_driving_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`town`)

[town_layout](town_layout.md) · [town_world](town_world.md) · [town_centerline](town_centerline.md) · [town_stop_lines](town_stop_lines.md) · [town_rules](town_rules.md) · [town_crossing_state](town_crossing_state.md) · [town_run](town_run.md) · [town_checks](town_checks.md)

---
*Provenance: drivetown.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
