---
op: plane_segmentation
dim: 3d
category: segment
in: points
out: labels
examples: [object_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# plane_segmentation — 3D `segment` op

- **データ種**: `points` → `labels`
- **呼び出し**: `import segment3d; segment3d.plane_segmentation(points, thresh: 'float', min_inliers: 'int', max_planes: 'int' = 5, iters: 'int' = 300, seed: 'int' = 0) -> 'np.ndarray'` (または `ops3d.get("plane_segmentation")`)

## 使い方

反復 RANSAC で最大 max_planes 枚の平面を逐次抽出(残差点 -1)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [object_segmentation](../../../../examples_3d/object_segmentation.py) — `py -3.11 examples_3d/object_segmentation.py`

## 型が繋がる次の op(`labels` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [vol_region_props](../regionprops/vol_region_props.md)

## 同カテゴリ(`segment`)

[region_growing](region_growing.md) · [euclidean_cluster](euclidean_cluster.md) · [vol_watershed](vol_watershed.md)

---
*Provenance: segment3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
