---
op: mirror_blind_zone
dim: drive
category: decide
in: 
out: table
examples: [poc_driving_decisions]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# mirror_blind_zone — DRIVE `decide` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.mirror_blind_zone(eye_xy, mirror_center_xy, mirror_normal_xy, mirror_width, *, mirror_radius=inf, direct_limit_deg: 'float' = 100.0, roi=(-15.0, -2.0, 0.9, 4.4)) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivedecide; drivedecide.mirror_blind_zone(eye_xy, mirror_center_xy, mirror_normal_xy, mirror_width, *, mirror_radius=inf, direct_limit_deg: 'float' = 100.0, roi=(-15.0, -2.0, 0.9, 4.4)) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("mirror_blind_zone")`)

## 使い方

自車の左後方で、左のドアミラーにも直接の視界にも入らない領域(2D、上から見た図)。

座標は車の x = 前・y = 左。``eye_xy`` = 運転者の眼、``mirror_center_xy`` = 鏡の中心、``mirror_normal_xy`` = 鏡の
法線(眼の側を向く。``mirror_aim_normal`` で作れる)、``mirror_width`` = 鏡の幅(上から見た弦の長さ)、
``mirror_radius`` = 凸面の曲率半径(inf = 平面鏡)。``direct_limit_deg`` = 首を回さずに直接見える方位の上限
(前方から左回り。100° は **仮定**)。``roi`` = (x_min, x_max, y_min, y_max) の対象領域(左の隣の車線。鏡の本体と
車体を含まないように置くこと = 鏡の光線が車体を通るかは見ていない)。

鏡で見える領域 = 鏡の両端で反射した 2 本の光線に挟まれ、かつ鏡の弦より眼の側。直接見える = 眼から見た方位 ≤ 上限。
死角 = roi ∖ (鏡 ∪ 直接) を **互いに素な凸多角形の列** で返す(凸 ∖ 凸 = 半平面を 1 つずつ外した和)。

返り値: ``pieces``(凸多角形 (k, 2) の list)、``area``、``mirror_edges``(両端の点 (2, 2))、
``mirror_rays``(両端の反射光線の単位ベクトル (2, 2))、``mirror_area`` / ``direct_area``(roi の中で見える面積)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_decisions](../../../../examples/poc_driving_decisions.py) — `py -3.11 examples/poc_driving_decisions.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`decide`)

[mirror_reflection_matrix](mirror_reflection_matrix.md) · [mirror_virtual_camera](mirror_virtual_camera.md) · [mirror_aim_normal](mirror_aim_normal.md) · [convex_mirror_fov](convex_mirror_fov.md) · [check_sequence_score](check_sequence_score.md) · [signal_phase_plan](signal_phase_plan.md) · [signal_state](signal_state.md) · [predict_amber_onset](predict_amber_onset.md)

---
*Provenance: drivedecide.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
