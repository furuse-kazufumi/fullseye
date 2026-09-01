---
op: order_spectrum
dim: acoustics
category: order
in: signal
out: table
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# order_spectrum — ACOUSTICS `order` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import acoustics; acoustics.order_spectrum(x, rate, rpm, samples_per_rev=64, revolutions=None, max_order=None, n_peaks=5)` (または `opsacoustics.get("order_spectrum")`)

## 使い方

Amplitude against shaft order — the spectrum a run-up should be read in.

:func:`angular_resample` followed by an rFFT over a **whole number of
revolutions** (the record is cropped to that). Bin spacing is
``1 / whole_revolutions`` in orders.

``revolutions`` overrides how many whole revolutions to keep, and it matters
more than it looks. An order ``o`` lands exactly on a bin only when
``o * revolutions`` is an integer; otherwise it straddles two and both read
low. Measured on the run-up below, which happens to cover 79.994
revolutions:

==============  ==========  =============  =============
revolutions     resolution  amp at o=1.0   amp at o=3.5
==============  ==========  =============  =============
79 (default)    0.012658    0.999967       **0.636961**
78 (even)       0.012821    1.000009       0.999371
==============  ==========  =============  =============

That 0.637 is the classic two-bin scallop loss, and nothing raises: the peak
is at the right order and 36 % too small, with a second peak of almost equal
height one bin away (measured 0.6370 at order 3.4937 and 0.6353 at 3.5063).
Cropping to an **even** number of revolutions puts every half-integer order
on a bin. The default is the largest whole number available; pass
``revolutions`` when the order you care about is fractional.

Returns a dict: ``orders``, ``magnitude`` (single-sided, ``2/N``),
``peak_order``, ``peak_amplitude``, ``peak_orders`` / ``peak_amplitudes``,
``resolution_order``, ``whole_revolutions``, ``samples_per_rev``,
``mean_rpm``, ``max_order``.

Measured, and this is the whole argument for the operator. A 4 s run-up from
600 to 1800 rpm at 5 kHz carrying exactly two shaft-locked components
(orders 1.0 and 3.5, unit amplitude) plus one fixed 400 Hz resonance, read
with ``revolutions=78``:

==========================  =====================  ====================
quantity                    ordinary spectrum      order spectrum
==========================  =====================  ====================
order-3.5 peak amplitude    0.070203 (of true 1)   0.999371 (of true 1)
its -3 dB width             66.50 Hz (= 3.33 ord)  0.00000 order
400 Hz resonance amplitude  1.0000, one bin        0.0517, over 26.7 ord
==========================  =====================  ====================

The ordinary spectrum recovers **7 %** of the shaft-locked component's
amplitude, because the energy is spread over 3.3 orders' worth of bins; the
order spectrum recovers **99.94 %** of it in a single bin whose -3 dB width
is one bin. The 400 Hz resonance goes the other way — sharp in hertz,
smeared across 26.7 orders after resampling. That **reversal** is the
diagnostic, and it is why both spectra are worth computing: what stays sharp
under angular resampling turns with the shaft, and what stays sharp under
ordinary transformation does not.

**Raises** ``ValueError``: everything :func:`angular_resample` refuses (in
particular the aliasing refusal), a ``revolutions`` larger than the record
actually contains, and a ``max_order`` above the angular Nyquist
``samples_per_rev/2``.

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

## 同カテゴリ(`order`)

[angular_resample](angular_resample.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
