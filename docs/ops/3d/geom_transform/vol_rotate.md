---
op: vol_rotate
dim: 3d
category: geom_transform
in: voxel
out: voxel
examples: [vol_geometry_transform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_rotate — 3D `geom_transform` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import volxform; volxform.vol_rotate(vol, angle_deg, axes=(1, 2), order=1, reshape=False, mode='constant', cval=0.0)` (または `ops3d.get("vol_rotate")`)

## 使い方

Rotate a volume in the plane of an axis pair (``scipy.ndimage.rotate``).

*axes* names the rotation plane and must be exactly one of ``(0, 1)``
(z-y plane, turning about the x-axis), ``(0, 2)`` (z-x, about y) or
``(1, 2)`` (y-x, about z — the axial-slice rotation; the default). Any
other pair — including a reversed one like ``(2, 1)`` — raises
``ValueError``, so the direction convention below is never silently
flipped.

**Direction (pinned)**: a positive *angle_deg* rotates **from the first
axis of** *axes* **toward the second** — the same convention as
``np.rot90``. Concretely, ``vol_rotate(v, 90, axes=a, reshape=False,
order=0)`` equals ``np.rot90(v, 1, axes=a)`` bit-for-bit when the in-plane
shape is square (the test pins this).

``reshape=False`` (default) keeps the input shape (in-plane corners that
leave the frame are lost, entering ones are filled with *cval* per *mode*);
``reshape=True`` grows the in-plane shape to contain the whole rotated
frame — the grown output is cap-checked against ``MAX_VOXELS`` *before*
the call. *order* is the spline degree (exact integer 0..5; >1 overshoots
— module notes).

Returns a ``(D, H, W)`` float64 volume (same shape unless *reshape*).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [vol_geometry_transform](../../../../examples_3d/vol_geometry_transform.py) — `py -3.11 examples_3d/vol_geometry_transform.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`geom_transform`)

[vol_resize](vol_resize.md) · [vol_affine](vol_affine.md)

---
*Provenance: volxform.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
