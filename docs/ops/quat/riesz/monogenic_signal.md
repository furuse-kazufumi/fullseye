---
op: monogenic_signal
dim: quat
category: riesz
in: image2d
out: qimage
examples: [quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# monogenic_signal — QUAT `riesz` op

- **データ種**: `image2d` → `qimage`
- **呼び出し**: `import quatimage; quatimage.monogenic_signal(image, wavelength_px=8.0, bandwidth_octaves=1.0) -> 'np.ndarray'` (または `opsquat.get("monogenic_signal")`)

## 使い方

The monogenic signal of an image at one scale. → (H, W, 4).

Felsberg & Sommer (2001). The image is band-passed by a log-radial raised
cosine centred at ``1/wavelength_px`` cycles/pixel with half-width
*bandwidth_octaves*, and the result is packed with its Riesz pair as the
quaternion ``(band-pass image, R1, R2, 0)``. From that single object
:func:`monogenic_amplitude`, :func:`monogenic_phase` and
:func:`monogenic_orientation` read the local contrast, the local phase and
the local orientation — the 2-D analogue of what ``|z|`` and ``arg z`` give
a 1-D analytic signal, with orientation as the extra degree of freedom that
only exists in 2-D.

The band-pass is applied *before* the Riesz kernels because the Riesz
multiplier has a jump at DC: without a band that excludes DC the "local
phase" of the image mean is undefined, not merely noisy.

Closed form
-----------
A grating exactly at the band centre passes with gain 1, so for
``contrast * cos(2*pi*(u0*x+v0*y) + p)`` the amplitude is ``contrast``
everywhere, the phase is the grating's own phase, and the orientation is
``atan2(v0, u0) mod pi``. Measured on a 64x64 frame with an 8 px grating of
unit contrast and phase 0.7: amplitude mean exactly ``1.0`` with a spread of
``8.9e-16`` across the frame, phase error ``5.3e-15`` rad, orientation error
``0.0`` rad.

**Honest limit.** The phase is well defined only where the amplitude is; in a
flat region the amplitude is at the rounding floor and the phase is the angle
of numerical dust. Nothing here suppresses that — the amplitude map *is* the
confidence map and it is returned in the same object, so a caller can mask on
it. The operators that consume the signal (:func:`riesz_displacement`,
:func:`riesz_motion_magnify`) do mask, with the same relative thresholds
:mod:`motionmag` uses, so their numbers are comparable.

**Raises** ``ValueError``: *image* is not a finite real ``(H, W)`` array;
*wavelength_px* is not ``> 2`` (a shorter wavelength is past Nyquist and the
band would be empty); *bandwidth_octaves* is not ``> 0``; the band contains
no frequency bin of this frame size.

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [quaternion_monogenic](../../../../examples/quaternion_monogenic.py) — `py -3.11 examples/quaternion_monogenic.py`

## 型が繋がる次の op(`qimage` を入力に取れる)

[quaternion_to_rgb](../convert/quaternion_to_rgb.md) · [quat_norm](../convert/quat_norm.md) · [quat_conjugate_image](../algebra/quat_conjugate_image.md) · [quat_normalize_image](../algebra/quat_normalize_image.md) · [quat_image_multiply](../algebra/quat_image_multiply.md) · [monogenic_amplitude](monogenic_amplitude.md) · [monogenic_phase](monogenic_phase.md) · [monogenic_orientation](monogenic_orientation.md)

## 同カテゴリ(`riesz`)

[riesz_transform](riesz_transform.md) · [monogenic_amplitude](monogenic_amplitude.md) · [monogenic_phase](monogenic_phase.md) · [monogenic_orientation](monogenic_orientation.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
