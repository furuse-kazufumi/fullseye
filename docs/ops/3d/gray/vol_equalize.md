---
op: vol_equalize
dim: 3d
category: gray
in: voxel
out: voxel
examples: [gray_window_level]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_equalize — 3D `gray` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_equalize(vol, nbins=256, mask=None)` (実装を直接呼ぶなら `import volgray; volgray.vol_equalize(vol, nbins=256, mask=None)`、台帳から引くなら `ops3d.get("vol_equalize")`)

## 使い方

Histogram equalisation of a volume (HALCON ``equ_histo_image``).

Builds an *nbins*-bin histogram over the volume's ``[min, max]`` range,
takes its cumulative distribution as a monotone LUT, and maps every voxel
through it — the output lives in ``(0, 1]`` and its histogram is
(approximately) flat. With *mask* (thresholded at ``> 0.5``, the volops
convention) the **histogram is computed from the masked voxels only while
the LUT is applied to the whole volume** — exactly the HALCON
``reduce_domain`` + ``equ_histo_image`` domain behaviour, and the right
tool when a dominant background (e.g. air around a CT subject) would
otherwise swallow the whole dynamic range.

A **constant volume is returned unchanged** — normalising a flat volume
would amplify floating-point dust into full-scale garbage (fail-honest,
not fail-loud; see the module docstring).

Parameters
----------
vol : array_like, shape (D, H, W)
    Input volume (coerced to float64; NaN/Inf rejected).
nbins : int
    Histogram bins, ``>= 2``. More bins = finer LUT (the mapping is
    piecewise-constant per bin — an approximation, documented above).
mask : array_like, shape (D, H, W), optional
    Histogram domain. Must match *vol*'s shape and select at least one
    voxel (an empty domain has no histogram — fail-closed).

Returns
-------
ndarray, shape (D, H, W), float64
    The equalised volume in ``[0, 1]`` (constant input: the input itself).

Raises
------
ValueError
    Non-3-D / non-finite input, ``nbins < 2``, a mask shape mismatch, or
    an empty mask.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gray_window_level](../../../../examples_3d/gray_window_level.py) — `py -3.11 examples_3d/gray_window_level.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`gray`)

[vol_window_level](vol_window_level.md) · [vol_gamma](vol_gamma.md) · [vol_stretch](vol_stretch.md)

---
*Provenance: volgray.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
