---
op: kendama_pose
dim: drive
category: kendamaworld
in: table
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# kendama_pose — DRIVE `kendamaworld` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.kendama_pose(world: 'dict', hand, p_ball, *, R_ken=None, R_ball=None) -> 'dict'` (実装を直接呼ぶなら `import kendamaworld; kendamaworld.kendama_pose(world: 'dict', hand, p_ball, *, R_ken=None, R_ball=None) -> 'dict'`、台帳から引くなら `opsdrive.get("kendama_pose")`)

## 使い方

けん玉の世界の状態を置く: けん(1 つの剛体。持つ所 kp["grip"] を手元 ``hand`` に、姿勢 ``R_ken`` 既定 = kp の技の姿勢
kp["R_ken"]: 皿胴の中心 = hand − R·grip)、玉(中心 ``p_ball``)、
糸(皿胴の糸穴 → 玉の糸穴)。``R_ball`` 既定 = 玉の糸穴(−HOLE_AXIS_LOCAL)が皿胴の糸穴を向く回転(玉の回転は解かない:
張っている間は正しく、飛翔中は近似)。返り値 ``{"tie", "cup" (受ける皿の縁の中心), "cup_axis", "cross" (皿胴の中心), "string_hole", "hole_axis" (大きな穴の向き、世界),
"R_ball"}``。
``world`` は :func:`kendama_world` のもの(world["kendama"] が要る)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`kendamaworld`)

[ken_mesh](ken_mesh.md) · [add_ken](add_ken.md) · [ken_set_pose](ken_set_pose.md) · [string_mesh](string_mesh.md) · [add_string](add_string.md) · [string_set](string_set.md) · [kendama_world](kendama_world.md) · [kendama_rig](kendama_rig.md)

---
*Provenance: kendamaworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
