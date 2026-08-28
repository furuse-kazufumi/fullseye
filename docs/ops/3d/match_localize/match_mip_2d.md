---
op: match_mip_2d
dim: 3d
category: match_localize
in: voxel × voxel
out: position
gpu: true
examples: [matching_localize]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# match_mip_2d — 3D `match_localize` op

- **データ種**: `voxel × voxel` → `position`
- **呼び出し**: `import match3d; match3d.match_mip_2d(scene_vol, model_vol, device='cpu')` (または `ops3d.get("match_mip_2d")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

MIP 投影 → 2D NCC(構造=voxel → 2D × 手法=NCC、変換=直交 MIP)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [matching_localize](../../../../examples_3d/matching_localize.py) — `py -3.11 examples_3d/matching_localize.py`

## 型が繋がる次の op(`position` を入力に取れる)

[refine_peak_newton](../refine/refine_peak_newton.md) · [refine_translation_lk](../refine/refine_translation_lk.md) · [refine_lm](../refine/refine_lm.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`match_localize`)

[match_shape_3d](match_shape_3d.md) · [match_chamfer_3d](match_chamfer_3d.md) · [match_curvature_3d](match_curvature_3d.md) · [match_hough_3d](match_hough_3d.md) · [match_points_ncc](match_points_ncc.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
