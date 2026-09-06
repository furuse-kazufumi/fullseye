---
op: noise_inconsistency_map
dim: imgforensics
category: noise
in: image2d
out: image2d
examples: [image_forensics_audit, poc_forensics_roc]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# noise_inconsistency_map — IMGFORENSICS `noise` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import imgforensics; imgforensics.noise_inconsistency_map(image, block: 'int' = 16) -> 'np.ndarray'` (または `opsimgforensics.get("noise_inconsistency_map")`)

## 使い方

ブロックごとの **雑音標準偏差** を並べた地図。``image2d``。

Immerkær 1996 の 3x3 マスクで高周波成分を取り、``block`` 角の非重複ブロックごとに
``sigma = sqrt(pi/2) / 6 * mean(|conv|)`` を出してブロック定数で戻す。
貼り付けた領域が別の露出・別の圧縮率・別のカメラから来ていれば、この値が
まわりと **段差**になる。

**精度は良い**(``tests/test_imgforensics.py`` が固定)。真の σ が上半分 0.01・
下半分 0.04(8 bit で 2.55 と 10.20、比 4.0)の合成画像で、推定は
**2.533 と 10.214、比 4.033** —— 絶対値も比も 1% 以内。

**この地図が言えないこと**:

* **テクスチャは雑音として数えられる**。Immerkær のマスクはラプラシアン風なので、
  細かい模様の領域は σ が高く出る。実測:**雑音は上下とも同じ σ=0.01** で、
  下半分にだけ市松模様を足した画像では、模様側 15.97 / 平坦側 2.58 = **6.2 倍**。
  段差があっても「改竄」ではなく「模様」かもしれない。
* 逆に **平滑化された改竄は σ が下がる**ので見えるが、平坦な背景に平坦な物を
  貼った場合は差が出ない。
* JPEG は雑音をブロックごとに削るので、圧縮済みの画像では ``block`` を 8 の倍数に
  しないとブロック格子と干渉して縞が出る(既定 16 は 8 の倍数)。
* ★ **画像の縁に、改竄と無関係な段差が必ず出る**(2026-09-06 実測)。
  畳み込みが ``mode="reflect"`` で折り返すため、外周のブロックでは高周波が
  減って σ が低く出る。**改竄ゼロ・一様雑音**の 256x256 で、最外ブロック帯
  8.815 に対し中心 9.537(**-7.6 %**)。同じ画像の生の局所 std は
  0.03491 と 0.03563(-2.0 %)しか違わないので、差の大半は推定器が作っている。
  中央値からの隔たりで見ると最外 0.7173 / 中心 0.5948 = **1.21 倍**。
  画素ごとの ROC を取るとこれだけでゼロ点 AUC が 0.5 から外れる
  (``examples/poc_forensics_roc.py`` の実測で 0.447)。**外周 1 ブロックを
  判定から外す**か、中央値を場所ごとに取ること。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`
- [poc_forensics_roc](../../../../examples/poc_forensics_roc.py) — `py -3.11 examples/poc_forensics_roc.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[perceptual_hash](../hash/perceptual_hash.md) · [fingerprint_correlate](../sensor/fingerprint_correlate.md) · [error_level_map](../compression/error_level_map.md) · [jpeg_quality_estimate](../compression/jpeg_quality_estimate.md) · [jpeg_ghost_map](../compression/jpeg_ghost_map.md) · [copy_move_regions](../copy_move/copy_move_regions.md) · [watermark_embed](../watermark/watermark_embed.md) · [watermark_extract](../watermark/watermark_extract.md)

## 同カテゴリ(`noise`)

—

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
