---
op: find_peaks
dim: oned
category: signal
in: signal
out: indices
examples: [poc_tree_ring_dendro, poc_web_roll_periodicity]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# find_peaks — ONED `signal` op

- **データ種**: `signal` → `indices`
- **呼び出し**: `import fullseye as fs; fs.ledger.find_peaks(x, height=None, distance=None)` (実装を直接呼ぶなら `import dsp; dsp.find_peaks(x, height=None, distance=None)`、台帳から引くなら `ops1d.get("find_peaks")`)

## 使い方

Peak indices (scipy.signal.find_peaks) — impacts / defect echoes.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tree_ring_dendro](../../../../examples/poc_tree_ring_dendro.py) — `py -3.11 examples/poc_tree_ring_dendro.py`
- [poc_web_roll_periodicity](../../../../examples/poc_web_roll_periodicity.py) — `py -3.11 examples/poc_web_roll_periodicity.py`

## 型が繋がる次の op(`indices` を入力に取れる)

[peak_subbin](peak_subbin.md)

## 同カテゴリ(`signal`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [bandpass](bandpass.md) · [envelope](envelope.md) · [rms](rms.md) · [resample](resample.md) · [spectrum](spectrum.md) · [spectrogram](spectrogram.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
