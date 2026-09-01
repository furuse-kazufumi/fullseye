---
op: angular_resample
dim: acoustics
category: order
in: signal
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# angular_resample — ACOUSTICS `order` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import acoustics; acoustics.angular_resample(x, rate, rpm, samples_per_rev=64)` (または `opsacoustics.get("angular_resample")`)

## 使い方

Resample a time record onto the shaft-angle axis (computed order tracking).

Under a changing shaft speed, a component locked to the shaft has a moving
frequency and smears across the spectrum, while a structural resonance stays
put. Resample the record so the samples are equally spaced in **shaft angle**
instead of in time and the situation reverses exactly: the order becomes a
single line and the resonance smears.

``rpm`` is either a single number (constant speed — the transform is then a
pure rescaling) or a per-sample array on the same clock as the signal. The
cumulative revolution count is the trapezoidal integral of ``rpm/60``, and
the signal is linearly interpolated onto a uniform grid in it.

Returns a dict — an angle-domain record is **not** put into circulation as a
plain signal, deliberately. Its samples are indexed by angle, not time, so
handing it to any op that takes a ``rate`` would produce frequencies in Hz
from an axis measured in revolutions: no exception, no NaN, just wrong
numbers. (Same judgement, and the same reason, as ``motionmag.motion_magnify``
not exposing a bare video adapter.) The dict carries ``signal``,
``angle_rev``, ``samples_per_rev``, ``revolutions`` (total),
``whole_revolutions``, ``rate`` (the original time-domain one, for
provenance), ``mean_rpm``, ``max_order``.

``max_order`` is ``samples_per_rev / 2`` — the Nyquist of the *angle* axis.

Measured: a pure order-3.5 component on a 600 -> 1800 rpm ramp, resampled at
64 samples/rev over 78 whole revolutions, reads amplitude 0.999371 in a
single bin of the order spectrum; the same component in the ordinary
spectrum peaks at 0.070203 and is 66.5 Hz wide.

**Raises** ``ValueError``: everything :func:`_as_signal` refuses, a
non-positive or wrong-length ``rpm``, ``samples_per_rev`` outside
``[2, 65536]``, an output over :data:`MAX_ANGULAR_SAMPLES`, fewer than one
complete revolution in the record, and — the aliasing refusal — a
``samples_per_rev`` whose implied Nyquist order needs content above the
time-domain Nyquist. Asking for 64 samples/rev on a shaft turning at 30 Hz
means representing 960 Hz, which a 100 Hz recording does not contain; the
resampler would happily manufacture it from the interpolation.

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[istft](../transform/istft.md)

## 同カテゴリ(`order`)

[order_spectrum](order_spectrum.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
