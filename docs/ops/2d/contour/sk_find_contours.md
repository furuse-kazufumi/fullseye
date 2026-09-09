---
op: sk_find_contours
dim: 2d
category: contour
in: image
out: contour
examples: [gallery2d_contour_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# sk_find_contours — 2D `contour` op

- **データ種**: `image` → `contour`
- **呼び出し**: `fullseye.apply(img, "sk_find_contours", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![sk_find_contours: input → output](../../_fig/sk_find_contours.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![sk_find_contours: knob a sweep](../../_fig/sk_find_contours.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![sk_find_contours: other inputs](../../_fig/sk_find_contours.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

等高線抽出(marching squares)。グレースケール画像上で指定したレベル値と交差する曲線を辿り、サブピクセル精度の輪郭座標列の集合として返す —— 二値画像の外周だけでなく、連続値の等高線も扱える点が二値輪郭抽出と違う。

HALCON に直接対応するものは無い(空欄)。実装は ``measure.find_contours(v, level=0.2+0.5*a)`` のうち頂点数 3 未満の断片を捨てたもの —— a は等高線のレベル(しきい値)を 0.2〜0.7 に振る。b は未使用。戻り値は画像形状と輪郭座標配列のリストを持つ辞書(``contour`` 型)。

## 詳しい使い方ガイド

- [gallery2d_contour_measure ファミリ ガイド](../guides/gallery2d_contour_measure.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
sk_find_contours 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_contour_measure](../../../../examples/gallery2d_contour_measure.py) — `py -3.11 examples/gallery2d_contour_measure.py`

## 型が繋がる次の op(`contour` を入力に取れる)

[identity](../misc/identity.md) · [select_contours](select_contours.md) · [smooth_contours](smooth_contours.md) · [fit_line_contours](fit_line_contours.md) · [contours_to_region](contours_to_region.md) · [count_contours](../features/count_contours.md) · [total_length](../features/total_length.md) · [select_contours_xld](select_contours_xld.md)

## 同カテゴリ(`contour`)

[select_contours](select_contours.md) · [smooth_contours](smooth_contours.md) · [fit_line_contours](fit_line_contours.md) · [contours_to_region](contours_to_region.md) · [edges_sub_pix](edges_sub_pix.md) · [lines_gauss](lines_gauss.md) · [select_contours_xld](select_contours_xld.md) · [smooth_contours_xld](smooth_contours_xld.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
