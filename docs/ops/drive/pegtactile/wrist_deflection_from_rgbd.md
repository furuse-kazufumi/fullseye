---
op: wrist_deflection_from_rgbd
dim: drive
category: pegtactile
in: rgb × image2d × matrix × matrix × signal × signal × scalar
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# wrist_deflection_from_rgbd — DRIVE `pegtactile` op

- **データ種**: `rgb × image2d × matrix × matrix × signal × signal × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.wrist_deflection_from_rgbd(rgb, depth, K, R_cam_to_world, cam_w, carriage_pos, r_peg: 'float', hinge_z: 'float' = 0.0) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.wrist_deflection_from_rgbd(rgb, depth, K, R_cam_to_world, cam_w, carriage_pos, r_peg: 'float', hinge_z: 'float' = 0.0) -> 'dict'`、台帳から引くなら `opsdrive.get("wrist_deflection_from_rgbd")`)

## 使い方

手首 RGB-D 1 枚から手首の並進たわみと傾き: ペグの画素(pegsim の色分類)→ depth の点群 → PCA の軸 → 既知半径の円柱当てはめ
(:func:`pegsim.cylinder_fit_known_radius`)→ 世界系の軸の直線 → 搬送台の系(エンコーダで既知の位置 ``carriage_pos`` を引く)で
ヒンジの高さ z = ``hinge_z`` を通る点 = (Δx, Δy)。軸の向きから傾き (θ_x, θ_y) を atan2 で。円柱の軸方向の位置は見えないので
Δz は出さない(正直に: 手首の z 圧縮は k̂ と触覚の F_z で補う、:func:`pegtactile_process_episode`)。
返り ``dx``・``dy``・``axis``・``tilt_x``・``tilt_y``・``rms_cyl``・``n_pts``。
**Raises** ValueError: 形が合わない、ペグの画素が 50 未満(見えない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegtactile`)

[pad_params](pad_params.md) · [pad_context](pad_context.md) · [peg_wrench_to_pad_loads](peg_wrench_to_pad_loads.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_shear_asymmetry](pad_shear_asymmetry.md) · [pad_marker_displacement](pad_marker_displacement.md) · [pad_tactile_frame](pad_tactile_frame.md) · [pad_tactile_read](pad_tactile_read.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
