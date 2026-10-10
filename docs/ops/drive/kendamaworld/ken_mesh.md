---
op: ken_mesh
dim: drive
category: kendamaworld
in: table
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# ken_mesh — DRIVE `kendamaworld` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ken_mesh(kp: 'dict', *, n: 'int' = 32) -> 'dict'` (実装を直接呼ぶなら `import kendamaworld; kendamaworld.ken_mesh(kp: 'dict', *, n: 'int' = 32) -> 'dict'`、台帳から引くなら `opsdrive.get("ken_mesh")`)

## 使い方

けん + 皿胴(大皿・小皿)+ 中皿のメッシュ。原点 = 皿胴の中心(手元)、けん = +x(けん先が +x)、皿胴の軸 = +z(大皿が上)。

面ラベル: 27 けん・皿胴の胴、28 大皿(皿胴の +z のラッパと皿)、30 小皿(−z)、31 中皿(けんの −x の端の開いた部分)。
返り値 ``{"V", "F", "color" (M,3), "label" (M,), "parts": {"ken": (f0, f1), "cross": (f0, f1)}, "anchors": {...},
"cup_radius", "cup_depth", "ken_length"}``。anchors(局所座標)= ``cross`` (0 = 皿胴の中心)、``spike_tip``、``base_rim``(中皿の縁の中心)、
``big_rim``(大皿の縁の中心)、``small_rim``、``tie``(皿胴の糸穴 (0, −cross_radius, 0))、``big_axis`` (+z)、``small_axis`` (−z)、
``base_axis`` (−x)、``ken_axis`` (+x)、``grip``(技の持つ所 = kp["grip"])。
2 つの閉じた回転体(けん・皿胴)は交わって置かれる(描画は深度で解く)。面は全部外向き(符号つき体積 > 0)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`kendamaworld`)

[add_ken](add_ken.md) · [ken_set_pose](ken_set_pose.md) · [string_mesh](string_mesh.md) · [add_string](add_string.md) · [string_set](string_set.md) · [kendama_world](kendama_world.md) · [kendama_rig](kendama_rig.md) · [ken_truth](ken_truth.md)

---
*Provenance: kendamaworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
