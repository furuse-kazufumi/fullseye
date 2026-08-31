---
op: plane_sweep_depth
dim: 3d
category: plane_sweep_stereo
in: image2d × image2d
out: depth
examples: [plane_sweep_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# plane_sweep_depth — 3D `plane_sweep_stereo` op

- **データ種**: `image2d × image2d` → `depth`
- **呼び出し**: `import plane_sweep; plane_sweep.plane_sweep_depth(img_ref: 'np.ndarray', img_src: 'np.ndarray', K: 'np.ndarray', R: 'np.ndarray', t: 'np.ndarray', depth_candidates, window: 'int' = 1, normal=(0.0, 0.0, 1.0)) -> 'np.ndarray'` (または `ops3d.get("plane_sweep_depth")`)

## 使い方

plane-sweep stereo で密な深度マップを推定。→ (H,W) depth。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [plane_sweep_depth](../../../../examples_3d/plane_sweep_depth.py) — `py -3.11 examples_3d/plane_sweep_depth.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[depth_to_points](../transform/depth_to_points.md) · [tsdf_from_depth](../transform/tsdf_from_depth.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [depth_to_organized_points](../range_image/depth_to_organized_points.md) · [normals_from_depth](../range_image/normals_from_depth.md) · [occlusion_edges](../range_image/occlusion_edges.md) · [bearing_angle_image](../range_image/bearing_angle_image.md)

## 同カテゴリ(`plane_sweep_stereo`)

[warp_by_plane](warp_by_plane.md)

---
*Provenance: plane_sweep.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
