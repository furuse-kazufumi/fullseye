---
op: vol_tiled_map
dim: 3d
category: domain
in: voxel
out: voxel
examples: [rle_region_efficiency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_tiled_map — 3D `domain` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_tiled_map(vol, fn, tile=64, overlap=8)` (実装を直接呼ぶなら `import volops; volops.vol_tiled_map(vol, fn, tile=64, overlap=8)`、台帳から引くなら `ops3d.get("vol_tiled_map")`)

## 使い方

Apply a shape-preserving volume operator in overlapping z-slabs, so peak

working memory is bounded by the slab — not the volume.

The third leg of the memory family: :func:`vol_crop_domain` shrinks *where*
you compute, :mod:`volregion` shrinks *what you keep*, and this bounds *how
much lives in RAM at once*. Each slab ``vol[z0-overlap : z1+overlap]`` is
run through *fn* and only the core ``[z0:z1)`` of the result is kept, so a
volume far above an operator's comfortable size streams through in
constant-memory pieces (measured: peak working set of a Gaussian drops with
the slab size while the output stays exact — see the test).

**Correctness contract (the honest part)**: the result equals ``fn(vol)``
exactly only for *local* operators whose spatial footprint along z is at
most *overlap* voxels on each side (a Gaussian of sigma s with scipy's
default truncation needs ``overlap >= round(4 * s)``; a morphology with a
k-voxel structuring element needs ``overlap >= k``). A *global* operator
(Otsu, normalisation, anything that looks at the whole histogram) is
silently WRONG under tiling — this function cannot detect that, so it is
documented instead: do not tile global operators.

Parameters: *fn* is any callable mapping a ``(d, H, W)`` float64 volume to
an array of the same shape (e.g. ``lambda v: vol_gradient_magnitude(v)``).
*tile* is the slab thickness (>= 1), *overlap* the per-side context
(>= 0). A slab result of the wrong shape raises ``ValueError`` immediately
(fail-closed — a shape-changing fn would silently corrupt the assembly).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [rle_region_efficiency](../../../../examples_3d/rle_region_efficiency.py) — `py -3.11 examples_3d/rle_region_efficiency.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`domain`)

[vol_reduce_domain](vol_reduce_domain.md) · [vol_bounding_box](vol_bounding_box.md) · [vol_crop_domain](vol_crop_domain.md) · [vol_uncrop](vol_uncrop.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
