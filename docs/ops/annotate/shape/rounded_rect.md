---
op: rounded_rect
dim: annotate
category: shape
in: image2d
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# rounded_rect — ANNOTATE `shape` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.rounded_rect(img, rect, radius=8, color='neutral', width=2, fill=False, alpha=1.0, scheme='okabe_ito')` (実装を直接呼ぶなら `import annotate; annotate.rounded_rect(img, rect, radius=8, color='neutral', width=2, fill=False, alpha=1.0, scheme='okabe_ito')`、台帳から引くなら `opsannotate.get("rounded_rect")`)

## 使い方

角丸の矩形(``fill=True`` で塗り)。下敷きや囲みに使う。

Raises
------
ValueError
    矩形が画像の外、radius が負か辺の半分を超える、alpha が [0,1] の外。

描画: 画素中心から「角を丸めた矩形」までの距離で内側判定し、``fill=False``
なら外周から ``max(1, width)`` px 幅の帯だけを載せる(距離判定の 1 段階、
アンチエイリアスは無し)。合成は ``out = m*color + (1-m)*img`` に ``alpha`` を
掛けたもの。

- ``img``: ``(H, W)`` / ``(H, W, 1|3|4)``。float64 に変換し ``[0, 1]`` にクリップした
  **複製**を返す(入力は変えない)。NaN/Inf は ``ValueError``。
- ``rect``: ``(x, y, w, h)``、x = 列・y = 行。丸めて整数化し、``w, h > 0``、
  画像内に完全に収まること(はみ出しは切り詰めず ``ValueError``)。
  占める画素は ``x .. x+w-1``、``y .. y+h-1``。
- ``radius``: 角の半径 [px]、``0 <= radius <= min(w, h)/2``。0 で普通の矩形。
- ``color``: ``palette`` の役割名(``"neutral"`` 等、``scheme`` で解決)か
  ``[0, 1]`` の RGB。グレー画像には RGB の平均を使う。
- 返り値: 入力と同形の float64。

``text_box`` の下敷きや ``annotate_legend`` の囲みと同じ見た目を手で組むときに。

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

## 型が繋がる次の op(`image2d` を入力に取れる)

[text_box](../text/text_box.md) · [arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md)

## 同カテゴリ(`shape`)

[filled_polygon](filled_polygon.md) · [arc](arc.md) · [ellipse](ellipse.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
