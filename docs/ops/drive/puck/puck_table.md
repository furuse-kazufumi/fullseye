---
op: puck_table
dim: drive
category: puck
in: 
out: table
examples: [poc_air_hockey_intercept]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# puck_table — DRIVE `puck` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.puck_table(*, x_half: 'float' = 0.974, y_half: 'float' = 0.519, puck_radius: 'float' = 0.03165, mass: 'float' = 0.01, mu: 'float' = 0.02, e: 'float' = 0.8, kt: 'float' = 1.0, g: 'float' = 9.81, goal_half: 'float' = 0.125, damping: 'float' = 0.005) -> 'dict'` (実装を直接呼ぶなら `import puck; puck.puck_table(*, x_half: 'float' = 0.974, y_half: 'float' = 0.519, puck_radius: 'float' = 0.03165, mass: 'float' = 0.01, mu: 'float' = 0.02, e: 'float' = 0.8, kt: 'float' = 1.0, g: 'float' = 9.81, goal_half: 'float' = 0.125, damping: 'float' = 0.005) -> 'dict'`、台帳から引くなら `opsdrive.get("puck_table")`)

## 使い方

台とパックの数(既定は Robot Air Hockey Challenge の ``table.xml`` から読んだ値、MIT、arXiv 2411.05718)。

壁の内面: 端の rim は中心 |x| = 1.019・半厚 0.045 → ``x_half`` = 0.974、横の rim は |y| = 0.564・半厚 0.045 → ``y_half`` = 0.519。
端の rim は |y| < 0.125 が空いている(ゴール、``goal_half``)。パック: 円柱 半径 0.03165、質量 0.01 kg。
``mu``(Coulomb)と ``e``・``kt``(壁の法線・接線の反発係数)は MJCF に **無い**(減速は粘性 ``damping``、壁は軟接触)ので
こちらの既定は仮定。返り値は dict(``table`` sort)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_air_hockey_intercept](../../../../examples/poc_air_hockey_intercept.py) — `py -3.11 examples/poc_air_hockey_intercept.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`puck`)

[puck_wall_bounce](puck_wall_bounce.md) · [puck_slide_predict](puck_slide_predict.md) · [puck_state_at](puck_state_at.md) · [puck_crossing_point](puck_crossing_point.md) · [puck_mirror_path](puck_mirror_path.md) · [puck_stop_distance](puck_stop_distance.md) · [puck_camera](puck_camera.md) · [puck_pinhole_camera](puck_pinhole_camera.md)

---
*Provenance: puck.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
