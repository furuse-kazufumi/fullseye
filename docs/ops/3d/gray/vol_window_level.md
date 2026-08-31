---
op: vol_window_level
dim: 3d
category: gray
in: voxel
out: voxel
examples: [gray_window_level]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# vol_window_level — 3D `gray` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import volgray; volgray.vol_window_level(vol, center, width, out_range=(0.0, 1.0))` (または `ops3d.get("vol_window_level")`)

## 使い方

CT window/level (HU windowing) — the radiologist's daily linear remap.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gray_window_level](../../../../examples_3d/gray_window_level.py) — `py -3.11 examples_3d/gray_window_level.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`gray`)

[vol_equalize](vol_equalize.md) · [vol_gamma](vol_gamma.md) · [vol_stretch](vol_stretch.md)

---
*Provenance: volgray.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
