---
op: morph_erode3d
dim: 3d
category: morphology
in: voxel
out: voxel
gpu: true
examples: [morphology_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# morph_erode3d — 3D `morphology` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import match3d; match3d.morph_erode3d(vol, r=1, device='cpu')` (または `ops3d.get("morph_erode3d")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

3D グレースケール erosion(cube SE の局所 min)。明領域を収縮。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [morphology_3d](../../../../examples_3d/morphology_3d.py) — `py -3.11 examples_3d/morphology_3d.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`morphology`)

[morph_dilate3d](morph_dilate3d.md) · [morph_gradient3d](morph_gradient3d.md) · [morph_tophat3d](morph_tophat3d.md) · [morph_blackhat3d](morph_blackhat3d.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
