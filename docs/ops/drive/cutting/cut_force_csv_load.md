---
op: cut_force_csv_load
dim: drive
category: cutting
in: any × any
out: table
examples: [poc_food_cutting_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# cut_force_csv_load — DRIVE `cutting` op

- **データ種**: `any × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cut_force_csv_load(path, license: 'str') -> 'dict'` (実装を直接呼ぶなら `import cutting; cutting.cut_force_csv_load(path, license: 'str') -> 'dict'`、台帳から引くなら `opsdrive.get("cut_force_csv_load")`)

## 使い方

有限要素の切断シミュレーションが書いた刃の力の CSV を読む(1 行目に ``Rcforc``、2 行目が列名、列 = 時刻と力の 3 成分が交互)。

想定しているのは arXiv:2105.12244 が公開したデータセット(CC BY-NC 4.0 = 非商用)。``license`` は呼び手が**必ず**書く
(データの使い道を返り値に残すため、空なら ValueError)。データは repo に入れず、置き場所は環境変数で渡す。
返り値: ``t_s``、``F_xyz``(N、(N, 3))、``license``、``path`` は返さない(ローカルパスを記録に残さない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_food_cutting_measure](../../../../examples/poc_food_cutting_measure.py) — `py -3.11 examples/poc_food_cutting_measure.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`cutting`)

[cutting_scene](cutting_scene.md) · [cutting_face_render](cutting_face_render.md) · [cutting_edge_render](cutting_edge_render.md) · [cutting_episode_synth](cutting_episode_synth.md) · [cutting_wrist_mjcf](cutting_wrist_mjcf.md) · [knife_edge_track](knife_edge_track.md) · [cut_depth_from_side](cut_depth_from_side.md) · [slice_thickness_profile](slice_thickness_profile.md)

---
*Provenance: cutting.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
