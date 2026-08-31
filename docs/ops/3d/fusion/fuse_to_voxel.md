---
op: fuse_to_voxel
dim: 3d
category: fusion
in: any
out: voxel
gpu: true
examples: [transforms_repr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# fuse_to_voxel — 3D `fusion` op

- **データ種**: `any` → `voxel`
- **呼び出し**: `import fuse3d; fuse3d.fuse_to_voxel(items, size=64, bounds=None, device='cpu', smooth=0.8)` (または `ops3d.get("fuse_to_voxel")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

複数構造を共通密度 voxel へ融合(TRIZ 統合)。items=[(data,kind,params_dict), ...]。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`fusion`)

[register_cross](register_cross.md)

---
*Provenance: fuse3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
