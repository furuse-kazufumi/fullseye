---
op: spiral_expected_tries
dim: drive
category: pegsym
in: matrix × scalar × scalar
out: table
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# spiral_expected_tries — DRIVE `pegsym` op

- **データ種**: `matrix × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spiral_expected_tries(points, capture: 'float', rho: 'float', grid: 'int' = 161) -> 'dict'` (実装を直接呼ぶなら `import pegsym; pegsym.spiral_expected_tries(points, capture: 'float', rho: 'float', grid: 'int' = 161) -> 'dict'`、台帳から引くなら `opsdrive.get("spiral_expected_tries")`)

## 使い方

横ずれが半径 ``rho`` の円板に一様のとき、点列 ``points`` を順に試して初めて(距離 ≤ ``capture``)捕まえるまでの期待試行回数。
``measured`` = 円板内の格子(grid × grid、円の外は捨てる)の平均。``closed`` = 掃いた面積の近似: k 点で面積 k·p·s を掃くので、半径 r に
達するのは k = πr²/(ps)、r が円板に一様なら E = πρ²/(2ps) + 1/2(p・s は点列から推定: s = 隣の点の距離の中央値、p = 外周の点の半径の
巻きあたりの増分)。どの点でも捕まらない格子点があれば ``uncovered`` > 0(覆いの穴)。
**Raises** ValueError: 点が (N ≥ 3, 2) でない、capture・rho ≤ 0、grid < 11。

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
