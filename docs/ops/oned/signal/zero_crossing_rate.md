---
op: zero_crossing_rate
dim: oned
category: signal
in: signal
out: measurement
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# zero_crossing_rate — ONED `signal` op

- **データ種**: `signal` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.zero_crossing_rate(x)` (実装を直接呼ぶなら `import dsp; dsp.zero_crossing_rate(x)`、台帳から引くなら `ops1d.get("zero_crossing_rate")`)

## 使い方

Fraction of adjacent samples that change sign — a cheap pitch/noisiness cue.

Exact zeros are neither a crossing nor a sign: a crossing is counted only when
the sign changes between consecutive *non-zero* samples, and the rate divides
by the number of adjacent sample pairs ``len(x) - 1``. So ``[1, 0, 1, 0, 1]`` is
``0.0`` and ``[1, 0, -1]`` is ``0.5`` (before 2026-09-02 ``diff(sign(x))`` counted
every touch of zero as a crossing: ``1.0`` for both).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`signal`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [bandpass](bandpass.md) · [envelope](envelope.md) · [rms](rms.md) · [resample](resample.md) · [spectrum](spectrum.md) · [spectrogram](spectrogram.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
