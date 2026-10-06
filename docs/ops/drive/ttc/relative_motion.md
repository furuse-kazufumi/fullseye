---
op: relative_motion
dim: drive
category: ttc
in: matrix × matrix
out: matrix
examples: [poc_ttc_rss, poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# relative_motion — DRIVE `ttc` op

- **データ種**: `matrix × matrix` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.relative_motion(pose0, pose1, motion=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import drivettc; drivettc.relative_motion(pose0, pose1, motion=None) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("relative_motion")`)

## 使い方

2 コマの間の、カメラ座標で見た点の剛体運動 ``T_rel``(``P_c1 = T_rel · P_c0``)。

``pose0`` / ``pose1`` は各コマの world → camera(:func:`driveworld.camera_pose`)。``motion`` は対象が世界で動いた
4×4(world → world、静止した世界なら None = 単位)。``T_rel = pose1 · motion · pose0⁻¹``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`
- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [foe_from_motion](foe_from_motion.md) · [flow_from_depth_motion](flow_from_depth_motion.md) · [ttc_truth](ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md) · [triangulate_dlt](../balltrack/triangulate_dlt.md)

## 同カテゴリ(`ttc`)

[foe_from_motion](foe_from_motion.md) · [flow_from_depth_motion](flow_from_depth_motion.md) · [ttc_truth](ttc_truth.md) · [ttc_from_flow](ttc_from_flow.md) · [ttc_from_scale](ttc_from_scale.md) · [ttc_from_range](ttc_from_range.md) · [label_extent](label_extent.md) · [foe_from_flow](foe_from_flow.md)

---
*Provenance: drivettc.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
