---
op: intersection
dim: 2d
category: nary
in: region × region
out: region
halcon: intersection
examples: [gallery_nary_image_algebra, poc_connectome_across_decades, poc_connectome_across_worms, poc_driving_crossing, poc_driving_japan_town, poc_driving_pass, poc_driving_school, poc_driving_town, poc_worm_neurites_grow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# intersection — 2D `nary` op

- **データ種**: `region × region` → `region`
- **呼び出し**: 入力 2 枚の op なので `fullseye.apply` では呼べない(あれは 1 画像モデル)。`g = fullseye.FullseyeGraph(); g.add("out", "intersection", ["$in1", "$in2"], a=0.5, b=0.5); g.run({"$in1": img1, "$in2": img2}, terminal="out")` (`$` 始まりが外から渡す入力)
- **HALCON 相当**: `intersection`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

2 つの領域の積(両方に入る画素)。HALCON の ``intersection`` に相当。入力は ``> 0.5`` で二値化する。``a``, ``b`` は未使用。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery_nary_image_algebra](../../../../examples/gallery_nary_image_algebra.py) — `py -3.11 examples/gallery_nary_image_algebra.py`
- [poc_connectome_across_decades](../../../../examples/poc_connectome_across_decades.py) — `py -3.11 examples/poc_connectome_across_decades.py`
- [poc_connectome_across_worms](../../../../examples/poc_connectome_across_worms.py) — `py -3.11 examples/poc_connectome_across_worms.py`
- [poc_driving_crossing](../../../../examples/poc_driving_crossing.py) — `py -3.11 examples/poc_driving_crossing.py`
- [poc_driving_japan_town](../../../../examples/poc_driving_japan_town.py) — `py -3.11 examples/poc_driving_japan_town.py`
- [poc_driving_pass](../../../../examples/poc_driving_pass.py) — `py -3.11 examples/poc_driving_pass.py`
- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`
- [poc_driving_town](../../../../examples/poc_driving_town.py) — `py -3.11 examples/poc_driving_town.py`
- [poc_worm_neurites_grow](../../../../examples/poc_worm_neurites_grow.py) — `py -3.11 examples/poc_worm_neurites_grow.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`nary`)

[add_image](add_image.md) · [sub_image](sub_image.md) · [mult_image](mult_image.md) · [div_image](div_image.md) · [abs_diff_image](abs_diff_image.md) · [max_image](max_image.md) · [min_image](min_image.md) · [bit_and](bit_and.md)

---
*Provenance: imgops_nary.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
