---
op: synthesize_speed_ramp
dim: acoustics
category: synthesis
in: 
out: table
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# synthesize_speed_ramp — ACOUSTICS `synthesis` op

- **データ種**: `` → `table`
- **呼び出し**: `import acoustics; acoustics.synthesize_speed_ramp(rate=5000.0, duration=4.0, rpm_start=600.0, rpm_end=1800.0, orders=(1.0, 3.5), amplitudes=None, resonance_hz=None, noise_sigma=0.0, seed=None)` (または `opsacoustics.get("synthesize_speed_ramp")`)

## 使い方

A run-up: components locked to shaft *order*, optionally one fixed in Hz.

Order tracking has no meaning at constant speed, so its ground truth needs a
signal whose shaft rate moves. Here the shaft rate ramps linearly from
``rpm_start`` to ``rpm_end`` and each component's instantaneous phase is
``2 pi * order * revolutions(t)`` — so it is locked to the shaft *exactly*,
by construction, and its order is known to machine precision.

``resonance_hz`` adds one component at a **fixed frequency** instead. That is
the discriminating case: after angular resampling an order stays put and a
resonance smears, which is the whole diagnostic value of the transform.

Returns a dict, because a speed record without its speed profile is not
analysable: ``signal`` (the waveform), ``rpm`` (per-sample shaft rate),
``revolutions`` (cumulative, per-sample), ``rate``, ``duration``,
``orders``, ``total_revolutions``, ``resonance_hz``, and
``max_component_hz``.

**Raises** ``ValueError``: non-real / string / bool scalars, non-positive
``rate`` / ``duration`` / ``rpm_start`` / ``rpm_end``, an empty or non-finite
``orders``, an ``amplitudes`` of the wrong length, a length over
:data:`MAX_SAMPLES`, and **any component reaching Nyquist at the fastest
point of the ramp** — checked at ``max(rpm)``, not at the mean, because a
ramp that is legal on average can alias at its top end and produce a
perfectly plausible spectrum.

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [acoustic_condition_monitoring](../../../../examples/acoustic_condition_monitoring.py) — `py -3.11 examples/acoustic_condition_monitoring.py`

## 型が繋がる次の op(`table` を入力に取れる)

[istft](../transform/istft.md)

## 同カテゴリ(`synthesis`)

[synthesize_bearing_signal](synthesize_bearing_signal.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
