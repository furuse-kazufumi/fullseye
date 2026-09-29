---
op: ball_detect
dim: drive
category: balltrack
in: image2d
out: table
examples: [poc_ball_bounce, poc_driving_school]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# ball_detect — DRIVE `balltrack` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ball_detect(image, *, mode: 'str' = 'bright', thresh=None, color=None, color_tol: 'float' = 0.25, radius_range=(1.5, 80.0), max_candidates: 'int' = 8) -> 'list'` (実装を直接呼ぶなら `import balltrack; balltrack.ball_detect(image, *, mode: 'str' = 'bright', thresh=None, color=None, color_tol: 'float' = 0.25, radius_range=(1.5, 80.0), max_candidates: 'int' = 8) -> 'list'`、台帳から引くなら `opsdrive.get("ball_detect")`)

## 使い方

画像から球の候補を出す: しきい値 → 連結成分 → 明るさ重みのサブピクセル重心・等価半径・充填率。

``mode`` = "bright"(明るい塊、``thresh`` 既定 = 平均 + 2σ)/ "dark"(暗い塊)/ "color"(``color`` (3,) との RGB 距離 < color_tol)/
"chroma"(明るさで正規化した色の距離 < color_tol: 陰影に強い)。
返り値 = ``[{"col", "row", "radius", "area", "fill", "score"}, …]``(score 降順、fill = 面積 / 外接円の面積で球らしさ)。
半径が ``radius_range`` の外の塊は捨てる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`balltrack`)

[ball_track](ball_track.md) · [kalman_ca](kalman_ca.md) · [triangulate_dlt](triangulate_dlt.md) · [track_triangulate](track_triangulate.md) · [bounce_detect](bounce_detect.md) · [marker_direction](marker_direction.md) · [spin_from_markers](spin_from_markers.md) · [reproject](reproject.md)

---
*Provenance: balltrack.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
