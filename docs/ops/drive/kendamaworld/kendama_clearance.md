---
op: kendama_clearance
dim: drive
category: kendamaworld
in: table
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# kendama_clearance — DRIVE `kendamaworld` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.kendama_clearance(kp: 'dict', hand, p_ball, *, R_ken=None, grip=None) -> 'dict'` (実装を直接呼ぶなら `import kendamaworld; kendamaworld.kendama_clearance(kp: 'dict', hand, p_ball, *, R_ken=None, grip=None) -> 'dict'`、台帳から引くなら `opsdrive.get("kendama_clearance")`)

## 使い方

玉の表面からけん玉(けん・皿胴の回転体)までの隙間 [m] (負 = 玉がけん玉にめり込んでいる)。kp の技の姿勢(R_ken、持つ所 grip)で
手元 ``hand``、玉の中心 ``p_ball``(どちらも (3,) か (N, 3))。回転体までの距離は子午面の輪郭までの 2-D の距離と厳密に等しい
ので、メッシュの離散化によらない。返り値 ``{"gap" (N,), "ken" (N,), "cross" (N,)}``(ken / cross = 各部品までの隙間)。
物理はけん玉と玉の衝突を解かないので、この量で「玉がけん玉を突き抜けた」step を数える(門・正直な報告に使う)。
``R_ken``(19 巡目、連続技の持ち替え): 姿勢を kp["R_ken"] の代わりに (3, 3) か時刻ごとの (N, 3, 3) で渡す。``grip`` = 持つ所(局所)の
上書き。どちらも None なら今まで通り。

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
