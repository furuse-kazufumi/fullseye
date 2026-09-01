---
op: metal_trace_interpolate
dim: tomography
category: artifact
in: sinogram
out: sinogram
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# metal_trace_interpolate — TOMOGRAPHY `artifact` op

- **データ種**: `sinogram` → `sinogram`
- **呼び出し**: `import tomography; tomography.metal_trace_interpolate(sinogram, angles_deg=None, image_threshold=None, mask=None, size=None)` (または `opstomography.get("metal_trace_interpolate")`)

## 使い方

Linear-interpolation metal artefact reduction (LI-MAR).

A metal implant attenuates so strongly that its detector bins carry almost no
photons; the measured line integrals there are dominated by scatter and by the
noise floor of the logarithm, and back-projecting them lays down the dark
bands and bright streaks between dense objects that make a slice unreadable.

The oldest working answer, and still the baseline every newer method is
compared against: declare the affected bins *missing* and fill them by linear
interpolation along the detector axis, per angle. The result is not the truth
— it is a smooth guess with the streaks removed — and it blurs whatever was
genuinely behind the metal.

**How the affected bins are found matters more than the interpolation, and
the obvious way is measurably worse than doing nothing.** The metal trace is
located the way LI-MAR actually does it: reconstruct once with
:func:`filtered_backprojection`, threshold the *image* at
``mean + 3*std``, forward-project that binary mask, and treat the bins it
touches as missing. Thresholding the **sinogram** directly is the shortcut
that suggests itself, and on the Shepp-Logan phantom with a 6-px implant it
goes wrong in the direction that is hardest to notice — it flags the densest
*legitimate* structure (the skull, seen edge-on) and interpolates it away:

    implant density   uncorrected   sinogram threshold   image threshold
         x8             0.0487           0.0626              0.0255
        x30             0.1583           0.2249              0.0255
       x100             0.5214           0.7127              0.0257

(normalised RMS error against the metal-free truth, outside the implant
footprint; the metal-free reconstruction itself scores 0.0250.) The image
route recovers essentially all of the damage at every density. The sinogram
route makes it 1.3-1.4x *worse* than not correcting at all, at every density,
while still producing a picture with fewer visible streaks — which is why the
shortcut is not offered as an option here rather than merely discouraged.

Inside the implant footprint the reconstruction is now wrong on purpose: the
metal is gone. Clinical practice puts it back from the thresholded
reconstruction afterwards; that step is not implemented.

:param sinogram: ``(n_angles, n_detectors)``.
:param angles_deg: view angles; ``None`` -> uniform ``[0, 180)``. Used for the
    internal reconstruction and re-projection, so a wrong angle set here
    misplaces the trace.
:param image_threshold: image-domain metal threshold; ``None`` ->
    ``mean + 3*std`` of the internal reconstruction.
:param mask: explicit boolean ``(n_angles, n_detectors)`` metal trace. When
    given, no reconstruction is done and *image_threshold* is ignored — this
    is the route to use when the trace comes from a segmentation you trust.
:param size: side of the internal reconstruction; ``None`` -> the inscribed
    square.
:returns: ``(n_angles, n_detectors)`` float64 sinogram.
:raises ValueError: if the mask shape disagrees with the sinogram, if the mask
    is not boolean, if nothing is left to interpolate from, or if any *row* is
    entirely masked.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`sinogram` を入力に取れる)

[backproject_sinogram](../reconstruct/backproject_sinogram.md) · [filtered_backprojection](../reconstruct/filtered_backprojection.md) · [sart_reconstruct](../reconstruct/sart_reconstruct.md) · [beam_hardening_apply](beam_hardening_apply.md) · [beam_hardening_correct](beam_hardening_correct.md) · [ring_artifact_apply](ring_artifact_apply.md) · [ring_artifact_remove](ring_artifact_remove.md) · [sinogram_center_of_rotation](../geometry/sinogram_center_of_rotation.md)

## 同カテゴリ(`artifact`)

[beam_hardening_apply](beam_hardening_apply.md) · [beam_hardening_correct](beam_hardening_correct.md) · [ring_artifact_apply](ring_artifact_apply.md) · [ring_artifact_remove](ring_artifact_remove.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
