---
op: riesz_motion_magnify
dim: quat
category: motion
in: video
out: table
examples: [quaternion_monogenic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# riesz_motion_magnify — QUAT `motion` op

- **データ種**: `video` → `table`
- **呼び出し**: `import quatimage; quatimage.riesz_motion_magnify(video, alpha, f_lo, f_hi, fps, scales: 'int' = 4) -> 'dict'` (または `opsquat.get("riesz_motion_magnify")`)

## 使い方

Scale a clip's in-band motion by *alpha*, by the Riesz route. → dict.

The Riesz-pyramid magnifier of Wadhwa et al. (2014), and the direct
counterpart of ``motionmag.motion_magnify``: same contract, same ``alpha``
convention (a **displacement gain** — 1 is the identity, 2 doubles the
motion, -1 reverses it), same honesty block, different decomposition.

Each radial sub-band is turned into a monogenic signal, projected onto the
band's temporal-mean orientation to give a complex analytic signal ``z``, and
the temporal phase deviation ``angle(z * conj(z_mean))`` is band-passed and
multiplied by ``alpha - 1``. The band is then re-rendered as
``I*cos(shift) - R_proj*sin(shift)`` — the real part of ``z * exp(i*shift)``
— and the bands are summed. Because the radial filters are an *amplitude*
partition of unity, that sum is the reconstruction: at ``alpha = 1`` the
output equals the input to **5.55e-16** (measured on a 64x64x64 clip;
``motionmag.motion_magnify`` gives 7.77e-16 on the same clip).

The gain really is the gain. Measuring the magnified clip's displacement with
the *independent* steerable estimator ``motionmag.displacement_series``, on a
single-grating clip of true amplitude 0.1 px:

========  ==========================  ==========================
alpha     Riesz measured gain         steerable measured gain
========  ==========================  ==========================
0.0        0.000000000000              0.000000000000
2.0        2.000000000000              2.000000000000
4.0        4.000000000000              4.000000000000
-1.0      -1.000000000000             -1.000000000000
20.0      20.000000000000             20.000000000000
========  ==========================  ==========================

— twelve decimal places, for both, including the reversal.

Returns the same shape of dict ``motionmag.motion_magnify`` returns —
``{"video", "alpha", "band_hz", "fps", "scales", "snr_in", "snr_out",
"image_snr_change_db", "motion_snr_out_db", "motion_snr_change_db",
"band_power_ratio", "phase_shift_max_rad", "phase_shift_rms_rad",
"linear_regime", "reference_coherence"}`` — and it is the same dict because
the SNR block is computed by **calling** ``motionmag.band_snr`` rather than
re-deriving it. Two magnifiers that disagree about how to measure their own
cost cannot be compared, so they share the measurement.

**Magnification never improves the motion SNR**, here as there: scaling the
in-band phase scales the in-band noise by the same factor. What degrades is
the image SNR. Measured on the shared 64x64x64 / 32 fps / 0.2 px / 4 Hz
synthetic under sigma = 0.01 noise, band 3-5 Hz, against
``motionmag.motion_magnify`` on the identical clip:

======  ==================  ==================  ==============  ==============
alpha   image change (dB)   image change (dB)   band ratio      band ratio
        Riesz               steerable           Riesz           steerable
======  ==================  ==================  ==============  ==============
2       -4.8611             -4.8260             0.937704        0.935433
4       -10.3616            -10.3504            0.861162        0.858130
8       -15.3515            -15.5097            0.629948        0.628597
======  ==================  ==================  ==============  ==============

The two magnifiers cost essentially the same — within 0.16 dB and 0.3 % of
band-power linearity at every gain. So the choice between them is **not**
about magnification quality; it is about the displacement measurement (where
the Riesz route has a 13 % failure mode on multi-orientation texture, see
:func:`riesz_displacement`) and about cost (this one is 2.09x faster on the
same clip: 0.1034 s against 0.2163 s, best of 7).

**Raises** ``ValueError``: *video* is not a valid ``(T, H, W)`` clip or is
over :data:`MAX_PYRAMID_ELEMENTS`; ``|alpha|`` is over :data:`MAX_ALPHA`;
the pass-band is empty, reaches DC, or exceeds Nyquist; *scales* is outside
``[1, MAX_SCALES]``.

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

[riesz_displacement](riesz_displacement.md) · [riesz_displacement_series](riesz_displacement_series.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
