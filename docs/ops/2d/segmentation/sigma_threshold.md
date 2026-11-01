---
op: sigma_threshold
dim: 2d
category: segmentation
in: image
out: region
examples: [poc_threshold_transfer_after_normalization]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# sigma_threshold — 2D `segmentation` op

- **データ種**: `image` → `region`
- **呼び出し**: `fullseye.apply(img, "sigma_threshold", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

零中心・σ単位の画像を ``k = 2 + 3*a`` で二値化する。

``b`` の 3 帯が明側 ``x>k`` / 暗側 ``x<-k`` / 両側 ``|x|>k``。この 2-D
レジストリ版は入力が標準化済みであることを前提とし、生画像からなら先に
``image_standardize`` をつなぐ。名前付き API は内部で頑健標準化する選択肢も持つ。

**空入力は σ単位を検査できないため拒否し、空 region へ黙って落とさない。**

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_threshold_transfer_after_normalization](../../../../examples/poc_threshold_transfer_after_normalization.py) — `py -3.11 examples/poc_threshold_transfer_after_normalization.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`segmentation`)

[threshold](threshold.md) · [ptile_threshold](ptile_threshold.md) · [otsu](otsu.md) · [canny](canny.md) · [adaptive_gauss_thresh](adaptive_gauss_thresh.md) · [sk_otsu](sk_otsu.md) · [sk_li](sk_li.md) · [sk_yen](sk_yen.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
