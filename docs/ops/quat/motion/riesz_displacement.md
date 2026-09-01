---
op: riesz_displacement
dim: quat
category: motion
in: video
out: table
examples: [quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# riesz_displacement — QUAT `motion` op

- **データ種**: `video` → `table`
- **呼び出し**: `import quatimage; quatimage.riesz_displacement(video, f_lo, f_hi, fps, scales: 'int' = 4) -> 'dict'` (または `opsquat.get("riesz_displacement")`)

## 使い方

Sub-pixel displacement field from the monogenic phase. → dict.

The measuring sibling of :func:`riesz_motion_magnify`, and the direct
counterpart of ``motionmag.phase_displacement``: nothing is amplified, the
displacement itself is returned in pixels.

Per radial band, the temporal phase deviation obeys
``dphi = -(kx*dx + ky*dy)`` where ``(kx, ky)`` is the local wave vector —
here ``k * n``, with the *direction* ``n`` read straight off the Riesz pair
(continuous, per pixel) and the *magnitude* ``k`` from the spectral
derivative ``Im(conj(z) d_n z)/|z|^2``. Each band gives one linear
constraint on the same two unknowns and the bands are combined per pixel by
weighted least squares with weights ``|z|^2``, solved by the closed-form 2x2
pseudo-inverse so that a rank-1 pixel (the aperture problem) returns the
component that *was* observed and exactly zero in the direction nothing
constrained.

Returns ``{"dx": (T, H, W), "dy": (T, H, W), "weight": (H, W),
"valid": (H, W) bool, "rank": (H, W) int8, "fps", "band_hz", "frames",
"wrap_limit_px", "reference_coherence"}`` — the same keys
``motionmag.phase_displacement`` returns, so the two are drop-in comparable.

Head to head against the complex steerable route
------------------------------------------------
All of the following is measured against ``motionmag.phase_displacement`` on
identical clips (64x64x64, 32 fps, 4 Hz bin-centred, band 3-5 Hz), with the
truth from an exact Fourier phase ramp and the error read as the deviation of
the least-squares gain from 1. **The verdict is mixed and the losses are
stated first.**

*When the model holds — one moving component per band — the two are the same
answer.* A single grating, translated:

============  ======================  ======================
true d (px)   Riesz relative error    steerable rel. error
============  ======================  ======================
0.001         1.463e-13               1.694e-13
0.010         3.997e-15               6.217e-15
0.100         3.331e-16               0.0
0.500         3.331e-16               0.0
1.000         0.0                     0.0
2.000         0.0                     2.220e-16
3.000         0.0                     0.0
3.050         2.220e-16               2.220e-16
3.060         1.332e-15               0.0
3.070         1.573e+00  <- broken    1.573e+00  <- broken
4.000         1.207e+00  <- broken    1.207e+00  <- broken
============  ======================  ======================

Both are exact to rounding, and **both break in the same place, between 3.06
and 3.07 px** — which is the closed-form ``J0`` zero, not an empirical
tolerance: the temporal-mean phase reference equals ``c * J0(k*A)``, whose
first zero at ``k*A = 2.4048`` is ``A = 2.4048/(2*pi/8) = 3.0619`` px for an
8 px grating. The Riesz route does **not** lift that ceiling, because the
ceiling belongs to the temporal-mean reference and not to the decomposition.

*Where the Riesz route loses, and it loses badly.* A radial band has no
orientation index, so two components at the same scale but different
orientations land in **one** band and the single-plane-wave model behind the
monogenic signal is simply false there. A steerable bank separates them by
filter. On ``motionmag.synthesize_translation``, whose default is exactly
that situation:

==================================  ==================  ==================
clip                                Riesz rel. error    steerable rel. err
==================================  ==================  ==================
lambda = (8, 16) px  [the default]  1.299e-01           4.441e-16
lambda = (8, 32) px  [2 octaves]    2.220e-16           0.0
lambda = (8, 8)  px  [same band]    6.256e-01           1.329e-02
==================================  ==================  ==================

A **13 % displacement error that does not shrink as the displacement shrinks,
with no exception and no NaN** — and 63 % when the two gratings share a
wavelength outright. Separate the components by two octaves and the error
returns to machine precision, which identifies the cause exactly. Any scene
with texture at several orientations in one octave — that is, most real
scenes — is in the bad case. This is the single most important limitation of
the Riesz route and no amount of tuning removes it.

*A second loss: it cannot measure everywhere.* The wave vector comes from the
Riesz pair, which **vanishes at every even-symmetric point** (local phase 0
or pi — the crest of a bright or dark line) even though the amplitude there
is at full strength. Measured on the single-grating clip, 1024 of 4096 pixels
(25.0 %) come back rank 0 against 0 of 4096 for the steerable route, whose
orientation comes from the filter and never degenerates. The affected pixels
are marked in ``rank`` and weighted zero, so they do not corrupt the answer —
but they are holes in the field.

*The theoretical win does not materialise.* Continuous per-pixel orientation
should beat a 4-orientation bank on oblique structure. Measured, it does not
— the raised-cosine angular windows already interpolate exactly:

===============  ==================  ==================
grating (deg)    Riesz rel. error    steerable rel. err
===============  ==================  ==================
0.0              3.331e-16           0.0
20.6             4.441e-16           4.441e-16
45.0             4.441e-16           4.441e-16
69.4             4.441e-16           4.441e-16
90.0             3.331e-16           0.0
===============  ==================  ==================

*Two wins that are real.* Under noise the Riesz estimate is consistently
about twice as accurate, because it spends its degrees of freedom on 4 bands
instead of 19 and admits fewer noise-only sub-bands to the normal equations
(single grating, A = 0.5 px):

==========  ==================  ==================
sigma       Riesz rel. error    steerable rel. err
==========  ==================  ==================
0.001       1.812e-05           2.329e-05
0.010       3.008e-04           5.119e-04
0.050       4.047e-03           8.670e-03
==========  ==================  ==================

And it is cheaper: it builds ``scales`` = 4 sub-bands where the steerable
bank builds ``scales * orientations + 3`` = 19. Measured wall clock on the
64x64x64 clip, best of 7: **0.0888 s against 0.1063 s (1.20x)** here, and
**0.1034 s against 0.2163 s (2.09x)** for the magnifiers — less than the
19:4 filter ratio suggests, because each Riesz band costs three inverse FFTs
(band, R1, R2) where a steerable band costs one.

**Summary, honestly.** Use the steerable route when the scene has structure
at several orientations per octave, which is the common case; use this one
when the scene is narrow-band, when the clip is noisy, or when the 2x is
worth having. The quaternion is the right *object* for the monogenic signal
and gives orientation for free; it does not make the measurement better.

**Raises** ``ValueError``: *video* is not a valid clip or is over
:data:`MAX_PYRAMID_ELEMENTS`; the pass-band is empty, reaches DC or exceeds
Nyquist; *scales* is outside ``[1, MAX_SCALES]``.

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [quaternion_monogenic](../../../../examples/quaternion_monogenic.py) — `py -3.11 examples/quaternion_monogenic.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`motion`)

[riesz_motion_magnify](riesz_motion_magnify.md) · [riesz_displacement_series](riesz_displacement_series.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
