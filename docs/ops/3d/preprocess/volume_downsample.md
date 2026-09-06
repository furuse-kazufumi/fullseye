---
op: volume_downsample
dim: 3d
category: preprocess
in: voxel
out: voxel
examples: [volume_downsampling]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# volume_downsample — 3D `preprocess` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import volops; volops.volume_downsample(vol, factor, mode='mean')` (または `ops3d.get("volume_downsample")`)

## 使い方

Block-pool a ``(D, H, W)`` volume by an integer *factor* per axis (data 間引き).

Large CT / laminography / simulation volumes must be thinned before the
heavier 3-D operators (Frangi/Sato are capped at ~256**3 voxels, see
``MAX_EIGEN_VOXELS``). This is the volume analogue of the point-cloud
``voxel_grid_downsample`` and the mesh ``decimate_qem`` — the third leg of
Fullseye's *間引き* (decimation) family, one per 3-D data sort.

Parameters
----------
vol : array_like, shape (D, H, W)
    Input volume (coerced to float64; NaN/Inf rejected).
factor : int or (fz, fy, fx)
    Block size per axis, each ``>= 1``. The output shape is
    ``(D//fz, H//fy, W//fx)``; a trailing partial block that cannot fill a
    full factor is dropped (deterministic, no edge bias).
mode : {'mean', 'max', 'stride'}
    * ``'mean'`` — average-pool. Band-limits before subsampling (the
      anti-aliasing choice); the right default for grey CT / MRI.
    * ``'max'``  — max-pool. Preserves thin bright structures (bone, vessel,
      defect voxels) that averaging would wash out.
    * ``'stride'`` — plain subsample ``vol[::fz, ::fy, ::fx]`` (fastest,
      but aliases — no pre-filter).

Returns
-------
ndarray, shape (D//fz, H//fy, W//fx), float64
    The downsampled volume. Spacing scales by the same factor: an input
    spacing ``(sz, sy, sx)`` mm becomes ``(sz*fz, sy*fy, sx*fx)`` mm.

Raises
------
ValueError
    Non-3-D input, a factor component ``< 1`` or larger than its axis, or an
    unknown *mode* (fail-closed).

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [volume_downsampling](../../../../examples_3d/volume_downsampling.py) — `py -3.11 examples_3d/volume_downsampling.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`preprocess`)

[statistical_outlier_removal](statistical_outlier_removal.md) · [radius_outlier_removal](radius_outlier_removal.md) · [voxel_grid_downsample](voxel_grid_downsample.md) · [mls_smooth](mls_smooth.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
