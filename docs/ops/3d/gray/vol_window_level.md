---
op: vol_window_level
dim: 3d
category: gray
in: voxel
out: voxel
examples: [gray_window_level]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_window_level — 3D `gray` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import volgray; volgray.vol_window_level(vol, center, width, out_range=(0.0, 1.0))` (または `ops3d.get("vol_window_level")`)

## 使い方

CT window/level (HU windowing) — the radiologist's daily linear remap.

Maps the intensity window ``[center - width/2, center + width/2]`` linearly
onto *out_range* ``(lo, hi)``; voxels below the window saturate at ``lo``,
voxels above at ``hi`` (clipped, by design — that is what a CT window
*does*). A bone window and a soft-tissue window on the same Hounsfield
volume make entirely different structures visible. HALCON analogue:
``scale_image`` (the linear part), plus the clip.

Parameters
----------
vol : array_like, shape (D, H, W)
    Input volume (coerced to float64; NaN/Inf rejected). Hounsfield units
    or any other physical scale — *center* / *width* live on the same scale.
center, width : float
    Window centre and full width. ``width`` must be ``> 0`` (fail-closed).
out_range : (float, float)
    Output ``(lo, hi)`` with ``lo < hi``. Default ``(0.0, 1.0)``.

Returns
-------
ndarray, shape (D, H, W), float64
    The windowed volume, everywhere inside ``[lo, hi]``.

Raises
------
ValueError
    Non-3-D / non-finite input, ``width <= 0``, or a malformed *out_range*.

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
