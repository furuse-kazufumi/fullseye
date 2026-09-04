---
op: text_box
dim: annotate
category: text
in: image2d × text
out: image2d
examples: [annotate_gallery, drawlist_deferred]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# text_box — ANNOTATE `text` op

- **データ種**: `image2d × text` → `image2d`
- **呼び出し**: `import annotate; annotate.text_box(img, text, xy, color='neutral', text_color=None, box_color=None, box_alpha=0.72, anchor='lt', pad=5, font_size=14, min_font_size=9, max_width=None, font_path=None, line_spacing=1.15, scheme='okabe_ito', min_contrast=2.0, border=0, border_color=None, style=None, wrap=True)` (または `opsannotate.get("text_box")`)

## 使い方

下敷き(半透明の板)つきの文字。**はみ出しは黙って切らず例外**。

Parameters
----------
img : ndarray
    ``(H,W)`` か ``(H,W,C)``、float [0,1]。
text : str
    描く文字列。
xy : (x, y)
    アンカーの位置(**x=col, y=row**、row は下向き)。
color : str or sequence
    役割名または RGB。``text_color`` 未指定ならこれが**枠の色**として
    使われ、文字は読みやすい既定色になる。
text_color, box_color : str/sequence or None
    文字色・板の色。None なら既定(明るい文字 × 暗い板)。文字色が None の
    ときは、**実際に下に出る色**に対して明るい既定色が ``min_contrast`` を
    割る場合に限り、暗い文字(板の色)へ自動で切り替える ―― 板なし
    (``box_alpha=0``)で白地に置く目盛り・カラーバー・凡例のラベルが
    白に溶けないため。``text_color`` を明示したときは切り替えない
    (色は図の意味なので勝手に変えず、読めなければ例外にする)。
box_alpha : float
    板の不透明度 [0,1]。``0`` なら板を描かない(目盛りラベル向け)。
anchor : str
    ``'lt','ct','rt','lm','cm','rm','lb','cb','rb'`` の 9 通り。
pad : int
    板の内側余白[px]。
max_width : int or None
    文字の折り返し幅。None なら 1 行のまま。
wrap : bool
    False なら折り返さず 1 行のまま縮めて ``max_width`` に収める。
min_contrast : float
    文字と「実際にその下に出る色」のコントラスト比の下限。下回れば
    **ValueError**(背景と同化した文字は誰も気づけないので通さない)。
    **限界(正直に)**: 比べる相手は板の下の**平均色**なので、
    白と黒が半々に混じった写真の上に ``box_alpha=0`` で置くと、平均は
    中間灰になり検査を通ってしまう(白い部分の上の文字は読めない)。
    地が荒れている場所では ``box_alpha`` を上げて板を効かせること ――
    この検査は「板を忘れた」を捕まえるためのもので、
    「板があっても読めない」まで保証はしない。
border : int
    板の枠線の太さ(0 で枠なし)。色は ``border_color`` か ``color``。
style : dict or None
    枠線を引く :func:`imagedraw.draw_polyline` へ**素通し**する引数。

Returns
-------
ndarray
    同じ shape の新しい配列。

Raises
------
ValueError
    板が画像からはみ出す / 文字が収まらない / コントラスト不足 /
    未知の役割名・アンカー / 負の余白。

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
- [drawlist_deferred](../../../../examples/drawlist_deferred.py) — `py -3.11 examples/drawlist_deferred.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md) · [axes_frame](../plot/axes_frame.md)

## 同カテゴリ(`text`)

[measure_text](measure_text.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
