---
op: kendama_world
dim: drive
category: kendamaworld
in: table
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# kendama_world — DRIVE `kendamaworld` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.kendama_world(kp: 'dict', *, floor: 'bool' = True, floor_size: 'float' = 4.0, hand=(0.0, 0.0, 1.0), p_ball=None, hang_deg: 'float' = 12.0, hang_dir=(1.0, -1.0, 0.0), subdiv: 'int' = 3, n: 'int' = 32) -> 'dict'` (実装を直接呼ぶなら `import kendamaworld; kendamaworld.kendama_world(kp: 'dict', *, floor: 'bool' = True, floor_size: 'float' = 4.0, hand=(0.0, 0.0, 1.0), p_ball=None, hang_deg: 'float' = 12.0, hang_dir=(1.0, -1.0, 0.0), subdiv: 'int' = 3, n: 'int' = 32) -> 'dict'`、台帳から引くなら `opsdrive.get("kendama_world")`)

## 使い方

床 + けん(kp の技の姿勢 R_ken、持つ所 kp["grip"] を ``hand`` に)+ 穴のある玉 + 糸の世界。原点は床、z 上。
玉は皿胴の糸穴からひもの有効長(kp["pendulum_length"])だけ下(真下から ``hang_deg`` だけ ``hang_dir`` 側へ振れた位置 ——
斜め (1, −1) なら方位 0° と 90° の両カメラから横ずれが見える)。``p_ball`` を渡せばそこに置く。
床は 0.25 m の升に割る(1 枚の大きな四角形だとカメラの背後にかかる三角形ごと落ちて床が消える)。
返り値の world["kendama"] = ``{"ken", "ball", "string"}``(objects の索引)+ ``"kp"``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`kendamaworld`)

[ken_mesh](ken_mesh.md) · [add_ken](add_ken.md) · [ken_set_pose](ken_set_pose.md) · [string_mesh](string_mesh.md) · [add_string](add_string.md) · [string_set](string_set.md) · [kendama_rig](kendama_rig.md) · [ken_truth](ken_truth.md)

---
*Provenance: kendamaworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
