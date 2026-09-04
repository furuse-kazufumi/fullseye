---
op: watermark_embed
dim: imgforensics
category: watermark
in: image2d × phash
out: image2d
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# watermark_embed — IMGFORENSICS `watermark` op

- **データ種**: `image2d × phash` → `image2d`
- **呼び出し**: `import imgforensics; imgforensics.watermark_embed(image, bits, strength: 'float' = 0.1, wavelet: 'str' = 'haar', level: 'int' = 1) -> 'np.ndarray'` (または `opsimgforensics.get("watermark_embed")`)

## 使い方

DWT-DCT **電子透かし**の埋め込み。透かし入り画像 ``(H, W)`` を返す。``image2d``。

1 段 DWT(既定 haar)の LL 副帯域を 8x8 に切り、各ブロックの直交 DCT-II の
**中帯域係数の対** ``(3,1)`` と ``(1,3)`` の大小関係で 1 ビットを表す
(Hsu & Wu 1999 の中帯域係数対法)。差が ``strength`` 未満なら差が
``strength`` になるまで **対称に**動かす(片方だけ動かすとブロックの
エネルギーが偏る)。抽出に原画像は要らない(ブラインド)。

容量は ``(LL の高さ // 8) * (LL の幅 // 8)`` ビット。``bits`` がそれより短ければ
先頭から埋め、残りのブロックは触らない。長ければ :class:`ValueError`。

``bits`` は bool の 1-D(``phash`` 語彙)。0/1 の int 配列も受けるが、
**float は受けない**(丸めの向きを黙って決めない)。

強度と画質のトレードオフは :func:`watermark_capacity` が掃引して表で返す。
実測(256x256 のテクスチャ画像・128 ビット、LL は 128x128 = 容量 256 ビット。
``tests/test_imgforensics.py::test_watermark_strength_psnr_tradeoff``):

========= ========== ====== ================= =================
strength  PSNR (dB)  BER    BER(JPEG 品質 90) BER(JPEG 品質 75)
========= ========== ====== ================= =================
0.02      45.48      0.000  0.008             0.195
0.05      44.48      0.000  0.000             0.008
0.10      42.95      0.000  0.000             0.000
0.20      40.32      0.000  0.000             0.000
0.40      36.37      0.000  0.000             0.000
========= ========== ====== ================= =================

**これがトレードオフの実体**である。無加工なら最弱の 0.02 でも誤り 0 だが、
JPEG 品質 75 を通すと 19.5% が化ける。既定の 0.1 は「品質 75 まで誤り 0、
PSNR 42.95 dB」の点として選んである(``clipped`` はどの強度でも 0)。

**PyWavelets 必須**(:class:`ImportError`)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[perceptual_hash](../hash/perceptual_hash.md) · [fingerprint_correlate](../sensor/fingerprint_correlate.md) · [error_level_map](../compression/error_level_map.md) · [jpeg_quality_estimate](../compression/jpeg_quality_estimate.md) · [jpeg_ghost_map](../compression/jpeg_ghost_map.md) · [noise_inconsistency_map](../noise/noise_inconsistency_map.md) · [copy_move_regions](../copy_move/copy_move_regions.md) · [watermark_extract](watermark_extract.md)

## 同カテゴリ(`watermark`)

[watermark_extract](watermark_extract.md) · [watermark_capacity](watermark_capacity.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
