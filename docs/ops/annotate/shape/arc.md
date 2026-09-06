---
op: arc
dim: annotate
category: shape
in: image2d
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# arc — ANNOTATE `shape` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import annotate; annotate.arc(img, center, radius, start_deg, end_deg, color='neutral', width=2, alpha=1.0, scheme='okabe_ito')` (または `opsannotate.get("arc")`)

## 使い方

円弧。角度は**画面の x 軸から時計回り**(row が下向きだから)で度。

Raises
------
ValueError
    radius が非正、角度が非有限、start == end、alpha が [0,1] の外。

描画: 中心からの距離 ``d`` が ``|d - radius| <= max(0.6, width/2)`` で、かつ
画素の方位角が ``start_deg`` から時計回りに ``(end_deg - start_deg) mod 360`` の
範囲にある画素を塗る(アンチエイリアス無し)。方位角は ``atan2(y - cy, x - cx)``
で、0 度 = 右(+x)、90 度 = 下(+y)、時計回りが正。

- ``center``: ``(x, y)``、x = 列・y = 行。画像外でもよい(はみ出しは切れるだけ)。
- ``radius``: 正 [px]。
- ``start_deg``, ``end_deg``: 度。``start`` から時計回りに ``end`` まで描く。
  差が 360 の倍数(``end - start`` が 0 でなく 360 など)は全周。
  ``start == end`` は「長さ 0」なので ``ValueError``。
- ``width``: 線幅 [px]。``max(0.6, width/2)`` を半幅にするので 1 px 未満でも
  途切れない。
- ``img`` / ``color`` / ``alpha`` / ``scheme`` の扱いは ``rounded_rect`` と同じ
  (float64 複製、``[0, 1]``、役割名か RGB)。
- 返り値: 入力と同形の float64。

角度を書き込む学術図の作法は ``annotate_angle`` が引き出し文字まで面倒を見る。

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

[rounded_rect](rounded_rect.md) · [filled_polygon](filled_polygon.md) · [ellipse](ellipse.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
