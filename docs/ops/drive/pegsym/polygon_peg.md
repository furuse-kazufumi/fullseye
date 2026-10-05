---
op: polygon_peg
dim: drive
category: pegsym
in: scalar
out: table
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# polygon_peg — DRIVE `pegsym` op

- **データ種**: `scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.polygon_peg(n: 'int', apothem: 'float' = 0.005, yaw: 'float' = 0.0, cut: 'float' = 0.0, centre=(0.0, 0.0)) -> 'dict'` (実装を直接呼ぶなら `import pegsym; pegsym.polygon_peg(n: 'int', apothem: 'float' = 0.005, yaw: 'float' = 0.0, cut: 'float' = 0.0, centre=(0.0, 0.0)) -> 'dict'`、台帳から引くなら `opsdrive.get("polygon_peg")`)

## 使い方

ペグの断面(反時計回りの頂点列): 正 n 角形(辺心距離 ``apothem`` [m]、面 0 の法線が ``yaw`` [rad])。``cut`` > 0 なら頂点 0
(面 0 と面 1 の間)を、その頂点の向きを法線とする直線で外接円から ``cut`` [m] 内側で落とす —— キー付き(対称は n = 1)。
返り ``vertices``(V, 2)、``n``(形の名目の n 回対称: キー付きは 1)、``apothem``、``circumradius``、``yaw``。
**Raises** ValueError: n < 3、apothem ≤ 0、cut < 0 か外接円と内接円の差以上(辺が消える)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_symmetry_search](../../../../examples/poc_peg_symmetry_search.py) — `py -3.11 examples/poc_peg_symmetry_search.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsym`)

[polygon_offset](polygon_offset.md) · [polygon_fit_check](polygon_fit_check.md) · [rotation_window](rotation_window.md) · [polygon_two_point_depth](polygon_two_point_depth.md) · [polygon_coverage_image](polygon_coverage_image.md) · [plane_topview](plane_topview.md) · [polygon_yaw_read](polygon_yaw_read.md) · [relative_yaw_from_images](relative_yaw_from_images.md)

---
*Provenance: pegsym.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
