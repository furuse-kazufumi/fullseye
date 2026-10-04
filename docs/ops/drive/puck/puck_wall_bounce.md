---
op: puck_wall_bounce
dim: drive
category: puck
in: signal × signal × scalar × scalar
out: table
examples: [poc_air_hockey_intercept]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# puck_wall_bounce — DRIVE `puck` op

- **データ種**: `signal × signal × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.puck_wall_bounce(v, normal, e: 'float', kt: 'float' = 1.0) -> 'dict'` (実装を直接呼ぶなら `import puck; puck.puck_wall_bounce(v, normal, e: 'float', kt: 'float' = 1.0) -> 'dict'`、台帳から引くなら `opsdrive.get("puck_wall_bounce")`)

## 使い方

壁との衝突: 法線成分 vₙ' = −e vₙ、接線成分 vₜ' = kₜ vₜ(e = 法線の反発係数、kₜ = 接線の保持率 = 接線の反発係数)。

回転は持たない(壁の摩擦で入る回転は接線の減りに畳んである。Cross 2022 のディスク衝突は「滑りか把持か」で接線の
反発係数を書く —— その 2 領域は入れていない)。返り値
``{"v", "vn_in", "vn_out", "vt_in", "vt_out", "energy_ratio"}``。法線だけの衝突なら energy_ratio = e²(門)。
``v·n ≥ 0``(離れていく)なら何もしない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_air_hockey_intercept](../../../../examples/poc_air_hockey_intercept.py) — `py -3.11 examples/poc_air_hockey_intercept.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`puck`)

[puck_table](puck_table.md) · [puck_slide_predict](puck_slide_predict.md) · [puck_state_at](puck_state_at.md) · [puck_crossing_point](puck_crossing_point.md) · [puck_mirror_path](puck_mirror_path.md) · [puck_stop_distance](puck_stop_distance.md) · [puck_camera](puck_camera.md) · [puck_pinhole_camera](puck_pinhole_camera.md)

---
*Provenance: puck.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
