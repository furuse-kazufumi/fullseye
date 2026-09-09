---
op: bandpass
dim: oned
category: signal
in: signal
out: signal
examples: [poc_leak_localization]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# bandpass — ONED `signal` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.bandpass(x, rate, low, high, order=4)` (実装を直接呼ぶなら `import dsp; dsp.bandpass(x, rate, low, high, order=4)`、台帳から引くなら `ops1d.get("bandpass")`)

## 使い方

Butterworth band-pass between *low* and *high* Hz. Both edges must be inside
``(0, rate/2)``; same length contract as :func:`lowpass`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_leak_localization](../../../../examples/poc_leak_localization.py) — `py -3.11 examples/poc_leak_localization.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](../function/create_funct_1d_array.md) · [create_funct_1d_pairs](../function/create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](../function/smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](../function/smooth_funct_1d_mean.md) · [derivate_funct_1d](../function/derivate_funct_1d.md) · [integrate_funct_1d](../function/integrate_funct_1d.md) · [zero_crossings_funct_1d](../function/zero_crossings_funct_1d.md) · [local_min_max_funct_1d](../function/local_min_max_funct_1d.md)

## 同カテゴリ(`signal`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [envelope](envelope.md) · [rms](rms.md) · [resample](resample.md) · [spectrum](spectrum.md) · [spectrogram](spectrogram.md) · [zero_crossing_rate](zero_crossing_rate.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
