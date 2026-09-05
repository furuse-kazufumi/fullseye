---
op: beam_hardening_correct
dim: tomography
category: artifact
in: sinogram
out: sinogram
examples: [ct_reconstruction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# beam_hardening_correct — TOMOGRAPHY `artifact` op

- **データ種**: `sinogram` → `sinogram`
- **呼び出し**: `import tomography; tomography.beam_hardening_correct(sinogram, high_energy_fraction=0.5, attenuation_ratio=0.4, poly_coeffs=None, n_table=4096)` (または `opstomography.get("beam_hardening_correct")`)

## 使い方

Undo cupping — either the exact model inverse, or a calibrated polynomial.

Two routes, and the difference between them is what you are allowed to claim:

* **Model inverse** (default). :func:`beam_hardening_apply` is a monotone
  scalar function of the line integral, so it has an exact inverse; this
  builds it by interpolating the forward curve on *n_table* nodes. Round-trip
  error on the disc phantom: **1.6e-08** absolute and **8.0e-09** relative to
  the peak line integral — the table resolution and nothing else.
  This is a *simulation* tool — it needs the same ``w`` and ``k`` the
  hardening used, which on real data nobody has.
* **Polynomial** (*poly_coeffs*). ``p_corr = c1 p + c2 p^2 + ...``, the
  water-correction of every clinical scanner, whose coefficients come from
  scanning a uniform water phantom and fitting for a flat reconstruction.
  This is what applies to real data, and it is only as good as the assumption
  that everything in the field of view attenuates like water.

The honest limitation is the same one every scanner has: the correction is
**material-specific**. A water calibration applied to a slice containing bone
or metal over-corrects the dense material and leaves dark bands between dense
objects, and nothing in the sinogram says which case you are in.

:param sinogram: ``(n_angles, n_detectors)`` hardened line integrals.
:param high_energy_fraction: *w* used by the forward model.
:param attenuation_ratio: *k* used by the forward model.
:param poly_coeffs: ``(c1, c2, ...)``; when given, the polynomial route is
    used and *w* / *k* are ignored.
:param n_table: nodes of the inverse table, ``64 .. 1048576``.
:returns: ``(n_angles, n_detectors)`` float64 corrected sinogram.
:raises ValueError: as :func:`beam_hardening_apply`, plus an empty or
    non-finite *poly_coeffs*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_reconstruction](../../../../examples/ct_reconstruction.py) — `py -3.11 examples/ct_reconstruction.py`

## 型が繋がる次の op(`sinogram` を入力に取れる)

[backproject_sinogram](../reconstruct/backproject_sinogram.md) · [filtered_backprojection](../reconstruct/filtered_backprojection.md) · [sart_reconstruct](../reconstruct/sart_reconstruct.md) · [beam_hardening_apply](beam_hardening_apply.md) · [ring_artifact_apply](ring_artifact_apply.md) · [ring_artifact_remove](ring_artifact_remove.md) · [metal_trace_interpolate](metal_trace_interpolate.md) · [sinogram_center_of_rotation](../geometry/sinogram_center_of_rotation.md)

## 同カテゴリ(`artifact`)

[beam_hardening_apply](beam_hardening_apply.md) · [ring_artifact_apply](ring_artifact_apply.md) · [ring_artifact_remove](ring_artifact_remove.md) · [metal_trace_interpolate](metal_trace_interpolate.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
