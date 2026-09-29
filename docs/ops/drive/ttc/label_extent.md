---
op: label_extent
dim: drive
category: ttc
in: labels2d
out: table
examples: [poc_ttc_rss]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# label_extent — DRIVE `ttc` op

- **データ種**: `labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.label_extent(label, value: 'int') -> 'dict'` (実装を直接呼ぶなら `import drivettc; drivettc.label_extent(label, value: 'int') -> 'dict'`、台帳から引くなら `opsdrive.get("label_extent")`)

## 使い方

ラベル像の中で値 ``value`` の画素の箱: ``{"col0", "col1", "row0", "row1", "width", "height", "n"}``。

幅・高さは画素数(``col1 − col0 + 1``)。無ければ全部 0。:func:`ttc_from_scale` の入力(完全な検出器の代役)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ttc`)

[relative_motion](relative_motion.md) · [foe_from_motion](foe_from_motion.md) · [flow_from_depth_motion](flow_from_depth_motion.md) · [ttc_truth](ttc_truth.md) · [ttc_from_flow](ttc_from_flow.md) · [ttc_from_scale](ttc_from_scale.md) · [ttc_from_range](ttc_from_range.md) · [foe_from_flow](foe_from_flow.md)

---
*Provenance: drivettc.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
