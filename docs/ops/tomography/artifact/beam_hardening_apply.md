---
op: beam_hardening_apply
dim: tomography
category: artifact
in: sinogram
out: sinogram
examples: [ct_reconstruction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# beam_hardening_apply — TOMOGRAPHY `artifact` op

- **データ種**: `sinogram` → `sinogram`
- **呼び出し**: `import tomography; tomography.beam_hardening_apply(sinogram, high_energy_fraction=0.5, attenuation_ratio=0.4)` (または `opstomography.get("beam_hardening_apply")`)

## 使い方

Turn a monochromatic sinogram into a **polychromatic** one — cupping.

A real X-ray tube emits a spectrum, and low-energy photons are absorbed more,
so the beam that survives a thick path is *harder* (higher mean energy) and
therefore attenuated less per unit length than the beam that survives a thin
one. The line integral stops being linear in path length, and the
reconstruction of a uniform object comes back with a depressed centre: the
cupping artefact.

The two-spectrum model used here is the smallest one that is physics and not a
curve::

    I/I0    = (1-w) exp(-p) + w exp(-k p)
    p_meas  = -ln(I/I0)

with *w* the fraction of the beam at the high energy and *k < 1* its relative
attenuation. It is exact at ``p = 0``, concave everywhere, and monotone — so
it is invertible, which is what :func:`beam_hardening_correct` inverts.

Measured on a uniform disc (radius 60 px in 256 px, density 1/60 so the peak
line integral is 2.0) at ``w = 0.5, k = 0.4``: the FBP reconstruction's
centre-to-rim ratio drops to **0.9312**, against **0.9981** before hardening,
and :func:`beam_hardening_correct` returns it to **0.9981** — the clean value
in all four digits. (The clean ratio is 0.9981 rather than exactly 1 because
of the detector sampling discussed in :func:`filtered_backprojection`. The
cupping is the 6.7-point drop, not the 0.2-point one.)

:param sinogram: ``(n_angles, n_detectors)`` monochromatic line integrals,
    which must be ``>= 0``.
:param high_energy_fraction: *w*, in ``[0, 1)``. 0 is a monochromatic beam and
    the operator is then the identity.
:param attenuation_ratio: *k*, in ``(0, 1)``. 1 is again monochromatic.
:returns: ``(n_angles, n_detectors)`` float64 hardened sinogram.
:raises ValueError: on a negative sinogram (a negative line integral is not a
    measurement this model can harden — the logarithm of the transmitted
    intensity has already gone wrong upstream), or parameters outside range.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_reconstruction](../../../../examples/ct_reconstruction.py) — `py -3.11 examples/ct_reconstruction.py`

## 型が繋がる次の op(`sinogram` を入力に取れる)

[backproject_sinogram](../reconstruct/backproject_sinogram.md) · [filtered_backprojection](../reconstruct/filtered_backprojection.md) · [sart_reconstruct](../reconstruct/sart_reconstruct.md) · [beam_hardening_correct](beam_hardening_correct.md) · [ring_artifact_apply](ring_artifact_apply.md) · [ring_artifact_remove](ring_artifact_remove.md) · [metal_trace_interpolate](metal_trace_interpolate.md) · [sinogram_center_of_rotation](../geometry/sinogram_center_of_rotation.md)

## 同カテゴリ(`artifact`)

[beam_hardening_correct](beam_hardening_correct.md) · [ring_artifact_apply](ring_artifact_apply.md) · [ring_artifact_remove](ring_artifact_remove.md) · [metal_trace_interpolate](metal_trace_interpolate.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
