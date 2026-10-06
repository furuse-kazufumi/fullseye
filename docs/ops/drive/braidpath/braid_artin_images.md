---
op: braid_artin_images
dim: drive
category: braidpath
in: signal × scalar
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# braid_artin_images — DRIVE `braidpath` op

- **データ種**: `signal × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.braid_artin_images(word, n_strands, max_length=200000)` (実装を直接呼ぶなら `import braidpath; braidpath.braid_artin_images(word, n_strands, max_length=200000)`、台帳から引くなら `opsdrive.get("braid_artin_images")`)

## 使い方

組紐の Artin 表現: 自由群 F_n の生成元 x₁..xₙ の像(自由簡約した語)。

σᵢ: xᵢ ↦ xᵢ xᵢ₊₁ xᵢ⁻¹、xᵢ₊₁ ↦ xᵢ、ほかは動かさない。語 w = σ_{i1} σ_{i2} … の像は左から順に代入して作る。
この表現は忠実(Artin 1925)なので、**像が全部一致 ⇔ 同じ組紐**。自由簡約だけの厳密な判定で、Dynnikov 座標と
独立に「等しい」を確かめる第 2 実装になる。像の長さは語の長さに対して指数で伸びうるので ``max_length`` で止める。

Returns: dict ``images``(長さ n の list、各要素は符号つき整数の list で ±k = x_k^(±1))、``lengths``、``identity``
(全部 xₖ そのものか)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`braidpath`)

[braid_from_trajectories](braid_from_trajectories.md) · [braid_reduce](braid_reduce.md) · [dynnikov_coordinates](dynnikov_coordinates.md) · [dynnikov_act](dynnikov_act.md) · [braid_equivalent](braid_equivalent.md) · [homotopy_class_compare](homotopy_class_compare.md) · [pairwise_winding](pairwise_winding.md) · [homotopy_shortest_paths](homotopy_shortest_paths.md)

---
*Provenance: braidpath.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
