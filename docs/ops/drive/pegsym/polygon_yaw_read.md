---
op: polygon_yaw_read
dim: drive
category: pegsym
in: image2d
out: table
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# polygon_yaw_read — DRIVE `pegsym` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.polygon_yaw_read(topview, n: 'int | None' = None, polarity: 'str' = 'dark', K: 'int' = 24, rel: 'float' = 0.02) -> 'dict'` (実装を直接呼ぶなら `import pegsym; pegsym.polygon_yaw_read(topview, n: 'int | None' = None, polarity: 'str' = 'dark', K: 'int' = 24, rel: 'float' = 0.02) -> 'dict'`、台帳から引くなら `opsdrive.get("polygon_yaw_read")`)

## 使い方

上から見た図(:func:`plane_topview`、列 = +x・行 = −y)の物体の輪郭(副画素の等値線、:mod:`pegtactile` と同じ ``threshold_sub_pix``)
の複素フーリエ係数から、向きを**周期 2π/n を法として**読む。n 回対称なら非零の係数は k ≡ 1 (mod n) だけで、
arg(c₁₋ₙ c₁ⁿ⁻¹)/n は始点に依らない(:func:`pegtactile.symmetry_order_contour`)。``n`` を渡すと検出した n でなくその n の位相を使う
(図面で n が分かっている時。実画像の縁の揺れで余分な係数が有意になっても位相は読める)。
``polarity`` = 物体が暗い("dark"、穴)か明るい("bright"、ペグの端面)。濃淡は 2 % と 98 % の分位で 0..1 に伸ばしてから 0.5 の等値線。
返り ``n_detected``・``n_used``・``yaw``(世界の向き、像の行が −y なので符号を戻す、周期 2π/n_used の代表 [0, P))・``centroid_px``
(row, col)・``amps``。n_used = 0(円)なら yaw = nan。
**Raises** ValueError: polarity が不明、像が平ら、輪郭が無い、n < 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_symmetry_search](../../../../examples/poc_peg_symmetry_search.py) — `py -3.11 examples/poc_peg_symmetry_search.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsym`)

[polygon_peg](polygon_peg.md) · [polygon_offset](polygon_offset.md) · [polygon_fit_check](polygon_fit_check.md) · [rotation_window](rotation_window.md) · [polygon_two_point_depth](polygon_two_point_depth.md) · [polygon_coverage_image](polygon_coverage_image.md) · [plane_topview](plane_topview.md) · [relative_yaw_from_images](relative_yaw_from_images.md)

---
*Provenance: pegsym.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
