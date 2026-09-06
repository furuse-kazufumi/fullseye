---
op: ellipse
dim: annotate
category: shape
in: image2d
out: image2d
examples: [annotate_gallery, poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# ellipse — ANNOTATE `shape` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import annotate; annotate.ellipse(img, center, radii, angle_deg=0.0, color='neutral', width=2, fill=False, alpha=1.0, scheme='okabe_ito')` (または `opsannotate.get("ellipse")`)

## 使い方

楕円(``angle_deg`` で回転、``fill=True`` で塗り)。

Raises
------
ValueError
    半径が非正、非有限、alpha が [0,1] の外。

描画: 画素を ``angle_deg`` だけ回した局所座標 ``(u, v)`` に写し、
``q = (u/ra)^2 + (v/rb)^2`` で判定する。``fill=True`` は ``q <= 1``、
``fill=False`` は ``|sqrt(q) - 1| <= max(1, width) / (2 min(ra, rb))`` の帯
(アンチエイリアス無し)。帯の幅を**短軸で正規化**しているので、扁平な楕円では
長軸の端ほど線が太く見える(近似)。

- ``center``: ``(x, y)``、x = 列・y = 行。画像外でもよい。
- ``radii``: ``(ra, rb)`` [px]。``ra`` が ``angle_deg`` 方向、``rb`` がその直交方向。
  両方とも正。
- ``angle_deg``: 回転角 [度]。x 軸から時計回り(画面座標、y が下向き)。
- ``width``: 線幅 [px] (``fill=False`` のとき)。
- ``img`` / ``color`` / ``alpha`` / ``scheme`` の扱いは ``rounded_rect`` と同じ
  (float64 複製、``[0, 1]``、役割名か RGB)。
- 返り値: 入力と同形の float64。

``ra == rb`` なら円。計測結果(楕円フィットの ``row, col, phi, ra, rb``)を
重ねるときは ``center=(col, row)``、``angle_deg=degrees(phi)`` に読み替える。

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
- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[text_box](../text/text_box.md) · [arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md)

## 同カテゴリ(`shape`)

[rounded_rect](rounded_rect.md) · [filled_polygon](filled_polygon.md) · [arc](arc.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
