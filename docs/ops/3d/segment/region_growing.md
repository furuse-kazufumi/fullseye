---
op: region_growing
dim: 3d
category: segment
in: points
out: labels
examples: [sensor_seg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# region_growing — 3D `segment` op

- **データ種**: `points` → `labels`
- **呼び出し**: `import segment3d; segment3d.region_growing(points, normals=None, angle_thresh_deg: 'float' = 15.0, k: 'int' = 20, min_region_size: 'int' = 3) -> 'np.ndarray'` (または `ops3d.get("region_growing")`)

## 使い方

法線類似で領域成長し連結した平滑領域へ同ラベルを付す(曲率ゲート無し変種)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sensor_seg](../../../../examples_3d/sensor_seg.py) — `py -3.11 examples_3d/sensor_seg.py`

## 型が繋がる次の op(`labels` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [vol_region_props](../regionprops/vol_region_props.md)

## 同カテゴリ(`segment`)

[euclidean_cluster](euclidean_cluster.md) · [plane_segmentation](plane_segmentation.md) · [vol_watershed](vol_watershed.md)

---
*Provenance: segment3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
