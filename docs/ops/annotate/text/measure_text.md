---
op: measure_text
dim: annotate
category: text
in: text
out: table
examples: [annotate_gallery, annotate_paper_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# measure_text — ANNOTATE `text` op

- **データ種**: `text` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.measure_text(text, font_size=14, font_path=None, max_width=None, min_font_size=9, line_spacing=1.15, wrap=True, bold=False, italic=False)` (実装を直接呼ぶなら `import annotate; annotate.measure_text(text, font_size=14, font_path=None, max_width=None, min_font_size=9, line_spacing=1.15, wrap=True, bold=False, italic=False)`、台帳から引くなら `opsannotate.get("measure_text")`)

## 使い方

文字を**描く前に**測る。収まらないなら折り返すか縮め、駄目なら例外。

Parameters
----------
text : str
    測る文字列(``\n`` で改行)。
font_size : int
    希望のサイズ。``max_width`` に入らなければ 1pt ずつ縮める。
font_path : str or None
    明示すると機械をまたいでも同じ結果になる。None は :data:`FONT_CANDIDATES`
    を固定順で探す。
max_width : int or None
    入れたい幅[px]。None なら縮小も折り返しもしない。
min_font_size : int
    ここまで縮めても入らなければ **ValueError**(黙って切らない)。
line_spacing : float
    行送り係数。
bold, italic : bool or int
    **合成**の太字・斜体(:func:`_bold_px` / :func:`_italic_tile`)。本物の
    Bold / Italic 書体ではないので字形は違う ―― 本物が要るときは
    ``font_path`` にその書体のファイルを渡すこと。``bold`` に整数を渡すと
    重ね打ちの回数を直に指定できる。**太さと傾きのぶんは ``width`` に入る**
    ので、板や表の桁はそのまま広がる(重ね打ちは横にだけ太るので
    ``height`` は変わらない)。
wrap : bool
    True(既定)なら ``max_width`` で**折り返す**。False なら折り返さず
    **行を増やさずフォントを縮めて**収める(格子のラベルのように、2 行に
    なると版が崩れる場所で使う ―― ``exhibit_tile._fit_label`` と同じ流儀)。
    どちらでも ``min_font_size`` まで来て入らなければ例外。
    ``\n`` の改行は ``max_width`` の有無・``wrap`` の値に**よらず常に**効く
    (幅を与えないと 1 行に潰れる、という事故は起きない)。

Returns
-------
dict
    ``{"lines", "font", "font_size", "width", "height", "line_height"}``。
    ``width``/``height`` は実測[px]。

Raises
------
ValueError
    ``max_width`` が非正 / ``min_font_size`` まで縮めても 1 行が入らない。

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [dataset_conventions](../guides/dataset_conventions.md) — 学習データセット規約の知識 — COCO / YOLO / VOC と外観検査での落とし穴

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate_gallery](../../../../examples/annotate_gallery.py) — `py -3.11 examples/annotate_gallery.py`
- [annotate_paper_tour](../../../../examples/annotate_paper_tour.py) — `py -3.11 examples/annotate_paper_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`text`)

[text_box](text_box.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
