---
op: intersection
dim: 2d
category: nary
in: region × region
out: region
halcon: intersection
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# intersection — 2D `nary` op

- **データ種**: `region × region` → `region`
- **呼び出し**: 入力 2 枚の op なので `fullseye.apply` では呼べない(あれは 1 画像モデル)。`g = fullseye.FullseyeGraph(); g.add("out", "intersection", ["$in1", "$in2"], a=0.5, b=0.5); g.run({"$in1": img1, "$in2": img2}, terminal="out")` (`$` 始まりが外から渡す入力)
- **HALCON 相当**: `intersection`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

Intersection of two regions.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`nary`)

[add_image](add_image.md) · [sub_image](sub_image.md) · [mult_image](mult_image.md) · [div_image](div_image.md) · [abs_diff_image](abs_diff_image.md) · [max_image](max_image.md) · [min_image](min_image.md) · [bit_and](bit_and.md)

---
*Provenance: imgops_nary.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
