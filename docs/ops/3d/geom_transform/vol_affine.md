---
op: vol_affine
dim: 3d
category: geom_transform
in: voxel
out: voxel
examples: [vol_geometry_transform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_affine — 3D `geom_transform` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_affine(vol, matrix, offset=(0, 0, 0), order=1, output_shape=None, mode='constant', cval=0.0)` (実装を直接呼ぶなら `import volxform; volxform.vol_affine(vol, matrix, offset=(0, 0, 0), order=1, output_shape=None, mode='constant', cval=0.0)`、台帳から引くなら `ops3d.get("vol_affine")`)

## 使い方

General affine resampling (``scipy.ndimage.affine_transform``).

**Convention (pinned — read this before writing a matrix)**: this is
scipy's **pull** (output -> input) resampler. For every output voxel at
integer coordinate ``o = (z, y, x)`` the result is the input interpolated
at ``matrix @ o + offset``::

    out[o] = vol[ matrix @ o + offset ]        # (z, y, x) order, voxels

Consequences: ``matrix = 2*I`` makes the object appear **half** size (each
output step strides two input voxels); ``offset = (1, 2, 3)`` moves the
object by ``(-1, -2, -3)``. To *push* content through a forward transform
``T`` (the pose from a registration), pass the **inverse** of ``T``. The
test suite machine-pins this direction.

*matrix* is either a ``(3, 3)`` linear part (with *offset* a separate
length-3 translation) or a ``(4, 4)`` homogeneous matrix
``[[A, t], [0, 0, 0, 1]]`` — then ``A`` / ``t`` are taken from the matrix,
the bottom row must be exactly ``(0, 0, 0, 1)``, and *offset* must stay at
its zero default (a second translation would be ambiguous). Any other
shape raises ``ValueError``.

*output_shape* defaults to the input shape; an explicit one is cap-checked
against ``MAX_VOXELS`` before allocation. *order* is the spline degree
(exact integer 0..5). Voxels whose source coordinate falls outside the
input are filled per *mode*/*cval*.

Returns a float64 volume of *output_shape*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [vol_geometry_transform](../../../../examples_3d/vol_geometry_transform.py) — `py -3.11 examples_3d/vol_geometry_transform.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`geom_transform`)

[vol_resize](vol_resize.md) · [vol_rotate](vol_rotate.md)

---
*Provenance: volxform.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
