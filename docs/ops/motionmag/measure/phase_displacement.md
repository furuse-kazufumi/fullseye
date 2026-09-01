---
op: phase_displacement
dim: motionmag
category: measure
in: video
out: table
examples: [motion_magnification]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# phase_displacement — MOTIONMAG `measure` op

- **データ種**: `video` → `table`
- **呼び出し**: `import motionmag; motionmag.phase_displacement(video, f_lo, f_hi, fps, scales: 'int' = 4, orientations: 'int' = 4) -> 'dict'` (または `opsmotionmag.get("phase_displacement")`)

## 使い方

Sub-pixel displacement field from local phase -> ``dict``.

The quantitative sibling of :func:`motion_magnify`: nothing is amplified and
nothing is re-rendered, the displacement itself is returned in pixels.

For each oriented sub-band, the temporal phase deviation ``dphi(t)`` (taken
against the band's temporal mean, unwrapped in time, band-passed) obeys
``dphi = -(kx*dx + ky*dy)``, where ``(kx, ky)`` is the band's **local**
spatial frequency in radians per pixel — computed exactly as
``Im(conj(z) grad z)/|z|^2`` with a spectral derivative, not from the band's
nominal centre. Each band contributes one linear constraint on the same
two unknowns, so the bands are combined per pixel by weighted least squares
with weights ``|z|^2`` (a band with no contrast gets no vote).

Returns ``{"dx": (T, H, W), "dy": (T, H, W), "weight": (H, W),
"valid": (H, W) bool, "rank": (H, W) int8, "fps": ..., "band_hz": ...,
"wrap_limit_px": ..., "reference_coherence": ...}``. ``dx``/``dy`` follow
:mod:`flow`: ``dx`` is column motion, ``dy`` row motion, positive towards
increasing index, and both are zero-mean along time because the band-pass
removed DC.

``rank`` says how much of the 2-D displacement the data could constrain at
each pixel: 2 = both components, 1 = **the aperture problem** (every band
with contrast there shares one orientation, so only the component along it
is observable — that component is returned and the unobservable direction is
exactly 0), 0 = no contrast at all, both zero. Measured on a purely
horizontal grating moving 0.3 px horizontally, every pixel is rank 1 and the
answer is ``dx = 0.3000000000000001``, ``dy = 0.0`` exactly.

**Accuracy and where it stops** (measured, 64x64x64 clip at 32 fps, 8 px
horizontal grating, 4 Hz bin-centred, noiseless, defaults; the error is on
the peak of the recovered waveform):

==============  ==============  ==============  ===================
true d (px)     k*d (rad)       measured (px)   relative error
==============  ==============  ==============  ===================
0.001           0.0008          0.00100000      8.7e-15
0.010           0.0079          0.01000000      3.1e-15
0.100           0.0785          0.10000000      1.8e-15
0.500           0.3927          0.50000000      6.7e-16
1.000           0.7854          1.00000000      4.4e-16
2.000           1.5708          2.00000000      6.7e-16
3.000           2.3562          3.00000000      5.9e-16
3.050           2.3954          3.05000000      2.9e-16
3.100           2.4347          1.72842712      4.4e-01   <- broken
4.000           3.1416          2.10461396      4.7e-01   <- broken
6.000           4.7124          2.35441757      6.1e-01   <- broken
==============  ==============  ==============  ===================

Exact to rounding — and then it stops, abruptly, between 3.05 and 3.10 px.
That boundary is closed-form, and it is *not* the naive phase-wrap bound.
The temporal phase reference is the band's temporal mean ``z_mean``, and for
a sinusoidal displacement of amplitude ``A`` that mean equals
``c * J0(k*A)`` — a Bessel function. At ``k*A = 2.4048``, the first zero of
``J0``, the reference amplitude passes through zero and its phase flips by
``pi``; every deviation measured against it is then wrong by ``pi``. For the
8 px grating that is ``A = 2.4048/(2*pi/8) = 3.0619`` px, which is exactly
where the table breaks. ``reference_coherence`` in the return is
``|z_mean| / mean_t|z|``, i.e. ``|J0(k*A)|`` blended over the bands, and it
falls monotonically from 1.00000 at 0.001 px to 0.50252 at the 3.05 px edge
— a runtime warning that the reference is going degenerate.

Beyond that sits the harder bound ``|k*d| < pi`` (half a band wavelength,
reported as ``wrap_limit_px`` from the measured local frequencies), which no
phase-based method can pass with a single band.

Under noise the accuracy is set by the noise, not by the method: on the same
clip with ``A = 0.5`` px, additive sigma = 0.001 / 0.01 / 0.05 gives
relative errors 2.2e-04 / 1.8e-03 / 1.9e-03.

## 詳しい使い方ガイド

- [motion_magnification ファミリ ガイド](../guides/motion_magnification.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_magnification](../../../../examples/motion_magnification.py) — `py -3.11 examples/motion_magnification.py`

## 型が繋がる次の op(`table` を入力に取れる)

[complex_steerable_reconstruct](../decompose/complex_steerable_reconstruct.md)

## 同カテゴリ(`measure`)

[displacement_series](displacement_series.md)

---
*Provenance: motionmag.py — MOTIONMAG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
