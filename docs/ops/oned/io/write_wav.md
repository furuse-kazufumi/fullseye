---
op: write_wav
dim: oned
category: io
in: signal
out: file
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# write_wav — ONED `io` op

- **データ種**: `signal` → `file`
- **呼び出し**: `import fullseye as fs; fs.ledger.write_wav(path, x, rate=44100)` (実装を直接呼ぶなら `import dsp; dsp.write_wav(path, x, rate=44100)`、台帳から引くなら `ops1d.get("write_wav")`)

## 使い方

Write a float ``[-1,1]`` mono signal to a 16-bit PCM WAV (stdlib).
Non-finite samples raise (they would become garbage PCM).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`file` を入力に取れる)

[read_wav](read_wav.md) · [read_audio](read_audio.md)

## 同カテゴリ(`io`)

[read_wav](read_wav.md) · [read_audio](read_audio.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
