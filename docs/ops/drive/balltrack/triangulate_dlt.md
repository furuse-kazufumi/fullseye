---
op: triangulate_dlt
dim: drive
category: balltrack
in: matrix × any × any
out: table
examples: [poc_ball_bounce, poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# triangulate_dlt — DRIVE `balltrack` op

- **データ種**: `matrix × any × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.triangulate_dlt(uvs, poses, Ks) -> 'dict'` (実装を直接呼ぶなら `import balltrack; balltrack.triangulate_dlt(uvs, poses, Ks) -> 'dict'`、台帳から引くなら `opsdrive.get("triangulate_dlt")`)

## 使い方

1 点の多視点三角測量(線形 DLT、SVD): ``uvs`` (C, 2)、``poses`` (C, 4, 4)、``Ks`` (C, 3, 3)。
返り値 ``{"p" (3,), "reproj_rms" px, "n_views"}``。NaN の視点は飛ばす。2 視点未満なら ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`balltrack`)

[ball_detect](ball_detect.md) · [ball_track](ball_track.md) · [kalman_ca](kalman_ca.md) · [track_triangulate](track_triangulate.md) · [bounce_detect](bounce_detect.md) · [marker_direction](marker_direction.md) · [spin_from_markers](spin_from_markers.md) · [spin_from_marker_sequence](spin_from_marker_sequence.md)

---
*Provenance: balltrack.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
