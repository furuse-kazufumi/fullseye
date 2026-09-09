---
op: mult_image
dim: 2d
category: nary
in: image × image
out: image
halcon: mult_image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# mult_image — 2D `nary` op

- **データ種**: `image × image` → `image`
- **呼び出し**: `fullseye.apply(img, "mult_image", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `mult_image`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

Multiply two images.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`nary`)

[add_image](add_image.md) · [sub_image](sub_image.md) · [div_image](div_image.md) · [abs_diff_image](abs_diff_image.md) · [max_image](max_image.md) · [min_image](min_image.md) · [bit_and](bit_and.md) · [bit_or](bit_or.md)

---
*Provenance: imgops_nary.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
