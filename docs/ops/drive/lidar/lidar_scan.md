---
op: lidar_scan
dim: drive
category: lidar
in: mesh × table × matrix
out: table
examples: [poc_driving_school]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# lidar_scan — DRIVE `lidar` op

- **データ種**: `mesh × table × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lidar_scan(V, F, spec, T_sensor, *, labels=None, seed: 'int' = 0) -> 'dict'` (実装を直接呼ぶなら `import lidarsim; lidarsim.lidar_scan(V, F, spec, T_sensor, *, labels=None, seed: 'int' = 0) -> 'dict'`、台帳から引くなら `opsdrive.get("lidar_scan")`)

## 使い方

メッシュ世界 ``(V, F)`` に姿勢 ``T_sensor``(world ← sensor)の LiDAR を 1 スイープ撃つ。

- ``V`` (N,3) float / ``F`` (M,3) int: 三角形メッシュ(空・非 (N,3)・非有限・範囲外の面番号は
  ``ValueError``)。
- ``spec``: :func:`lidar_spec` の dict。
- ``T_sensor``: 4×4 同次行列(world ← sensor)。センサ座標は x=前, y=左, z=上。
- ``labels``: 面ごとの int ラベル (M,) または None(None なら当たったセルのラベルは 0)。
- ``seed``: ノイズの乱数種(``noise_std == 0`` なら乱数を一切引かず、ビット単位で決定的)。

返り値の dict:
``points`` (K,3) **世界座標**の反射点(行優先: beam 0 の列 0 から)/ ``ranges`` (n_beams, n_az)
[m] (0 = 無返答)/ ``hit_face`` (n_beams, n_az) int(−1 = 無し)/ ``labels`` (n_beams, n_az) int
(−1 = 無し)/ ``beam`` (K,) int / ``col`` (K,) int / ``n_hits`` int。
最近接の面が ``range_min`` 未満または ``range_max`` 超なら無返答(奥の面へ抜けない)。ノイズは
無ノイズ距離で返答の有無を決めた後、``ranges`` と ``points`` に足す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md) · [rss_longitudinal_opposite](../rss/rss_longitudinal_opposite.md)

## 同カテゴリ(`lidar`)

[lidar_spec](lidar_spec.md) · [ray_plane_range](ray_plane_range.md) · [ray_box_ranges](ray_box_ranges.md)

---
*Provenance: lidarsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
