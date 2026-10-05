---
op: world_apply_terrain
dim: drive
category: terrain
in: table × table
out: table
examples: [poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# world_apply_terrain — DRIVE `terrain` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.world_apply_terrain(world: 'dict', p: 'dict', step: 'float' = 2.0) -> 'dict'` (実装を直接呼ぶなら `import driveterrain; driveterrain.world_apply_terrain(world: 'dict', p: 'dict', step: 'float' = 2.0) -> 'dict'`、台帳から引くなら `opsdrive.get("world_apply_terrain")`)

## 使い方

world_build の出力(平らな世界)に地形を掛ける(その場で書き換え、同じ dict を返す)。

路面の升(objects[0] "ground")を terrain_mesh に置き換え、姿勢を持つ物体(資産・木・歩行者)は姿勢の
(x, y) の高さだけ剛体で持ち上げ、持たない物体(縁石・白線・停止線・レール・坂)は頂点ごとに持ち上げる。
``world["terrain"] = p`` を記録する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`terrain`)

[perlin2](perlin2.md) · [fbm_params](fbm_params.md) · [fbm_height](fbm_height.md) · [fbm_gradient](fbm_gradient.md) · [radial_periodogram](radial_periodogram.md) · [spectral_slope](spectral_slope.md) · [course_distance](course_distance.md) · [terrain_params](terrain_params.md)

---
*Provenance: driveterrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
