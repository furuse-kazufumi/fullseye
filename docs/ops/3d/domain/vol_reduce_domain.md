---
op: vol_reduce_domain
dim: 3d
category: domain
in: voxel × voxel
out: voxel
examples: [roi_domain_boundary]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# vol_reduce_domain — 3D `domain` op

- **データ種**: `voxel × voxel` → `voxel`
- **呼び出し**: `import volops; volops.vol_reduce_domain(vol, domain)` (または `ops3d.get("vol_reduce_domain")`)

## 使い方

Restrict a volume to a *domain* mask (HALCON ``reduce_domain``, voxel-wise).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [roi_domain_boundary](../../../../examples_3d/roi_domain_boundary.py) — `py -3.11 examples_3d/roi_domain_boundary.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`domain`)

[vol_bounding_box](vol_bounding_box.md) · [vol_crop_domain](vol_crop_domain.md) · [vol_uncrop](vol_uncrop.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
