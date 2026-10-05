---
op: rss_longitudinal_check
dim: drive
category: rss
in: table
out: table
examples: [poc_ttc_rss]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# rss_longitudinal_check — DRIVE `rss` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.rss_longitudinal_check(d: 'float', v_rear: 'float', v_front: 'float', p: 'dict', p_front: 'Optional[dict]' = None) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import rsssafety; rsssafety.rss_longitudinal_check(d: 'float', v_rear: 'float', v_front: 'float', p: 'dict', p_front: 'Optional[dict]' = None) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("rss_longitudinal_check")`)

## 使い方

同方向の縦間隔 d(後続の前端 〜 先行の後端、≥ 0)が安全か。

Returns ``{"safe_distance", "dangerous" (d ≤ safe_distance), "margin" (d − safe_distance)}``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](rss_longitudinal_same.md)

## 同カテゴリ(`rss`)

[rss_params](rss_params.md) · [rss_stopping_distance](rss_stopping_distance.md) · [rss_longitudinal_same](rss_longitudinal_same.md) · [rss_longitudinal_opposite](rss_longitudinal_opposite.md) · [rss_lateral](rss_lateral.md) · [rss_lateral_check](rss_lateral_check.md) · [rss_worst_case_gap](rss_worst_case_gap.md) · [rss_worst_case_gap_opposite](rss_worst_case_gap_opposite.md)

---
*Provenance: rsssafety.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
