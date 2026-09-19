---
op: vol_local_std
dim: 3d
category: feature
in: voxel
out: voxel
examples: [ct_porosity_and_fibre_morphometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# vol_local_std — 3D `feature` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_local_std(vol, size=5)` (実装を直接呼ぶなら `import volops; volops.vol_local_std(vol, size=5)`、台帳から引くなら `ops3d.get("vol_local_std")`)

## 使い方

Unbiased local standard deviation inside a cubic window.

The 3-D counterpart of the registry op ``local_std`` (HALCON's
``deviation_image``).  The variance is taken **after subtracting the global
mean** — ``E[x^2] - E[x]^2`` loses every significant digit on a volume whose
values sit far from zero, and the leftover shows up as a fake texture on a
uniform block.  It is then unbiased twice: ``n/(n-1)`` on the variance and
``c4(n)`` on the square root, so the estimate of ``sigma`` itself (not of
``sigma^2``) is unbiased.

*size* is the edge of the cubic window in voxels (odd, >= 3), so
``n = size**3`` voxels enter each estimate.  **The relative standard error of
a single voxel's estimate is ``1/sqrt(2(n-1))``** — 3.1% for a 5x5x5 window,
1.1% for 9x9x9.  Quote that figure whenever a noise or roughness number is
read off this volume.

Returns a ``(D, H, W)`` float64 volume in the input's own units (it is *not*
normalised, so values from different scans compare directly).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_porosity_and_fibre_morphometry](../../../../examples_3d/ct_porosity_and_fibre_morphometry.py) — `py -3.11 examples_3d/ct_porosity_and_fibre_morphometry.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md) · [vol_frangi](vol_frangi.md) · [vol_local_thickness](vol_local_thickness.md) · [vol_orientation_coherence](vol_orientation_coherence.md) · [vol_euler_number](vol_euler_number.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
