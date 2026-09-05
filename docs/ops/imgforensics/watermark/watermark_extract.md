---
op: watermark_extract
dim: imgforensics
category: watermark
in: image2d
out: phash
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# watermark_extract — IMGFORENSICS `watermark` op

- **データ種**: `image2d` → `phash`
- **呼び出し**: `import imgforensics; imgforensics.watermark_extract(image, n_bits: 'int', wavelet: 'str' = 'haar', level: 'int' = 1) -> 'np.ndarray'` (または `opsimgforensics.get("watermark_extract")`)

## 使い方

透かしの **ブラインド抽出**。bool の 1-D(``phash`` 語彙)を返す。

同じ DWT / ブロック分割で中帯域係数の対の大小を読むだけ。原画像も鍵も要らない
—— これは **秘匿ではなく完全性の印**であり、鍵が無いので **誰でも消せるし
誰でも書ける**。所有権の主張には使えない。

返りが ``phash`` 語彙なので、埋めたビット列との一致は :func:`hash_distance` で
そのまま数えられる(BER = ``hash_distance(sent, got) / n_bits``)。
語彙を合わせてあるのはそのため。

**PyWavelets 必須**(:class:`ImportError`)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`phash` を入力に取れる)

[hash_distance](../hash/hash_distance.md) · [watermark_embed](watermark_embed.md) · [watermark_capacity](watermark_capacity.md)

## 同カテゴリ(`watermark`)

[watermark_embed](watermark_embed.md) · [watermark_capacity](watermark_capacity.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
