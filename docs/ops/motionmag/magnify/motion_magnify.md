---
op: motion_magnify
dim: motionmag
category: magnify
in: video
out: table
examples: [motion_magnification, poc_motion_magnification, quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# motion_magnify — MOTIONMAG `magnify` op

- **データ種**: `video` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.motion_magnify(video, alpha, f_lo, f_hi, fps, scales: 'int' = 4, orientations: 'int' = 4) -> 'dict'` (実装を直接呼ぶなら `import motionmag; motionmag.motion_magnify(video, alpha, f_lo, f_hi, fps, scales: 'int' = 4, orientations: 'int' = 4) -> 'dict'`、台帳から引くなら `opsmotionmag.get("motion_magnify")`)

## 使い方

Scale the in-band motion of a clip by *alpha* -> ``dict``.

For every oriented sub-band of every frame the local phase is taken relative
to that band's temporal mean as the **wrapped** deviation
``angle(z * conj(z_mean))`` in ``(-pi, pi]`` — it is deliberately **not**
unwrapped along time (see the design note above ``_AMP_FLOOR``: unwrapping
a noise band is a random walk that manufactured a 12.27 rad step where
0.039 rad was intended) — band-passed to
``[f_lo, f_hi]``, multiplied by ``alpha - 1`` and added back. Because a
translation by ``d`` shifts a band's phase by ``-k·d``, the phase of the
result is ``-alpha * k·d`` for *any* ``k`` — the output displacement is
``alpha * d`` without the local spatial frequency ever being estimated.
Low-pass, high-pass and completion residuals are reconstructed untouched
(they have no single ``k`` to be consistent about).

``alpha`` is the **displacement gain**: 1 is the identity, 0 removes the
in-band motion, 2 doubles it, -1 reverses it. (The literature writes the
magnified motion as ``(1 + alpha_paper) d``; this ``alpha`` is
``1 + alpha_paper``.)

Returns a dict::

    {"video": (T, H, W) magnified frames,
     "alpha": ..., "band_hz": (f_lo, f_hi), "fps": ...,
     "snr_in": {...}, "snr_out": {...},        # raw band_snr of in / out
     "image_snr_change_db": ...,               # <= 0 once |alpha| > 1
     "motion_snr_out_db": ...,                 # gain-corrected; never rises
     "motion_snr_change_db": ...,
     "band_power_ratio": ...,                  # 1.0 = perfectly linear
     "phase_shift_max_rad": ..., "phase_shift_rms_rad": ...,
     "linear_regime": bool, "reference_coherence": ...}

**The SNR block is part of the contract, not decoration.** Amplifying the
in-band phase amplifies the in-band noise by exactly the same factor, so
the *motion* SNR cannot rise — magnification reveals motion, it never
measures it better than the recording allowed. What degrades is the image:
the output's temporal fluctuation grows like ``alpha^2`` against an
unchanged static scene. Measured on a 64x64, 64-frame, 32 fps clip carrying
0.2 px of 4 Hz motion under sigma = 0.01 sensor noise, band 3-5 Hz:

======  ===============  ==================  ==============  =============
alpha   image_snr (dB)   image change (dB)   motion_snr_out  band_power
                                             (dB)            ratio
======  ===============  ==================  ==============  =============
1       29.2574          -0.0000             11.9404         1.000000
2       24.4304          -4.8270             11.6285         0.934861
4       18.9039          -10.3535            11.2270         0.857626
8       13.7428          -15.5146             9.7565         0.628551
======  ===============  ==================  ==============  =============

Roughly 5 dB of image SNR per doubling (the algebra's asymptote is
``20*log10(2) = 6.02`` once the amplified band dominates the noise budget),
while the motion SNR only ever falls. ``band_power_ratio`` is the measured
``band_power_out / (alpha^2 * band_power_in)``: 1.0 means the magnification
stayed linear, and the shortfall is the energy the phase modulation threw
into harmonics.

``phase_shift_max_rad`` is the largest increment applied anywhere, including
in contrast-free bands that hold only noise, so it is routinely large and is
reported for completeness rather than as a verdict. ``phase_shift_rms_rad``
is the contrast-weighted RMS — the number that describes the structure a
viewer actually sees — and ``linear_regime`` is ``phase_shift_rms_rad < pi``.

★ **``linear_regime`` is wrong in both directions. Read
``reference_coherence`` instead.** Measured 2026-09-06 on a 64x64 / 100
frame / 37 fps clip, 3.7 Hz on-bin, band 3.0-4.5 Hz:

==========  =======  ==============  ==============  ==================
amplitude   alpha    rms [rad]       linear_regime   reference_coherence
==========  =======  ==============  ==============  ==================
0.10 px         200          7.809   **False**                   0.9992
2.50 px           3          0.661   True                        0.6225
3.05 px           3          0.017   **True**                    0.5024
3.10 px           3          0.032   **True**                    0.5077
==========  =======  ==============  ==============  ==================

Row 1: ``alpha = 200`` on a 0.1 px motion is reproduced to a fidelity error
of 2e-14 against a clip that really was moved 200x — perfectly linear, and
the flag says False. **The magnification factor does not break linearity;
the input amplitude does.** Rows 3 and 4 straddle the actual breakdown, at
the first zero of ``J0(k A)`` (``2.4048 / k = 3.0619 px`` here), where the
fidelity error jumps from machine precision to 1.6e+01 — and the flag says
True. Worse, ``phase_shift_rms_rad`` **collapses** across that boundary
(0.661 -> 0.017) rather than growing, because the temporal-mean phase
reference the RMS is measured against is itself dying. A statistic that
points the wrong way cannot be repaired by moving its threshold, so the
flag is left as it is (it does report what it says: whether the phase
increment stayed under pi) and ``reference_coherence`` — which falls
monotonically 1.00 -> 0.50 as the amplitude approaches that zero — is the
number to act on. Pinned by
``tests/test_motionmag.py::test_linear_regime_flag_is_wrong_in_both_directions``.
``reference_coherence`` is ``|mean_t z| / mean_t |z|``, weighted by band
energy: it is 1 for small motion and collapses towards 0 when the motion is
large enough that the temporal-mean phase reference stops being meaningful
(see :func:`phase_displacement` for the closed form).

**Narrow-band condition, measured.** The relation is exact when each
sub-band carries a single moving component. On broadband texture (isotropic
noise smoothed by a Gaussian, 0.2 px of motion, ``alpha = 3``) the recovered
magnified amplitude is 4.8 % low at sigma = 1.0, 5.5 % at 1.5 and 9.1 % at
3.0 px of smoothing — the more spatial frequencies share a band, the more
the phase of their sum departs from linearity in the displacement. That is
inherent to phase-based processing, not a tuning fault.

## 詳しい使い方ガイド

- [motion_magnification ファミリ ガイド](../guides/motion_magnification.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_magnification](../../../../examples/motion_magnification.py) — `py -3.11 examples/motion_magnification.py`
- [poc_motion_magnification](../../../../examples/poc_motion_magnification.py) — `py -3.11 examples/poc_motion_magnification.py`
- [quaternion_monogenic](../../../../examples/quaternion_monogenic.py) — `py -3.11 examples/quaternion_monogenic.py`

## 型が繋がる次の op(`table` を入力に取れる)

[complex_steerable_reconstruct](../decompose/complex_steerable_reconstruct.md)

## 同カテゴリ(`magnify`)

—

---
*Provenance: motionmag.py — MOTIONMAG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
