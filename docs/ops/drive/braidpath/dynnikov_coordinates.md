---
op: dynnikov_coordinates
dim: drive
category: braidpath
in: signal × scalar
out: table
examples: [poc_braid_homotopy_classes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# dynnikov_coordinates — DRIVE `braidpath` op

- **データ種**: `signal × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dynnikov_coordinates(word, n_strands)` (実装を直接呼ぶなら `import braidpath; braidpath.dynnikov_coordinates(word, n_strands)`、台帳から引くなら `opsdrive.get("dynnikov_coordinates")`)

## 使い方

標準の曲線図 E = (0, …, 0; −1, …, −1) に組紐を作用させた Dynnikov 座標(整数、溢れない)。

n 本の紐に右端の穴を 1 つ足した n + 1 個の穴の円板で取る(a・b とも長さ n − 1)。この作用は忠実なので、
**座標が等しい ⇔ 同じ組紐**。1 文字あたり定数回の加減算と max / min だけで、語の長さに比例する時間で済む
(取っ手簡約や自由群の像と違って膨らまない —— 数が大きくなるだけで、Python の整数は溢れない)。

Returns: dict ``a``・``b``(int の list)、``key``(a + b の tuple、類の鍵に使う)、``n_strands``、``n_punctures``、
``max_abs``(座標の最大の絶対値)、``bits``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_braid_homotopy_classes](../../../../examples/poc_braid_homotopy_classes.py) — `py -3.11 examples/poc_braid_homotopy_classes.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`braidpath`)

[braid_from_trajectories](braid_from_trajectories.md) · [braid_reduce](braid_reduce.md) · [braid_artin_images](braid_artin_images.md) · [dynnikov_act](dynnikov_act.md) · [braid_equivalent](braid_equivalent.md) · [homotopy_class_compare](homotopy_class_compare.md) · [pairwise_winding](pairwise_winding.md) · [homotopy_shortest_paths](homotopy_shortest_paths.md)

---
*Provenance: braidpath.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
