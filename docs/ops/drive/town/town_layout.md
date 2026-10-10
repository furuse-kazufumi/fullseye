---
op: town_layout
dim: drive
category: town
in: 
out: table
examples: [poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# town_layout — DRIVE `town` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.town_layout(name: 'str' = 'default', *, overlap: 'float' = 0.05) -> 'dict'` (実装を直接呼ぶなら `import drivetown; drivetown.town_layout(name: 'str' = 'default', *, overlap: 'float' = 0.05) -> 'dict'`、台帳から引くなら `opsdrive.get("town_layout")`)

## 使い方

既定の町。``"default"`` = road(30) → intersection → road(20) → crossing(踏切) → road(20) → slope → road(20) →
parallel_parking → road(30)(全部幅 7 m、停止線は交差点 1 本と踏切 1 本)。``"short"`` = road(20) → crossing → road(20)
(テストの速い門)。

**Raises** ``ValueError``: 名前が :data:`TOWN_NAMES` に無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_town](../../../../examples/poc_driving_town.py) — `py -3.11 examples/poc_driving_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`town`)

[town_chain](town_chain.md) · [town_world](town_world.md) · [town_centerline](town_centerline.md) · [town_stop_lines](town_stop_lines.md) · [town_rules](town_rules.md) · [town_crossing_state](town_crossing_state.md) · [town_run](town_run.md) · [town_checks](town_checks.md)

---
*Provenance: drivetown.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
