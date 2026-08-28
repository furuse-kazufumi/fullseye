---
op: euclidean_cluster
dim: 3d
category: segment
in: points
out: labels
examples: [object_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# euclidean_cluster — 3D `segment` op

- **データ種**: `points` → `labels`
- **呼び出し**: `import segment3d; segment3d.euclidean_cluster(points, tol: 'float', min_size: 'int' = 10) -> 'np.ndarray'` (または `ops3d.get("euclidean_cluster")`)

## 使い方

半径 tol の近接グラフの連結成分で距離クラスタリング(-1=ノイズ)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [object_segmentation](../../../../examples_3d/object_segmentation.py) — `py -3.11 examples_3d/object_segmentation.py`

## 型が繋がる次の op(`labels` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`segment`)

[region_growing](region_growing.md) · [plane_segmentation](plane_segmentation.md) · [vol_watershed](vol_watershed.md)

---
*Provenance: segment3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
