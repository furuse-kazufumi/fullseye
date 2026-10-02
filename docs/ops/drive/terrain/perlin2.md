---
op: perlin2
dim: drive
category: terrain
in: image2d × image2d
out: table
examples: [poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# perlin2 — DRIVE `terrain` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.perlin2(x, y, seed: 'int' = 0, freq: 'float' = 1.0) -> 'dict'` (実装を直接呼ぶなら `import driveterrain; driveterrain.perlin2(x, y, seed: 'int' = 0, freq: 'float' = 1.0) -> 'dict'`、台帳から引くなら `opsdrive.get("perlin2")`)

## 使い方

Perlin(2002, improved noise)の 2 次元勾配雑音を世界座標 (x, y) で評価する。

格子は ``freq`` [周期/m] の間隔、勾配は 8 方向の単位ベクトル、補間は quintic fade ``6t⁵−15t⁴+10t³``。
返り値 ``{"value", "dx", "dy"}``(導関数は解析的、``d/dx`` は世界座標あたり)。定理: 格子点で値 0、
周期 256 格子、|value| ≤ 1。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`terrain`)

[fbm_params](fbm_params.md) · [fbm_height](fbm_height.md) · [fbm_gradient](fbm_gradient.md) · [radial_periodogram](radial_periodogram.md) · [spectral_slope](spectral_slope.md) · [course_distance](course_distance.md) · [terrain_params](terrain_params.md) · [terrain_height](terrain_height.md)

---
*Provenance: driveterrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
