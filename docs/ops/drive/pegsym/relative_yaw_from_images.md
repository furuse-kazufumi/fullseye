---
op: relative_yaw_from_images
dim: drive
category: pegsym
in: image2d × image2d × scalar
out: table
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# relative_yaw_from_images — DRIVE `pegsym` op

- **データ種**: `image2d × image2d × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.relative_yaw_from_images(peg_view, hole_view, n: 'int', peg_polarity: 'str' = 'bright', hole_polarity: 'str' = 'dark', K: 'int' = 24) -> 'dict'` (実装を直接呼ぶなら `import pegsym; pegsym.relative_yaw_from_images(peg_view, hole_view, n: 'int', peg_polarity: 'str' = 'bright', hole_polarity: 'str' = 'dark', K: 'int' = 24) -> 'dict'`、台帳から引くなら `opsdrive.get("relative_yaw_from_images")`)

## 使い方

ペグ(上向きカメラ → 先端面の平面に打ち直した図)と穴(手首カメラ → 口の平面の図)の向きの差を、n 回対称の商で:
Δ = symmetry_fold(yaw_peg − yaw_hole, n)。どちらも :func:`polygon_yaw_read` で読み、形ごとの位相の定数(頂点の向きと面の向きの差)は
同じ形どうしの差で消える(穴はペグを外へずらした相似形なので)。キー付き(n = 1)は相似でないので、ずれが小さく残る(門で測る)。
返り ``delta``(ペグを −delta 回せば揃う)、``peg``・``hole``(読み)、``n``。
**Raises** ValueError: n < 1、読みが失敗した(:func:`polygon_yaw_read` の例外)。

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
