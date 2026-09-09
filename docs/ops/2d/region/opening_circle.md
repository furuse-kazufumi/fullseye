---
op: opening_circle
dim: 2d
category: region
in: region
out: region
halcon: opening_circle
examples: [gallery2d_region, poc_bone_trabecular_thickness, poc_change_detection_misreg, poc_document_scan]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# opening_circle — 2D `region` op

- **データ種**: `region` → `region`
- **呼び出し**: `fullseye.apply(img, "opening_circle", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `opening_circle`(意味・パラメータは HALCON リファレンスが参考になる)

![opening_circle: input → output](../../_fig/opening_circle.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![opening_circle: knob a sweep](../../_fig/opening_circle.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![opening_circle: stages](../../_fig/opening_circle.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![opening_circle: other inputs](../../_fig/opening_circle.inputs.jpg)

## 使い方

円盤形構造要素による二値オープニング(収縮の後に膨張)。小さな突起や
細い連結部を除去しつつ、大まかな形状は保つ。HALCON の
``opening_circle``（Open a region with a circular structuring element.）
に相当。

``a`` が構造要素の半径を 1〜4 の範囲で振る。``b`` は未使用。

## 詳しい使い方ガイド

- [gallery2d_region ファミリ ガイド](../guides/gallery2d_region.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
threshold 0.50 0.50
opening_circle 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_region](../../../../examples/gallery2d_region.py) — `py -3.11 examples/gallery2d_region.py`
- [poc_bone_trabecular_thickness](../../../../examples/poc_bone_trabecular_thickness.py) — `py -3.11 examples/poc_bone_trabecular_thickness.py`
- [poc_change_detection_misreg](../../../../examples/poc_change_detection_misreg.py) — `py -3.11 examples/poc_change_detection_misreg.py`
- [poc_document_scan](../../../../examples/poc_document_scan.py) — `py -3.11 examples/poc_document_scan.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](reg_erode.md) · [reg_dilate](reg_dilate.md) · [reg_open](reg_open.md) · [reg_close](reg_close.md) · [fill_holes](fill_holes.md) · [select_largest](select_largest.md) · [remove_small](remove_small.md)

## 同カテゴリ(`region`)

[reg_erode](reg_erode.md) · [reg_dilate](reg_dilate.md) · [reg_open](reg_open.md) · [reg_close](reg_close.md) · [fill_holes](fill_holes.md) · [select_largest](select_largest.md) · [remove_small](remove_small.md) · [invert_region](invert_region.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
