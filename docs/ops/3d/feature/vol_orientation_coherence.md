---
op: vol_orientation_coherence
dim: 3d
category: feature
in: voxel
out: voxel
examples: [ct_porosity_and_fibre_morphometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# vol_orientation_coherence — 3D `feature` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_orientation_coherence(vol, sigma=1.0, rho=3.0)` (実装を直接呼ぶなら `import volops; volops.vol_orientation_coherence(vol, sigma=1.0, rho=3.0)`、台帳から引くなら `ops3d.get("vol_orientation_coherence")`)

## 使い方

How strongly the local structure points **one way** (3-D structure tensor).

Builds ``J = G_rho * (grad I)(grad I)^T`` and returns

    (l1 - l3) / (l1 + l2 + l3),   l1 >= l2 >= l3

in ``[0, 1]``: ``1`` where one direction dominates (a fibre, a lamella edge,
a crack face), ``0`` where the gradient is isotropic (a uniform block, white
noise) or where two directions are equally strong.  *sigma* smooths before
differentiating (so noise is not differentiated into structure); *rho* is the
integration width — make it larger than the spacing of the structure you are
measuring.

**HALCON computes this tensor and throws it away**: ``coherence_enhancing_diff``
uses it to steer a diffusion but exposes neither the orientation nor the
coherence.  Returning the measurement is the point of this operator.

**Applicability.** (1) ``rho`` too small collapses the tensor to rank 1 and
the answer sticks at 1 everywhere — that is *not* perfect alignment, it is a
failure to measure.  (2) Two fibre families crossing at equal strength read
as 0, indistinguishable from a uniform block; pair it with ``vol_local_std``
to tell "no direction" from "no structure".  (3) Voxels whose tensor trace is
below ``1e-6`` of the volume maximum return 0.

Returns a ``(D, H, W)`` float64 volume in ``[0, 1]``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_porosity_and_fibre_morphometry](../../../../examples_3d/ct_porosity_and_fibre_morphometry.py) — `py -3.11 examples_3d/ct_porosity_and_fibre_morphometry.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md) · [vol_frangi](vol_frangi.md) · [vol_local_std](vol_local_std.md) · [vol_local_thickness](vol_local_thickness.md) · [vol_euler_number](vol_euler_number.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
