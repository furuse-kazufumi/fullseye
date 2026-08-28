---
op: decode_fringe
dim: 3d
category: structured_light
in: images
out: depth
examples: [structured_light]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# decode_fringe — 3D `structured_light` op

- **データ種**: `images` → `depth`
- **呼び出し**: `import fringe; fringe.decode_fringe(phase_shift_images, ref_phase=None, k=1.0, mask=None, min_modulation=None) -> 'np.ndarray'` (または `ops3d.get("decode_fringe")`)

## 使い方

位相シフト画像列を一括復号: wrapped → unwrap →(参照減算で)高さ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [structured_light](../../../../examples_3d/structured_light.py) — `py -3.11 examples_3d/structured_light.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[depth_to_points](../transform/depth_to_points.md) · [tsdf_from_depth](../transform/tsdf_from_depth.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [depth_to_organized_points](../range_image/depth_to_organized_points.md) · [normals_from_depth](../range_image/normals_from_depth.md) · [occlusion_edges](../range_image/occlusion_edges.md) · [bearing_angle_image](../range_image/bearing_angle_image.md)

## 同カテゴリ(`structured_light`)

[wrapped_phase](wrapped_phase.md) · [unwrap_phase_2d](unwrap_phase_2d.md) · [graycode_decode](graycode_decode.md) · [synthesize_fringes](synthesize_fringes.md)

---
*Provenance: fringe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
