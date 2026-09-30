---
op: kendama_rig
dim: drive
category: kendamaworld
in: table
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# kendama_rig — DRIVE `kendamaworld` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.kendama_rig(kp: 'dict' = None, *, n: 'int' = 2, distance: 'float' = 1.5, height: 'float' = 1.05, fov_deg: 'float' = 45.0, width: 'int' = 480, height_px: 'int' = 360, target=(0.0, 0.0, 1.0)) -> 'list'` (実装を直接呼ぶなら `import kendamaworld; kendamaworld.kendama_rig(kp: 'dict' = None, *, n: 'int' = 2, distance: 'float' = 1.5, height: 'float' = 1.05, fov_deg: 'float' = 45.0, width: 'int' = 480, height_px: 'int' = 360, target=(0.0, 0.0, 1.0)) -> 'list'`、台帳から引くなら `opsdrive.get("kendama_rig")`)

## 使い方

振り上げの空間(x, y ∈ ±0.4 m、z ∈ 0.55〜1.45 m: 手元 1.0 m、ひも 0.42 m、持ち上げ 0.265 m)を見るカメラの組。
n = 2: 方位 0° と 90°、n = 4: 90° ごと。全部が ``target``(既定 (0, 0, 1.0))を見る。
返り値 ``[{"pose", "K", "eye", "width", "height"}, …]``(ballworld.camera_rig と同型)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`kendamaworld`)

[ken_mesh](ken_mesh.md) · [add_ken](add_ken.md) · [ken_set_pose](ken_set_pose.md) · [string_mesh](string_mesh.md) · [add_string](add_string.md) · [string_set](string_set.md) · [kendama_world](kendama_world.md) · [ken_truth](ken_truth.md)

---
*Provenance: kendamaworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
