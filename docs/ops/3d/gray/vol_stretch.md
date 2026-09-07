---
op: vol_stretch
dim: 3d
category: gray
in: voxel
out: voxel
examples: [gray_window_level]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_stretch — 3D `gray` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_stretch(vol, p_low=1.0, p_high=99.0)` (実装を直接呼ぶなら `import volgray; volgray.vol_stretch(vol, p_low=1.0, p_high=99.0)`、台帳から引くなら `ops3d.get("vol_stretch")`)

## 使い方

Percentile contrast stretch to ``[0, 1]`` (robust ``scale_image_max``).

Computes the *p_low*-th and *p_high*-th intensity percentiles and maps
``[P(p_low), P(p_high)]`` linearly onto ``[0, 1]``, clipping outside — so a
handful of hot/cold outlier voxels (a metal artefact, a dead detector
element) no longer dictates the display range, unlike a plain min/max
normalisation. The defaults (1 % / 99 %) are the usual display-stretch
choice.

If the two percentile values coincide (a constant — or near-constant —
volume), the input is **returned unchanged** rather than divided by zero
(see the module docstring's flat-volume note).

Parameters
----------
vol : array_like, shape (D, H, W)
    Input volume (coerced to float64; NaN/Inf rejected).
p_low, p_high : float
    Percentiles in ``[0, 100]`` with ``p_low < p_high`` (fail-closed).

Returns
-------
ndarray, shape (D, H, W), float64
    The stretched volume in ``[0, 1]`` (degenerate percentiles: the input
    itself).

Raises
------
ValueError
    Non-3-D / non-finite input, percentiles out of ``[0, 100]``, or
    ``p_low >= p_high``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gray_window_level](../../../../examples_3d/gray_window_level.py) — `py -3.11 examples_3d/gray_window_level.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`gray`)

[vol_window_level](vol_window_level.md) · [vol_equalize](vol_equalize.md) · [vol_gamma](vol_gamma.md)

---
*Provenance: volgray.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
