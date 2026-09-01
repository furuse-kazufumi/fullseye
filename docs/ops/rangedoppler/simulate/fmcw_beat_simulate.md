---
op: fmcw_beat_simulate
dim: rangedoppler
category: simulate
in: 
out: beatcube
examples: [fmcw_range_doppler]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# fmcw_beat_simulate — RANGEDOPPLER `simulate` op

- **データ種**: `` → `beatcube`
- **呼び出し**: `import rangedoppler; rangedoppler.fmcw_beat_simulate(ranges_m=(10.0,), velocities_ms=(0.0,), angles_deg=None, amplitudes=None, n_samples=64, n_chirps=32, n_antennas=1, sample_rate_hz=10000000.0, slope_hz_per_s=20000000000000.0, chirp_period_s=5e-05, wavelength_m=0.0038934, element_spacing_m=None, phase_deg=0.0, noise_sigma=0.0, seed=0)` (または `opsrangedoppler.get("fmcw_beat_simulate")`)

## 使い方

Synthesise the complex ``(A, C, S)`` beat cube for known targets.

The forward model. Every target ``t`` contributes

``a_t * exp(1j*(2*pi*f_b_t*n/f_s + 2*pi*f_d_t*m*T_c + 2*pi*d*k*sin(th_t)/lam + phi))``

over fast-time sample ``n``, chirp ``m`` and antenna ``k``, with
``f_b = 2*S*R/c`` and ``f_d = 2*v/lambda``. Contributions add linearly, which
is what makes a multi-target cube a valid ground truth: each target's peak
stands at its own bin regardless of the others.

**Sign conventions** (see the module docstring): ``velocities_ms`` is
``dR/dt``, so **positive is receding** and lands in a positive Doppler bin;
``angles_deg`` is measured from array boresight and a positive angle advances
the phase of the higher-index elements.

*amplitudes* defaults to 1.0 for every target — there is no radar equation
here, no ``1/R^4``, no propagation loss (module docstring, honest limits).
*noise_sigma* adds circular complex Gaussian noise with that per-component
standard deviation, drawn from ``numpy.random.default_rng(seed)``; the
default 0.0 returns the exact noiseless cube, which is what the closed-form
tests compare against.

Ground truth: a target placed at an exact bin centre — ``R = j*dR`` and
``v = i*dv`` from :func:`fmcw_design` — puts the whole of its energy in bin
``(i, j)`` of :func:`range_doppler_map`, whose peak magnitude is then exactly
``a * N_s * N_c``. Measured on the default configuration: the peak magnitude
is bit-exactly 2048.0 (``N_s*N_c``, relative error 0.0), the largest other
cell in the map is 2.6e-16 of it, and with three targets at different bins
and different amplitudes the recovered ranges and velocities are exact to
0.0 metres and 0.0 m/s with amplitudes within 5.6e-17. See
``tests/test_rangedoppler.py``.

**Raises** ``ValueError``: a range at or beyond ``c*f_s/(2S)``, a speed at or
beyond ``lambda/(4*T_c)``, an angle at or beyond ``asin(lambda/(2d))`` — the
three aliasing limits, refused rather than folded silently; a non-positive
range; mismatched target-list lengths; a cube over
:data:`MAX_CUBE_ELEMENTS` (checked *before* allocation); a negative
amplitude or noise sigma; a non-integer seed; and the usual
string/bool/complex/NaN scalar refusals.

## 詳しい使い方ガイド

- [fmcw_range_doppler ファミリ ガイド](../guides/fmcw_range_doppler.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fmcw_range_doppler](../../../../examples/fmcw_range_doppler.py) — `py -3.11 examples/fmcw_range_doppler.py`

## 型が繋がる次の op(`beatcube` を入力に取れる)

[fmcw_window_apply](../process/fmcw_window_apply.md) · [range_doppler_map](../process/range_doppler_map.md) · [fmcw_range_profile](../process/fmcw_range_profile.md) · [beamform_delay_sum](../beamform/beamform_delay_sum.md) · [beamform_doa](../beamform/beamform_doa.md)

## 同カテゴリ(`simulate`)

—

---
*Provenance: rangedoppler.py — RANGEDOPPLER operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
