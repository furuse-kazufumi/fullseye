---
op: town_world
dim: drive
category: town
in: table
out: table
examples: [poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# town_world — DRIVE `town` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.town_world(layout, *, props=(), **kwargs) -> 'dict'` (実装を直接呼ぶなら `import drivetown; drivetown.town_world(layout, *, props=(), **kwargs) -> 'dict'`、台帳から引くなら `opsdrive.get("town_world")`)

## 使い方

:func:`driveworld.world_build` の薄い包み(``props`` と残りの引数をそのまま渡す)に、停止線・信号・踏切の位置の表を
``world["town"]`` として足し、踏切の要素ごとに **遮断機つき警報機 2 基・遮断かん(上がり)・踏切の板・列車(遠くに待機)** を置く。

``world["town"] = {"stop_lines": [(x, y, yaw, kind)], "signals": [(x, y, yaw, kind)], "crossings": [(x0, y0, x1, y1, s0, s1)],
"gear": [踏切ごとの設備の索引 dict], "total_length"}``(signals は交差点の 4 基全部、yaw = 灯器が向く向き。stop_lines は
左側通行の物)。設備の状態は :func:`town_crossing_state` で時刻ごとに書き換える。

**Raises** ``ValueError``: layout が town_chain の物でない(world_build の例外はそのまま)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_town](../../../../examples/poc_driving_town.py) — `py -3.11 examples/poc_driving_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`town`)

[town_chain](town_chain.md) · [town_layout](town_layout.md) · [town_centerline](town_centerline.md) · [town_stop_lines](town_stop_lines.md) · [town_rules](town_rules.md) · [town_crossing_state](town_crossing_state.md) · [town_run](town_run.md) · [town_checks](town_checks.md)

---
*Provenance: drivetown.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
