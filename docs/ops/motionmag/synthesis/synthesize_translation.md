---
op: synthesize_translation
dim: motionmag
category: synthesis
in: 
out: video
examples: [motion_magnification, quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# synthesize_translation — MOTIONMAG `synthesis` op

- **データ種**: `` → `video`
- **呼び出し**: `import motionmag; motionmag.synthesize_translation(shape=(64, 64), frames: 'int' = 32, amplitude_px=0.5, frequency_hz=4.0, fps=32.0, direction_deg=0.0, wavelength_px=(8.0, 16.0), contrast=0.4, offset=0.5, noise_sigma=0.0, seed: 'int' = 0) -> 'np.ndarray'` (または `opsmotionmag.get("synthesize_translation")`)

## 使い方

A clip whose displacement is known in closed form -> ``(T, H, W)`` video.

The scene is a stationary two-axis sinusoidal grating that is translated,
frame by frame, by

    ``d(t) = amplitude_px * sin(2*pi * frequency_hz * t / fps)``

along *direction_deg* (0 deg = towards +x / increasing column). The
translation is applied as a Fourier phase ramp, which for a pattern that is
periodic on the grid is the *exact* band-limited shift — no interpolation
kernel, no resampling error, so ``d(t)`` is ground truth to machine
precision and sub-pixel amplitudes are meaningful.

``wavelength_px`` is either one number (both axes) or ``(lambda_x,
lambda_y)``. **The default deliberately makes the two axes different
octaves**, and that is not cosmetic: if the horizontal and vertical gratings
share a radial frequency they land in the *same* sub-band, whose local phase
is then the phase of a sum of two moving components rather than of one. The
phase of a sum is not linear in the displacement, so scaling it does not
scale the motion — measured, a 64x64 clip built with a single wavelength on
both axes magnified at ``alpha = 2`` came out at ``0.939 * (2 d)`` instead of
``2 d``, a 6.1 % error that does *not* shrink as ``d`` shrinks. Separating
the octaves puts one component in each band and the relation becomes exact.
This is the standard narrow-band condition of phase-based processing, made
visible in the synthetic instead of hidden.

Each wavelength is snapped so that a whole number of cycles fits the frame
(``cycles = max(1, round(W / wavelength_px))``, effective wavelength
``W / cycles``); without that the pattern is not periodic on the grid and the
Fourier shift would wrap a discontinuity across the border. With the default
64x64 frame and ``(8, 16)`` the snap is exact (8 and 4 cycles).

Values are **not clipped** into ``[0, 1]``: clipping is a nonlinearity that
would break the exact translation this function exists to provide. With the
defaults the samples lie in ``[offset - contrast, offset + contrast]``.

*noise_sigma* adds zero-mean Gaussian sensor noise (after translation, drawn
from ``numpy.random.default_rng(seed)``) — the term that makes an SNR
measurable at all.

This is the counterpart of ``photoncount.tcspc_simulate``: a forward model
good enough to close the loop on the analysis operators in this module.

## 詳しい使い方ガイド

- [motion_magnification ファミリ ガイド](../guides/motion_magnification.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_magnification](../../../../examples/motion_magnification.py) — `py -3.11 examples/motion_magnification.py`
- [quaternion_monogenic](../../../../examples/quaternion_monogenic.py) — `py -3.11 examples/quaternion_monogenic.py`

## 型が繋がる次の op(`video` を入力に取れる)

[temporal_bandpass](../temporal/temporal_bandpass.md) · [temporal_band_power](../temporal/temporal_band_power.md) · [band_snr](../temporal/band_snr.md) · [motion_magnify](../magnify/motion_magnify.md) · [phase_displacement](../measure/phase_displacement.md) · [displacement_series](../measure/displacement_series.md)

## 同カテゴリ(`synthesis`)

—

---
*Provenance: motionmag.py — MOTIONMAG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
