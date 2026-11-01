---
op: ptile_threshold
dim: 2d
category: segmentation
in: image
out: feature
examples: [poc_threshold_transfer_after_normalization]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# ptile_threshold — 2D `segmentation` op

- **データ種**: `image` → `feature`
- **呼び出し**: `fullseye.apply(img, "ptile_threshold", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

面積率で決める P-tile しきい値を feature として返す。

``a`` を ``p = 0.001 + 0.998*a``（CDF の端を除く面積率）、``b < 0.5`` を明側、
それ以外を暗側に写す。Doyle (1962) の順位統計であり、値域の利得・オフセットを
つまみにしない。詳細な ``p`` と極性を名前付きで渡す公開 API は
``fullseye.ledger.ptile_threshold``。

**空入力は分布を持たないため拒否し、しきい値を捏造しない。**

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_threshold_transfer_after_normalization](../../../../examples/poc_threshold_transfer_after_normalization.py) — `py -3.11 examples/poc_threshold_transfer_after_normalization.py`

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md) · [feature_to_img](../bridge/feature_to_img.md)

## 同カテゴリ(`segmentation`)

[threshold](threshold.md) · [sigma_threshold](sigma_threshold.md) · [otsu](otsu.md) · [canny](canny.md) · [adaptive_gauss_thresh](adaptive_gauss_thresh.md) · [sk_otsu](sk_otsu.md) · [sk_li](sk_li.md) · [sk_yen](sk_yen.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
