---
op: resample
dim: oned
category: signal
in: signal
out: signal
examples: [profile_frame_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# resample — ONED `signal` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.resample(x, rate, new_rate)` (実装を直接呼ぶなら `import dsp; dsp.resample(x, rate, new_rate)`、台帳から引くなら `ops1d.get("resample")`)
- **台帳経由の戻り値**: `fullseye.ledger.resample(...)` は**宣言 out 型 `signal` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.resample.raw(...)`、または `dsp.resample` を直接呼ぶ。
  - 本体の返り: `(signal, new_rate)`

## 使い方

Resample a signal to *new_rate* (Fourier method).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [profile_frame_tour](../../../../examples/profile_frame_tour.py) — `py -3.11 examples/profile_frame_tour.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](../function/create_funct_1d_array.md) · [create_funct_1d_pairs](../function/create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](../function/smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](../function/smooth_funct_1d_mean.md) · [derivate_funct_1d](../function/derivate_funct_1d.md) · [integrate_funct_1d](../function/integrate_funct_1d.md) · [zero_crossings_funct_1d](../function/zero_crossings_funct_1d.md) · [local_min_max_funct_1d](../function/local_min_max_funct_1d.md)

## 同カテゴリ(`signal`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [bandpass](bandpass.md) · [envelope](envelope.md) · [rms](rms.md) · [spectrum](spectrum.md) · [spectrogram](spectrogram.md) · [zero_crossing_rate](zero_crossing_rate.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
