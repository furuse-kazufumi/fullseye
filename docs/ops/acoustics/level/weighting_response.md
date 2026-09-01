---
op: weighting_response
dim: acoustics
category: level
in: signal
out: signal
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# weighting_response — ACOUSTICS `level` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import acoustics; acoustics.weighting_response(freqs, kind='A', floor_db=-200.0)` (または `opsacoustics.get("weighting_response")`)

## 使い方

The A / C / Z frequency-weighting curve, in dB, at the given frequencies.

Computed from the four pole frequencies that *define* the networks and
normalised so that the response at 1 kHz is exactly 0 dB **by construction**
— the curve is divided by its own value at 1 kHz rather than having a
published offset constant added to it. That is why the tests can assert
equality at 1 kHz to 0.0 rather than to a tolerance, and why no standard's
table of attenuations appears anywhere in this repository.

The response depends on ``f`` only through ``f**2``, so it is an even
function and negative frequencies are evaluated at ``|f|`` — that is the
definition, not a repair. ``f = 0`` has zero response (both curves have a
zero at DC) and is reported as ``floor_db`` rather than ``-inf``.

Measured (computed, then printed — these are outputs, not transcriptions):

========  =========  =========
f (Hz)    A (dB)     C (dB)
========  =========  =========
10        -70.4304   -14.3300
31.5      -39.5250    -3.0305
100       -19.1428    -0.2996
1000        0.0000     0.0000
4000        0.9633    -0.8260
10000      -2.4918    -4.4055
20000      -9.3469   -11.2786
========  =========  =========

``A(1000)`` and ``C(1000)`` are exactly ``0.0`` — the Python float, not a
rounding — because of the construction. The low-frequency asymptote is a
closed form and is asserted in the tests: ``A`` falls at exactly
80 dB/decade as ``f -> 0`` (``f**4`` over three constants) and ``C`` at
exactly 40 dB/decade (``f**2``). Measured between 0.001 and 0.01 Hz with the
floor lowered out of the way: **79.999998** and **39.999998** dB/decade.

That last caveat is real and is why the floor is an argument: with the
default ``floor_db = -200`` the A curve reaches the floor below about
0.35 Hz (unfloored, ``A(0.1) = -228.55`` dB), so the asymptote measured
against the default floor comes out as 0.0 dB/decade between 0.01 and
0.1 Hz — a clamp, correctly reported, that would look like a bug if the
floor were not visible.

Returns a float64 array the same shape as *freqs*.

**Raises** ``ValueError``: a non-1-D / non-finite / complex / masked
``freqs``, an unknown ``kind``.

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [acoustic_condition_monitoring](../../../../examples/acoustic_condition_monitoring.py) — `py -3.11 examples/acoustic_condition_monitoring.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[stft](../transform/stft.md) · [envelope_spectrum](../bearing/envelope_spectrum.md) · [spectral_kurtosis](../bearing/spectral_kurtosis.md) · [cepstrum](../bearing/cepstrum.md) · [angular_resample](../order/angular_resample.md) · [order_spectrum](../order/order_spectrum.md) · [octave_spectrum](octave_spectrum.md) · [apply_weighting](apply_weighting.md)

## 同カテゴリ(`level`)

[octave_bands](octave_bands.md) · [octave_spectrum](octave_spectrum.md) · [apply_weighting](apply_weighting.md) · [equivalent_level](equivalent_level.md) · [percentile_level](percentile_level.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
