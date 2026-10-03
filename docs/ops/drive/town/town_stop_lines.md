---
op: town_stop_lines
dim: drive
category: town
in: table
out: table
examples: [poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# town_stop_lines — DRIVE `town` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.town_stop_lines(layout, *, side: 'str' = 'left') -> 'List[dict]'` (実装を直接呼ぶなら `import drivetown; drivetown.town_stop_lines(layout, *, side: 'str' = 'left') -> 'List[dict]'`、台帳から引くなら `opsdrive.get("town_stop_lines")`)

## 使い方

町の停止線を弧長順に並べる: ``[{"s", "x", "y", "yaw", "kind", "element", "crossing_zone": (s0, s1) | None,
"drawn": bool}, ...]``。

交差点: 要素の ``stop_lines``(線分 (2, 2))のうち **中心線に端点が載り、進行方向の ``side`` の側へ延びる物** が走行路の
停止線(4 本のうち 1 本。左側通行なら左、右側通行なら鏡像の 1 本)。踏切: 停止線の位置は **踏切面 − stop_setback の閉形式**
(drivecourse は左車線にしか白線を描かないので side に依らない。``drawn`` = その側に白線が描かれているか)。
``s`` は中心線上の弧長、``yaw`` はそこでの進行方向。踏切は踏切面の弧長の範囲 ``crossing_zone`` も付ける。

**Raises** ``ValueError``: layout が town_chain の物でない、side が left/right でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_town](../../../../examples/poc_driving_town.py) — `py -3.11 examples/poc_driving_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`town`)

[town_chain](town_chain.md) · [town_layout](town_layout.md) · [town_world](town_world.md) · [town_centerline](town_centerline.md) · [town_rules](town_rules.md) · [town_crossing_state](town_crossing_state.md) · [town_run](town_run.md) · [town_checks](town_checks.md)

---
*Provenance: drivetown.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
