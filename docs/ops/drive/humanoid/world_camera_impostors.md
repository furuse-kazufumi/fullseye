---
op: world_camera_impostors
dim: drive
category: humanoid
in: table × matrix × matrix
out: table
examples: [poc_driving_humanoids]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# world_camera_impostors — DRIVE `humanoid` op

- **データ種**: `table × matrix × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.world_camera_impostors(world: 'dict', pose, K, width: 'int' = 640, height: 'int' = 400, actors=(), **camera_kw) -> 'dict'` (実装を直接呼ぶなら `import drivehumanoid; drivehumanoid.world_camera_impostors(world: 'dict', pose, K, width: 'int' = 640, height: 'int' = 400, actors=(), **camera_kw) -> 'dict'`、台帳から引くなら `opsdrive.get("world_camera_impostors")`)

## 使い方

:func:`driveworld.world_camera` で世界を撮り、``actors`` のインポスタを**深度で前後を比べて**貼る。

``actors`` = ``[{"imp": humanoid_impostors の返り値, "x", "y", "yaw", "distance" (歩いた距離 [m])}, …]``。
向きの段 = 体から見たカメラの方位を n_yaw 段に丸めたもの、位相 = 歩いた距離を周期で割った余りに最も近い段。
大きさ = 実際のカメラの「1 m あたりの画素」/ 事前描画の「1 m あたりの画素」(最近傍で拡大縮小)。
返り値は world_camera と同じ鍵。貼った画素は ``label`` = 物体のラベル(7)、``face`` = −2(三角形が無い)、
``shade`` = 1。加えて ``"impostor_pixels"``(貼った画素の数)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_humanoids](../../../../examples/poc_driving_humanoids.py) — `py -3.11 examples/poc_driving_humanoids.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`humanoid`)

[humanoid_clip_mesh](humanoid_clip_mesh.md) · [world_pose_humanoid](world_pose_humanoid.md) · [humanoid_impostors](humanoid_impostors.md)

---
*Provenance: drivehumanoid.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
