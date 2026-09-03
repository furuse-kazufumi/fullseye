---
op: error_level_map
dim: imgforensics
category: compression
in: image2d
out: image2d
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# error_level_map — IMGFORENSICS `compression` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import imgforensics; imgforensics.error_level_map(image, quality: 'int' = 90, normalize: 'bool' = True) -> 'np.ndarray'` (または `opsimgforensics.get("error_level_map")`)

## 使い方

ELA(誤差レベル解析)。指定品質で **再圧縮した差分**の地図を返す。``image2d``。

Krawetz 2007。JPEG は 8x8 ブロックごとに量子化するので、**一度圧縮された領域**は
同じ品質で再圧縮しても誤差が小さく、**後から貼られた / 描かれた領域**は誤差が
大きく残る、という考え方に基づく。

``normalize=True``(既定)なら最大値で割って [0, 1] にする(見るため)。
``False`` なら 8 bit 階調そのままの絶対誤差(数えるため)。

**Pillow が無ければ :class:`ImportError`。近似には落ちない。** DCT の量子化だけを
numpy で真似ると、符号化器の丸め・色空間変換・チャネル間引きが消えた *別物* に
なる。それを ELA と名乗ると、この族が潰そうとしている「もっともらしく間違う」を
自分でやることになる。

**この地図が言えないこと**(``tests/test_imgforensics.py`` が数で固定。
256x256 の 1/f^1.6 画像の中央 64x64 に別画像を貼ったもの):

==================================== =============== =============== =========
元の画像                             貼付部の ELA    背景の ELA      比
==================================== =============== =============== =========
**無圧縮**(一度も JPEG を通らない)  0.1966          0.1793          **1.096**
一度 JPEG 品質 75 を通した           0.1966          0.0401          **4.898**
==================================== =============== =============== =========

* **無圧縮 PNG では何も言えない**。上の 1.096 倍は「貼った所と貼っていない所が
  区別できない」という意味である。**ELA が意味を持つのは「元が JPEG」のとき
  だけ**で、そのとき初めて 4.898 倍という差になる。
* よく言われる「ELA は高周波を追っているだけ」も、この画像では成り立たない ——
  ELA と Sobel 勾配強度の相関は **0.003**(無圧縮)/ **0.057**(JPEG 済み)。
  ELA は 8x8 ブロックの量子化残差を見ているので、勾配とは別のものを測っている。
  それでも上の表のとおり **無圧縮では改竄を分離しない**。「勾配の言い換えだから
  駄目」なのではなく、**比べる基準になる量子化履歴が無いから駄目**である。
* 平坦な領域は圧縮しても誤差が出ないので、**改竄されていても暗いまま**になる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[perceptual_hash](../hash/perceptual_hash.md) · [fingerprint_correlate](../sensor/fingerprint_correlate.md) · [jpeg_quality_estimate](jpeg_quality_estimate.md) · [jpeg_ghost_map](jpeg_ghost_map.md) · [noise_inconsistency_map](../noise/noise_inconsistency_map.md) · [copy_move_regions](../copy_move/copy_move_regions.md) · [watermark_embed](../watermark/watermark_embed.md) · [watermark_extract](../watermark/watermark_extract.md)

## 同カテゴリ(`compression`)

[jpeg_quality_estimate](jpeg_quality_estimate.md) · [jpeg_ghost_map](jpeg_ghost_map.md) · [jpeg_ghost_quality](jpeg_ghost_quality.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
