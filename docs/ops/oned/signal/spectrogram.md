---
op: spectrogram
dim: oned
category: signal
in: signal
out: image2d
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# spectrogram — ONED `signal` op

- **データ種**: `signal` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.spectrogram(x, rate=1.0, win=256, hop=None)` (実装を直接呼ぶなら `import dsp; dsp.spectrogram(x, rate=1.0, win=256, hop=None)`、台帳から引くなら `ops1d.get("spectrogram")`)
- **台帳経由の戻り値**: `fullseye.ledger.spectrogram(...)` は**宣言 out 型 `image2d` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.spectrogram.raw(...)`、または `dsp.spectrogram` を直接呼ぶ。
  - 本体の返り: `(freqs, times, S) — S が本体`

## 使い方

STFT magnitude spectrogram -> ``(freqs, times, S)`` with ``S`` shape
``(n_freqs, n_frames)``. Hann-windowed; *hop* defaults to ``win//2``.

**Same raw convention as :func:`spectrum`, but a different divisor.** Each
column is the unnormalised ``|rfft(frame * hann(win))|``, so it is not an
amplitude either — and dividing by ``2/win`` is *wrong* here, because the
Hann window has already thrown away part of the signal. The correct one-sided
amplitude conversion divides by the window's coherent gain::

    w = np.hanning(win)
    amp = S * (2.0 / w.sum())        # bins 1 .. win/2-1; DC / Nyquist: 1/w.sum()

Measured on a unit sine at a bin centre (``rate = 16000`` Hz, 1000 Hz,
amplitude exactly 1.0, ``win = 256``): the raw column peak is
``63.7497786196906``; ``* 2/win`` gives ``0.49804514546633283`` (too small by
exactly the Hann coherent gain ``sum(w)/win = 0.498046875``), while
``* 2/sum(w)`` gives ``0.9999965273676957``. Only the second one is the
amplitude that was actually in the signal.

Peak *positions*, frame-to-frame ratios and any dB *difference* are unaffected
by either factor. This function returns magnitudes only — the phase is
discarded, so it cannot be inverted; use ``acoustics.stft`` / ``acoustics.istft``
for a round-trip.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [acoustic_condition_monitoring](../../../../examples/acoustic_condition_monitoring.py) — `py -3.11 examples/acoustic_condition_monitoring.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

—

## 同カテゴリ(`signal`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [bandpass](bandpass.md) · [envelope](envelope.md) · [rms](rms.md) · [resample](resample.md) · [spectrum](spectrum.md) · [zero_crossing_rate](zero_crossing_rate.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
