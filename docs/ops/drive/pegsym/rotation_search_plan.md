---
op: rotation_search_plan
dim: drive
category: pegsym
in: scalar × scalar
out: table
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# rotation_search_plan — DRIVE `pegsym` op

- **データ種**: `scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.rotation_search_plan(n_sym: 'int', phi_cap: 'float', estimate: 'float' = 0.0, order: 'str' = 'alternate') -> 'dict'` (実装を直接呼ぶなら `import pegsym; pegsym.rotation_search_plan(n_sym: 'int', phi_cap: 'float', estimate: 'float' = 0.0, order: 'str' = 'alternate') -> 'dict'`、台帳から引くなら `opsdrive.get("rotation_search_plan")`)

## 使い方

回転の探索の候補(ペグに加える yaw の補正): 1 周期 P = 2π/n_sym を M = ⌈P/(2 phi_cap)⌉ 等分した刻み s = P/M(≤ 2 phi_cap なので
捕まえる窓が隙間なく覆う)。``order`` = "alternate"(推定値から 0, +s, −s, +2s, …)か "sweep"(0, s, 2s, …)。n_sym = 0(円)は 1 候補。
返り ``angles``(M,)、``step``、``period``、``M``。
**Raises** ValueError: n_sym < 0、phi_cap ≤ 0、order が不明。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_symmetry_search](../../../../examples/poc_peg_symmetry_search.py) — `py -3.11 examples/poc_peg_symmetry_search.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsym`)

[polygon_peg](polygon_peg.md) · [polygon_offset](polygon_offset.md) · [polygon_fit_check](polygon_fit_check.md) · [rotation_window](rotation_window.md) · [polygon_two_point_depth](polygon_two_point_depth.md) · [polygon_coverage_image](polygon_coverage_image.md) · [plane_topview](plane_topview.md) · [polygon_yaw_read](polygon_yaw_read.md)

---
*Provenance: pegsym.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
