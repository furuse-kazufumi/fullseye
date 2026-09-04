---
op: radon_transform
dim: tomography
category: forward
in: image2d
out: sinogram
examples: [ct_reconstruction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# radon_transform — TOMOGRAPHY `forward` op

- **データ種**: `image2d` → `sinogram`
- **呼び出し**: `import tomography; tomography.radon_transform(image, angles_deg=None, n_detectors=None, oversample=1)` (または `opstomography.get("radon_transform")`)

## 使い方

Forward parallel-beam projection: a slice in, a **sinogram** out.

Rows of the result are projection angles and columns are detector bins. The
convention is fixed here and never negotiated again; every other operator in
this module reads it the same way, and a transposed sinogram is structurally
indistinguishable from a valid one (see :mod:`opstomography` for the measured
consequences of not giving it its own sort).

The ray at detector bin ``j`` and angle ``theta`` is the line
``x cos(theta) + y sin(theta) = j - (n_det-1)/2``, with ``x`` the column
offset from the image centre and ``y`` the row offset — so ``+y`` runs *down*
the array, matching the rest of Fullseye's image indexing rather than a
textbook's upward ``y``. The transform is the same either way (the sinogram is
mirrored in the angle axis), but only one of the two agrees with
:func:`ellipse_phantom`, and the tests hold them together.

Accuracy against the closed form (a disc of radius 60 px in a 256-px grid,
180 views), measured in ``tests/test_tomography.py``: interior RMS error
**0.073 %** of the peak line integral, whole-sinogram RMS **0.402 %** — the
difference between the two being the partial-volume edge, where the phantom's
own anti-aliased boundary is what is being sampled.

:param image: 2-D slice, at least 2x2.
:param angles_deg: 1-D view angles in degrees; ``None`` ->
    ``linspace(0, 180, 180, endpoint=False)``.
:param n_detectors: bins; ``None`` -> odd count covering the diagonal.
:param oversample: ray samples per pixel, ``1 .. 8``. The default is 1
    because 4 measures no better (0.073 % against 0.070 %).
:returns: ``(n_angles, n_detectors)`` float64 sinogram.
:raises ValueError: on non-finite input, an empty angle list, a detector count
    under 4, or a sinogram over :data:`MAX_SINOGRAM_ELEMENTS`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_reconstruction](../../../../examples/ct_reconstruction.py) — `py -3.11 examples/ct_reconstruction.py`

## 型が繋がる次の op(`sinogram` を入力に取れる)

[backproject_sinogram](../reconstruct/backproject_sinogram.md) · [filtered_backprojection](../reconstruct/filtered_backprojection.md) · [sart_reconstruct](../reconstruct/sart_reconstruct.md) · [beam_hardening_apply](../artifact/beam_hardening_apply.md) · [beam_hardening_correct](../artifact/beam_hardening_correct.md) · [ring_artifact_apply](../artifact/ring_artifact_apply.md) · [ring_artifact_remove](../artifact/ring_artifact_remove.md) · [metal_trace_interpolate](../artifact/metal_trace_interpolate.md)

## 同カテゴリ(`forward`)

[ellipse_phantom](ellipse_phantom.md) · [ellipse_sinogram](ellipse_sinogram.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
