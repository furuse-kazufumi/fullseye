---
op: rotation_from_omega
dim: drive
category: ballworld
in: 
out: matrix
examples: [poc_ball_bounce]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# rotation_from_omega — DRIVE `ballworld` op

- **データ種**: `なし` → `matrix`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.rotation_from_omega(omega, dt: 'float') -> 'np.ndarray'` (実装を直接呼ぶなら `import ballworld; ballworld.rotation_from_omega(omega, dt: 'float') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("rotation_from_omega")`)

## 使い方

角速度 ω [rad/s] で dt 秒回す回転行列(Rodrigues)。R_{k+1} = R(ω dt) R_k。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`ballworld`)

[table_params](table_params.md) · [table_world](table_world.md) · [ball_mesh](ball_mesh.md) · [add_ball](add_ball.md) · [ball_set_pose](ball_set_pose.md) · [camera_rig](camera_rig.md) · [ball_truth](ball_truth.md) · [icosphere](icosphere.md)

---
*Provenance: ballworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
