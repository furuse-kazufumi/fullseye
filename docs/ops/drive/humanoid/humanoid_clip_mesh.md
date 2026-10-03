---
op: humanoid_clip_mesh
dim: drive
category: humanoid
in: table
out: table
examples: [poc_driving_humanoids]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# humanoid_clip_mesh — DRIVE `humanoid` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.humanoid_clip_mesh(clip: 'dict', distance: 'float') -> 'dict'` (実装を直接呼ぶなら `import drivehumanoid; drivehumanoid.humanoid_clip_mesh(clip: 'dict', distance: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("humanoid_clip_mesh")`)

## 使い方

歩いた距離 ``distance`` [m] でのメッシュ(``{"V","F","color","label","dims"}``、原点 = 腰の真下、+x = 前)。

1 周期で ``cycle_length`` 進む。コマの間は頂点を線形に補間する(面の組み方は全コマ同じ)。形は腰の真下が原点のまま
なので、**置く位置を ``distance`` だけ進めれば**支持脚は地面で止まって見える(コマの位相は ``advance`` で歩いた距離に
合わせてある)。★2026-10-03: 最初の版は周期内の前進をここでも差し引き、置く側と 2 重に引いていた(滑りの門で発覚)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_humanoids](../../../../examples/poc_driving_humanoids.py) — `py -3.11 examples/poc_driving_humanoids.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`humanoid`)

[world_pose_humanoid](world_pose_humanoid.md) · [humanoid_impostors](humanoid_impostors.md) · [world_camera_impostors](world_camera_impostors.md)

---
*Provenance: drivehumanoid.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
