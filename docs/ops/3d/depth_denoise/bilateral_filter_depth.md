---
op: bilateral_filter_depth
dim: 3d
category: depth_denoise
in: depth
out: depth
examples: [depth_denoise]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# bilateral_filter_depth — 3D `depth_denoise` op

- **データ種**: `depth` → `depth`
- **呼び出し**: `import depth_bilateral; depth_bilateral.bilateral_filter_depth(depth: 'np.ndarray', spatial_sigma: 'float', range_sigma: 'float', *, invalid: 'float | None' = 0.0, truncate: 'float' = 3.0) -> 'np.ndarray'` (または `ops3d.get("bilateral_filter_depth")`)

## 使い方

深度画像の bilateral filter(段差保存デノイズ)。→ float64 (H,W)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [depth_denoise](../../../../examples_3d/depth_denoise.py) — `py -3.11 examples_3d/depth_denoise.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[depth_to_points](../transform/depth_to_points.md) · [tsdf_from_depth](../transform/tsdf_from_depth.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [depth_to_organized_points](../range_image/depth_to_organized_points.md) · [normals_from_depth](../range_image/normals_from_depth.md) · [occlusion_edges](../range_image/occlusion_edges.md) · [bearing_angle_image](../range_image/bearing_angle_image.md)

## 同カテゴリ(`depth_denoise`)

[joint_bilateral](joint_bilateral.md) · [fill_holes](fill_holes.md)

---
*Provenance: depth_bilateral.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
