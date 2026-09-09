---
op: max_image
dim: 2d
category: nary
in: image × image
out: image
halcon: max_image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# max_image — 2D `nary` op

- **データ種**: `image × image` → `image`
- **呼び出し**: 入力 2 枚の op なので `fullseye.apply` では呼べない。`g = fullseye.FullseyeGraph(); g.add("out", "max_image", ["in1", "in2"][:2], a=0.5, b=0.5)` (実装は `import imgops_nary; {o.name: o for o in imgops_nary.build_nary()}["max_image"].fn(inputs, a, b)`)
- **HALCON 相当**: `max_image`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

Pixelwise maximum of two images.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`nary`)

[add_image](add_image.md) · [sub_image](sub_image.md) · [mult_image](mult_image.md) · [div_image](div_image.md) · [abs_diff_image](abs_diff_image.md) · [min_image](min_image.md) · [bit_and](bit_and.md) · [bit_or](bit_or.md)

---
*Provenance: imgops_nary.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
