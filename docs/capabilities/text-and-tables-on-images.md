---
id: text-and-tables-on-images
title: 画像の上に、文字と表を置きたい場所へ置く
title_en: Put text and tables exactly where you want them on an image
category: 見せる
ops: [text_box, annotate_text_path, annotate_text_path_layout, annotate_table, annotate_table_layout, measure_text]
examples: [annotate_paper_tour]
version: 0.1.11
---

# 画像の上に、文字と表を置きたい場所へ置く

## できること

検査画像や解析結果に、**位置を指定して**文字を焼き込めます。`text_box` は 9 方向のアンカー・半透明の板・折り返し、`annotate_text_path` は折れ線に沿った配置で、**斜め**(接線角に 1 字ずつ回す)・**縦書き**(`upright=True`)・**改行**(`\n`)・経路に沿ったそろえ(`anchor="start"/"center"/"end"`)・線に触れさせない**法線オフセット**が使えます。字は色(役割名または RGB)に加えて、合成の **Bold / Italic** も指定できます。

`annotate_table` はタブ区切りの文字列をそのまま**表**にします。桁幅は指定されたサイズの**実フォントで 1 セルずつ測った最大**で、桁間の既定は行高の 0.6 倍 —— `font_size` を変えれば間隔も一緒に動きます。数に見える桁だけ自動で右そろえになり、板は既定で半透明です。

**描く前に測れる**のがこの層の設計で、`measure_text` / `annotate_text_path_layout` / `annotate_table_layout` は幾何だけを返します。置き場所を数字で検算してから描けます。

## What it does

Place text on an image where you actually want it: nine-way anchors, translucent plates, wrapping, and — along a polyline — slanted, vertical (`upright=True`), multi-line (`\n`), start/centre/end alignment and a perpendicular offset. Colour, plus synthetic bold and italic. `annotate_table` turns a tab-separated string into a table whose column widths are **measured with the real font at the requested size**, with a font-size-proportional column gap, automatic right-alignment for numeric columns and a translucent plate. Every one has a `*_layout` twin that returns the geometry so you can check the placement before drawing.

## 向くところ / 向かないところ

**向く**: 測定値の焼き込み、ROI の名札、経路や輪郭に沿った注記、結果の表をそのまま図に載せること。

**向かない**: ★**本文組版ではありません**。縦書きは短い注記のための実装で、句読点の右上寄せ・小書き仮名の位置補正・縦中横はやりません(近似せず、できないことを docstring に書いてあります)。★Bold / Italic は**合成**(輪郭を太らせる / せん断)なので、本物の Bold 書体とは字形が違います。本物が要るときは `font_path` にその書体のファイルを渡してください。★はみ出しは**黙って切らず例外**にします。図から切れた文字は機械では気づけないためで、これは仕様です。★表の行で桁数がそろっていないと例外になります(黙って埋めると数字が隣の見出しの下に並びます)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

img = np.zeros((140, 320, 3))
img = fs.annotate_table(img, "項目\t実測\t予測\n面積\t12.50\t12.48\n周長\t9.75\t9.80",
                        (10, 10), header=True)          # 桁幅は実フォントで実測
img = fs.annotate_text_path(img, "along the edge", [(12.0, 128.0), (300.0, 100.0)],
                            font_size=13, anchor="center", offset=-8.0, italic=True)
print('図', np.asarray(img).shape)
```

## 裏づけ

- op: `text_box` / `annotate_text_path`(+ `_layout`)/ `annotate_table`(+ `_layout`)/ `measure_text`
- 例: [`annotate_paper_tour`](../../examples/annotate_paper_tour.py)(節 1-3 が経路の閉形式、節 7 が桁幅と桁間)
- 試験: `tests/test_annotate_text_path2.py`(アンカー / 縦書き / 改行)、`tests/test_annotate_bold_italic.py`(合成字体)、`tests/test_annotate_table.py`(桁幅・そろえ・半透明)
