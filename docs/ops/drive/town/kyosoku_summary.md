---
op: kyosoku_summary
dim: drive
category: town
in: 
out: table
examples: [poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# kyosoku_summary — DRIVE `town` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.kyosoku_summary(path=None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivetown; drivetown.kyosoku_summary(path=None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("kyosoku_summary")`)

## 使い方

教則の場面の再現台帳(docs/drive/kyosoku_scenarios.json)を読み、category × status の件数表にする。

``path`` = None なら repo の ``docs/drive/kyosoku_scenarios.json``(このモジュールの場所から引く)。
返り値 ``{"total", "statuses" (順序つき), "by_status": {status: n}, "categories": [...] (件数の多い順),
"by_category": {category: {status: n}}, "table": [[category, n_reproduced, n_partial, n_pending, n_not_reproducible, total], ...]}``。

**Raises** ``ValueError``: ファイルが無い・JSON でない・``scenarios`` が無い・場面に id/category/status が無い・
status が :data:`KYOSOKU_STATUSES` に無い・id が重複。

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
