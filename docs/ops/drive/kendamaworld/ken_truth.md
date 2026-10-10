---
op: ken_truth
dim: drive
category: kendamaworld
in: table × table
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# ken_truth — DRIVE `kendamaworld` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ken_truth(world: 'dict', i_ken: 'int', cam: 'dict') -> 'dict'` (実装を直接呼ぶなら `import kendamaworld; kendamaworld.ken_truth(world: 'dict', i_ken: 'int', cam: 'dict') -> 'dict'`、台帳から引くなら `opsdrive.get("ken_truth")`)

## 使い方

けん i_ken の真値の投影: 受ける皿の縁の中心(anchors[kp["catch_cup"] + "_rim"] を姿勢で動かした点)の (col, row)、深度、
像での皿の半径 [px] (大皿の半径で)、
``visible``(カメラの前にあり画素が像の内側)。ballworld.ball_truth と同型。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`kendamaworld`)

[ken_mesh](ken_mesh.md) · [add_ken](add_ken.md) · [ken_set_pose](ken_set_pose.md) · [string_mesh](string_mesh.md) · [add_string](add_string.md) · [string_set](string_set.md) · [kendama_world](kendama_world.md) · [kendama_rig](kendama_rig.md)

---
*Provenance: kendamaworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
