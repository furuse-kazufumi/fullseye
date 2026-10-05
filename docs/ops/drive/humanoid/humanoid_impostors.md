---
op: humanoid_impostors
dim: drive
category: humanoid
in: table
out: table
examples: [poc_driving_humanoids]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# humanoid_impostors — DRIVE `humanoid` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.humanoid_impostors(clip: 'dict', *, n_yaw: 'int' = 16, n_phase: 'int' = 12, res: 'int' = 128, distance: 'float' = 30.0, light=(0.3, -0.5, 0.8), ambient: 'float' = 0.35) -> 'dict'` (実装を直接呼ぶなら `import drivehumanoid; drivehumanoid.humanoid_impostors(clip: 'dict', *, n_yaw: 'int' = 16, n_phase: 'int' = 12, res: 'int' = 128, distance: 'float' = 30.0, light=(0.3, -0.5, 0.8), ambient: 'float' = 0.35) -> 'dict'`、台帳から引くなら `opsdrive.get("humanoid_impostors")`)

## 使い方

クリップ(:func:`humanoid_walk_clip`)を **方位 n_yaw × 位相 n_phase** の向きから描いておく。

方位 b = 体から見たカメラの向き 2πb / n_yaw(0 = 正面 +x から見る)。カメラは体の高さの中ほどの高さから水平に、
距離 ``distance`` で見る(ほぼ平行投影)。色は :func:`driveworld.world_camera` と同じ Lambert(光はカメラ系)。

Returns:
    ``{"color" (n_yaw, n_phase, res, res, 3) uint8, "mask" (...) bool, "dz" (...) float16 (画素の深度 − distance [m]),
    "f" (事前描画の焦点距離 [px]), "distance", "eye_h" [m], "res", "n_yaw", "n_phase", "cycle_length", "dims",
    "phase_s" (各位相の歩いた距離 [m])}``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_humanoids](../../../../examples/poc_driving_humanoids.py) — `py -3.11 examples/poc_driving_humanoids.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`humanoid`)

[humanoid_clip_mesh](humanoid_clip_mesh.md) · [world_pose_humanoid](world_pose_humanoid.md) · [world_camera_impostors](world_camera_impostors.md)

---
*Provenance: drivehumanoid.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
