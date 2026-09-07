---
op: plane_segmentation
dim: 3d
category: segment
in: points
out: labels
examples: [object_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# plane_segmentation — 3D `segment` op

- **データ種**: `points` → `labels`
- **呼び出し**: `import fullseye as fs; fs.ledger.plane_segmentation(points, thresh: 'float', min_inliers: 'int', max_planes: 'int' = 5, iters: 'int' = 300, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import segment3d; segment3d.plane_segmentation(points, thresh: 'float', min_inliers: 'int', max_planes: 'int' = 5, iters: 'int' = 300, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("plane_segmentation")`)

## 使い方

反復 RANSAC で最大 max_planes 枚の平面を逐次抽出(残差点 -1)。

残り点集合に :func:`ransac_fit.ransac_plane` を掛け、その最大 consensus 平面の
inlier 数が ``min_inliers`` 以上なら新ラベルを与えて除去 → 残りで再検出、を繰り返す。
複数の床/壁/階段状の面を一度に分離する(単一平面適合の pcseg との差)。inlier が
``min_inliers`` に満たなくなった時点で停止し、以降の点は残差 -1(球や複雑物体はここに残る)。

Args:
    points: (N,3) 点群。
    thresh: 点-平面距離の inlier しきい値(距離、要 > 0)。
    min_inliers: 平面として採用する最小 inlier 数(要 >= 3)。
    max_planes: 抽出する平面の最大枚数(要 >= 1)。
    iters: 各 RANSAC 反復数。
    seed: 乱数シード(決定論。各平面で seed+平面index を使う)。

Returns:
    labels: (N,) int。検出順(=consensus 大きい順に近い)に 0,1,2,... を平面へ付与、
    どの平面にも属さない残差点は -1。空入力は shape (0,)。

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
