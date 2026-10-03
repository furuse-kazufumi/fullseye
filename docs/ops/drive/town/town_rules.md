---
op: town_rules
dim: drive
category: town
in: 
out: table
examples: [poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# town_rules — DRIVE `town` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.town_rules(jurisdiction: 'str' = 'JP') -> 'dict'` (実装を直接呼ぶなら `import drivetown; drivetown.town_rules(jurisdiction: 'str' = 'JP') -> 'dict'`、台帳から引くなら `opsdrive.get("town_rules")`)

## 使い方

法規パック(:data:`RULE_PACKS` の複製)。``{"jurisdiction", "side": "left"|"right", "crossing_stop": "always"|"when_active",
"intersection_stop": "signal", "hold_s", "look_required", "look_hold_s", "sources": [...], "verified", "notes"}``。

JP = 左側通行・踏切は常に一時停止 + 安全確認(道路交通法 33 条 1 項、本文で確認済 → verified True)。
US = 右側通行・一般車は警報中だけ停止(州法。**一次確認なし → verified False**)。DE = 右側通行・StVO §19 で遮断機/灯火が
動作している時だけ(**一次確認なし → verified False**)。verified が False の規則は PoC・報告で断定しない。

**Raises** ``ValueError``: 知らない jurisdiction。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_town](../../../../examples/poc_driving_town.py) — `py -3.11 examples/poc_driving_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`town`)

[town_chain](town_chain.md) · [town_layout](town_layout.md) · [town_world](town_world.md) · [town_centerline](town_centerline.md) · [town_stop_lines](town_stop_lines.md) · [town_crossing_state](town_crossing_state.md) · [town_run](town_run.md) · [town_checks](town_checks.md)

---
*Provenance: drivetown.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
