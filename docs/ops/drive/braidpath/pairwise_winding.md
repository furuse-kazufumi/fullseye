---
op: pairwise_winding
dim: drive
category: braidpath
in: any
out: matrix
examples: [poc_braid_homotopy_classes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# pairwise_winding — DRIVE `braidpath` op

- **データ種**: `any` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.pairwise_winding(trajectories, obstacles=None)` (実装を直接呼ぶなら `import braidpath; braidpath.pairwise_winding(trajectories, obstacles=None)`、台帳から引くなら `opsdrive.get("pairwise_winding")`)

## 使い方

紐の対ごとの相対の巻き数 [回転] (相対ベクトルの偏角の総変化 / 2π)。対称行列、対角は 0。

偏角の増分は atan2(外積, 内積) で取る(主値 (−π, π])。1 刻みで半回転以上回ると向きが決まらないので止める。
閉形式: 純粋な組紐では 2 本の間の交差の符号つきの数を c として 2π·W = π c ちょうど(門)。巻き数は可換な
不変量なので、交換子 [A, B] の形の組紐(全部の対で巻き数 0 なのに自明でない)を区別できない —— それが組紐を使う理由。

Returns: (n, n) の float 配列(n = エージェント + 障害物の点)。
Raises: ValueError(2 本が同じ点に来る、1 刻みの増分が π に届く —— 刻みを細かく)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_braid_homotopy_classes](../../../../examples/poc_braid_homotopy_classes.py) — `py -3.11 examples/poc_braid_homotopy_classes.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`braidpath`)

[braid_from_trajectories](braid_from_trajectories.md) · [braid_reduce](braid_reduce.md) · [braid_artin_images](braid_artin_images.md) · [dynnikov_coordinates](dynnikov_coordinates.md) · [dynnikov_act](dynnikov_act.md) · [braid_equivalent](braid_equivalent.md) · [homotopy_class_compare](homotopy_class_compare.md) · [homotopy_shortest_paths](homotopy_shortest_paths.md)

---
*Provenance: braidpath.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
