---
op: signal_features
dim: oned
category: signal
in: signal
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# signal_features — ONED `signal` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.signal_features(x, rate=1.0)` (実装を直接呼ぶなら `import dsp; dsp.signal_features(x, rate=1.0)`、台帳から引くなら `ops1d.get("signal_features")`)

## 使い方

A compact acoustic/vibration feature vector for anomaly detection:
``rms``, ``peak``, ``crest_factor``, ``zcr``, ``spectral_centroid`` (Hz),
``peak_freq`` (Hz), ``bandwidth`` (Hz). All finite — a NaN / Inf sample raises
``ValueError`` rather than producing NaN features; empty signal -> zeros.

The three spectral entries are built on :func:`spectrum`, but every one of
them is a *ratio* of magnitudes (``argmax``, a magnitude-weighted mean, a
magnitude-weighted spread), so the raw ``|rfft|`` convention documented there
cancels out and these numbers are unaffected by it. ``rms``, ``peak`` and
``crest_factor`` are computed in the time domain and never touch the FFT.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`signal`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [bandpass](bandpass.md) · [envelope](envelope.md) · [rms](rms.md) · [resample](resample.md) · [spectrum](spectrum.md) · [spectrogram](spectrogram.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
