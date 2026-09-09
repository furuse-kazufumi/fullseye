---
op: read_audio
dim: oned
category: io
in: file
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# read_audio — ONED `io` op

- **データ種**: `file` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.read_audio(path)` (実装を直接呼ぶなら `import dsp; dsp.read_audio(path)`、台帳から引くなら `ops1d.get("read_audio")`)

## 使い方

Read any audio format -> ``(x, rate)``. Uses ``soundfile`` if available
(mp3/flac/ogg/…), else falls back to the stdlib WAV reader.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](../function/create_funct_1d_array.md) · [create_funct_1d_pairs](../function/create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](../function/smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](../function/smooth_funct_1d_mean.md) · [derivate_funct_1d](../function/derivate_funct_1d.md) · [integrate_funct_1d](../function/integrate_funct_1d.md) · [zero_crossings_funct_1d](../function/zero_crossings_funct_1d.md) · [local_min_max_funct_1d](../function/local_min_max_funct_1d.md)

## 同カテゴリ(`io`)

[read_wav](read_wav.md) · [write_wav](write_wav.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
