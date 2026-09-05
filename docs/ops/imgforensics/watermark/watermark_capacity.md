---
op: watermark_capacity
dim: imgforensics
category: watermark
in: image2d × phash
out: table
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# watermark_capacity — IMGFORENSICS `watermark` op

- **データ種**: `image2d × phash` → `table`
- **呼び出し**: `import imgforensics; imgforensics.watermark_capacity(image, bits, strengths=(0.02, 0.05, 0.1, 0.2, 0.4), wavelet: 'str' = 'haar', level: 'int' = 1, jpeg_quality=None) -> 'dict'` (または `opsimgforensics.get("watermark_capacity")`)

## 使い方

埋め込み強度と **PSNR / BER** のトレードオフを掃引して返す。``table``。

各 ``strength`` について埋め込み → 抽出を実際に走らせ、

``psnr_db``  原画像と透かし入り画像の PSNR(値域 [0, 1] 基準、``MAX=1``)
``ber``      抽出のビット誤り率(:func:`hash_distance` で数える)
``clipped``  透かし入り画像が [0, 1] からはみ出した画素の割合。
             **はみ出しは保存時に必ず失われる**ので、PSNR だけ見て強度を
             上げると「測っていない劣化」が増える

``jpeg_quality`` に品質を渡すと、透かし入り画像を **本物の JPEG** に通してから
抽出した ``ber_jpeg`` も入る(Pillow 必須。省略時は列ごと入らない ——
環境によって返る列が変わらないようにするため、既定では走らせない)。

返りは ``{"capacity_bits": int, "n_bits": int, "rows": [...], "caveats": [...]}``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`table` を入力に取れる)

[evidence_quantile](../calibration/evidence_quantile.md)

## 同カテゴリ(`watermark`)

[watermark_embed](watermark_embed.md) · [watermark_extract](watermark_extract.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
