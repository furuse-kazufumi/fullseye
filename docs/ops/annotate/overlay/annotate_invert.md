---
op: annotate_invert
dim: annotate
category: overlay
in: image2d × mask
out: image2d
examples: [annotate_paper_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# annotate_invert — ANNOTATE `overlay` op

- **データ種**: `image2d × mask` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.annotate_invert(img, mask, draw='fill', width=1.5, mode='complement', alpha=1.0, bits=128, min_contrast=1.5, on_invisible='warn')` (実装を直接呼ぶなら `import annotate; annotate.annotate_invert(img, mask, draw='fill', width=1.5, mode='complement', alpha=1.0, bits=128, min_contrast=1.5, on_invisible='warn')`、台帳から引くなら `opsannotate.get("annotate_invert")`)

## 使い方

領域(region)を**反転色**で塗る/縁取る。

「地が明るいか暗いか判らないので、どちらでも見える色で描きたい」という
ときの古典手。塗り色を決めずに済むかわりに、**中間調で消える**ので
:func:`annotate_invert_visibility` の測定を内側で必ず通す。

★**地がモノクロ(グレー)なら、まず彩度のある色を検討すること**。灰色には
彩度が無いので、彩度のある色はどの階調とも**色相で**区別がつく —— 反転色
より確実で、しかも「これは重ねた線だ」と一目で判る
(:func:`annotate_outline` / :func:`overlay_mask` に役割色を渡す)。
反転色が本領を発揮するのは、地がカラーで**どの色を選んでも衝突しうる**とき。
なお :func:`annotate_invert_visibility` が測るのは WCAG の**輝度**比なので、
「輝度は同じだが色相が違う」ような見え方は評価できない —— 色で描くなら、
この op の数字は当てにしないこと。

Parameters
----------
mask : (H,W)
    領域。真偽か [0,1] の重み。**画像と形が違えば例外**。
draw : {"fill", "margin"}
    HALCON の ``set_draw`` と同じ語。``"fill"`` は中身ごと、``"margin"``
    は**輪郭だけ**を反転する。輪郭は太さ ``width`` 画素(整数に丸める)の
    帯で、領域の内外へ半分ずつ広がる。
width : float
    ``draw="margin"`` のときの帯の太さ(画素)。
mode : str
    :data:`INVERT_MODES`。``"complement"`` は地の模様を残し、``"xor"`` は
    模様を残したまま消えないことを保証し、``"contrast"`` は白黒に倒して
    見えることを保証する。
bits : int
    ``mode="xor"`` の bit マスク(1..255)。既定 ``0x80`` は最上位 bit だけを
    反転する ―― **必ず 128 階調跳ぶので消えない**。``0xFF`` にすると
    ``complement`` と同じ(崖ごと同じ)、``0x0F`` のような下位だけの
    マスクは**どの階調でも見えない**(実測: 全 256 階調で比 1.5 未満)。
alpha : float
    反転の効き。1.0 で完全に反転、0.5 なら地と反転色の中間
    (**``mode="complement"`` の 0.5 は必ず中間調になる** —— 反転色を
    半分にすると消えるのは道理なので、警告はそれを拾う)。
min_contrast, on_invisible :
    見えないと判ったときの扱い。``"warn"``(既定)/ ``"raise"``(fail-closed)
    / ``"ignore"``。

Returns
-------
(H,W[,C]) float64
    反転を乗せた複製。**入力は書き換えない**。

Raises
------
ValueError
    形の不一致 / 値域外 / 未知の ``draw`` ``mode`` ``on_invisible`` /
    ``on_invisible="raise"`` で不可視。

Examples
--------
>>> import numpy as np, annotate
>>> img = np.zeros((16, 16)); img[4:12, 4:12] = 1.0
>>> m = np.zeros((16, 16), bool); m[6:10, 6:10] = True
>>> out = annotate.annotate_invert(img, m)
>>> float(out[7, 7]), float(out[1, 1])
(0.0, 0.0)
>>> ring = annotate.annotate_invert(img, m, draw="margin", width=1)
>>> float(ring[7, 7])                      # 中身は触らない
1.0

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [dataset_conventions](../guides/dataset_conventions.md) — 学習データセット規約の知識 — COCO / YOLO / VOC と外観検査での落とし穴

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate_paper_tour](../../../../examples/annotate_paper_tour.py) — `py -3.11 examples/annotate_paper_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[text_box](../text/text_box.md) · [arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md)

## 同カテゴリ(`overlay`)

[overlay_mask](overlay_mask.md) · [overlay_labels](overlay_labels.md) · [annotate_invert_visibility](annotate_invert_visibility.md) · [annotate_invert_path](annotate_invert_path.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
