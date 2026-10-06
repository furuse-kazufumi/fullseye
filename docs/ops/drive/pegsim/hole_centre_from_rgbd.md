---
op: hole_centre_from_rgbd
dim: drive
category: pegsim
in: rgb × image2d × matrix
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# hole_centre_from_rgbd — DRIVE `pegsim` op

- **データ種**: `rgb × image2d × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.hole_centre_from_rgbd(rgb, depth, K, peg_mask=None, radius: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import pegsim; pegsim.hole_centre_from_rgbd(rgb, depth, K, peg_mask=None, radius: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("hole_centre_from_rgbd")`)

## 使い方

手首 RGB-D 1 枚から穴(暗い円盤)の中心を 3-D(カメラ座標)で: 板の平面を depth で当て、反エイリアスの縁を平面に持ち上げ、
平面内で円を当てる(:func:`measure.fit_circle`)。

画像面の楕円当てはめ(:func:`measure.fit_ellipse`)も参考に返すが、透視では楕円の中心 ≠ 円の中心の投影(試作で最大 1.9 px の
偏り)なので 3-D で当てる。``radius`` に治具の図面の値(面取りの外径 R + W)を渡すと :func:`circle_fit_known_radius` で中心だけを
解く —— ペグが低く構えて縁の半分近くを隠す姿勢(ε = −3 mm、高さ 4 mm)では自由な当てはめの 0.18 px が既知半径で 0.05 px になる。
返り: ``centre_cam``(3,)、``radius``、``rms_circle``、``n_edge``、``edge_uv``、``plane_n``・``plane_c``、
``ellipse``、``uv``(中心の投影)、``peg``(ペグのマスク)。``depth`` は画素中心の +Z 距離 [m] (MSAA の深度は使わない)。
**Raises** ``RuntimeError``: 縁が見つからない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegsim`)

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [two_point_depth](two_point_depth.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
