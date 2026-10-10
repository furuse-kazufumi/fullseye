---
op: polygon_two_point_depth
dim: drive
category: pegsym
in: matrix × matrix × scalar
out: table
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# polygon_two_point_depth — DRIVE `pegsym` op

- **データ種**: `matrix × matrix × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.polygon_two_point_depth(peg_vertices, hole_vertices, theta: 'float', tilt_dir: 'float' = 0.0, depth_max: 'float' = 0.05, tol: 'float' = 1e-10) -> 'dict'` (実装を直接呼ぶなら `import pegsym; pegsym.polygon_two_point_depth(peg_vertices, hole_vertices, theta: 'float', tilt_dir: 'float' = 0.0, depth_max: 'float' = 0.05, tol: 'float' = 1e-10) -> 'dict'`、台帳から引くなら `opsdrive.get("polygon_two_point_depth")`)

## 使い方

傾けた多角形ペグの二点接触の深さ l₂ [m] (最狭部 z = 0 から先端の中心まで)を厳密に: 深さ l で z ≤ 0 にあるペグの部分は、先端面の
頂点と側面の稜線が z = 0 を切る点の凸包。穴は鉛直な角柱なので、この頂点の水平の射影が平行移動で穴に入る(:func:`polygon_fit_check`)
間は入り、l を深くすると入らなくなる —— その境を二分法で。``tilt_dir`` = 傾ける水平の向き [rad] (世界系、ペグの断面と同じ系)。
比べる円の式(Whitney、pegsim の 3-D 円柱の厳密式 (2R − r(cos θ + sec θ))/tan θ)を、内接円(r = A、R = A + δ)と外接円
(r = A/cos(π/n)、R = (A + δ)/cos(π/n))で返す(``circle_in``・``circle_out``)。正方形を面に平行な軸で傾けた時の小角の極限は
Goli ほか 2024 の式 (2.28) φ = (v − v′)/h、すなわち l₂ tan θ → 2δ(``goli_small_angle`` = 2δ/tan θ)。
奇数の n(三角形)は面の向かいが頂点なので、どの向きでも内接円の式より深い。偶数の n は面の法線の向きで内接円の式に一致する
(正方形で 1e-11 m)。内接円の側に 0.03 % まで出る組がある(傾き 6°、面から 15°)。
返り ``l2``・``circle_in``・``circle_out``・``goli_small_angle``(δ は辺心距離の差の平均、n は頂点数)。
**Raises** ValueError: θ ≤ 0 か ≥ 30°、まっすぐでも入らない、depth_max まで二点接触しない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_symmetry_search](../../../../examples/poc_peg_symmetry_search.py) — `py -3.11 examples/poc_peg_symmetry_search.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsym`)

[polygon_peg](polygon_peg.md) · [polygon_offset](polygon_offset.md) · [polygon_fit_check](polygon_fit_check.md) · [rotation_window](rotation_window.md) · [polygon_coverage_image](polygon_coverage_image.md) · [plane_topview](plane_topview.md) · [polygon_yaw_read](polygon_yaw_read.md) · [relative_yaw_from_images](relative_yaw_from_images.md)

---
*Provenance: pegsym.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
