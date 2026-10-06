---
op: dynnikov_act
dim: drive
category: braidpath
in: any × signal
out: table
examples: [poc_braid_homotopy_classes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# dynnikov_act — DRIVE `braidpath` op

- **データ種**: `any × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dynnikov_act(coords, word)` (実装を直接呼ぶなら `import braidpath; braidpath.dynnikov_act(coords, word)`、台帳から引くなら `opsdrive.get("dynnikov_act")`)

## 使い方

任意の Dynnikov 座標 (a; b)(整数でも実数でもよい —— 式は区分線形)に組紐の語を作用させる。

``coords`` は dict(``a``・``b``)か、長さ 2(n − 1) の列(前半 a、後半 b)。紐の本数は n = len(a) + 1。関係式
σᵢσᵢ₊₁σᵢ = σᵢ₊₁σᵢσᵢ₊₁・σᵢσⱼ = σⱼσᵢ・σᵢσᵢ⁻¹ = 1 は**どの (a; b) でも恒等的に**成り立つ(門 1 で乱数の実数座標に)。

Returns: :func:`dynnikov_coordinates` と同じ形の dict(実数の入力なら float のまま)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_braid_homotopy_classes](../../../../examples/poc_braid_homotopy_classes.py) — `py -3.11 examples/poc_braid_homotopy_classes.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`braidpath`)

[braid_from_trajectories](braid_from_trajectories.md) · [braid_reduce](braid_reduce.md) · [braid_artin_images](braid_artin_images.md) · [dynnikov_coordinates](dynnikov_coordinates.md) · [braid_equivalent](braid_equivalent.md) · [homotopy_class_compare](homotopy_class_compare.md) · [pairwise_winding](pairwise_winding.md) · [homotopy_shortest_paths](homotopy_shortest_paths.md)

---
*Provenance: braidpath.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
