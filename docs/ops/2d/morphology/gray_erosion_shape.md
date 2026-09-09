---
op: gray_erosion_shape
dim: 2d
category: morphology
in: image
out: image
halcon: gray_erosion_shape
examples: [gallery2d_morphology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# gray_erosion_shape — 2D `morphology` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "gray_erosion_shape", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `gray_erosion_shape`(意味・パラメータは HALCON リファレンスが参考になる)

![gray_erosion_shape: input → output](../../_fig/gray_erosion_shape.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![gray_erosion_shape: knob a sweep](../../_fig/gray_erosion_shape.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![gray_erosion_shape: other inputs](../../_fig/gray_erosion_shape.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

円形（disk, 半径 ``_rad(a)``=1〜4）構造要素によるグレースケール収縮（gray erosion）—— 窓内の最小値に置き換える。b は未使用。

HALCON の ``gray_erosion_shape``（円・矩形など任意形状のマスクで窓内最小のグレー値を求める演算）に相当。矩形版は ``gray_erosion_rect`` が担当する。

## 詳しい使い方ガイド

- [gallery2d_morphology ファミリ ガイド](../guides/gallery2d_morphology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
gray_erosion_shape 0.35 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_morphology](../../../../examples/gallery2d_morphology.py) — `py -3.11 examples/gallery2d_morphology.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`morphology`)

[gerode](gerode.md) · [gdilate](gdilate.md) · [gopen](gopen.md) · [gclose](gclose.md) · [tophat](tophat.md) · [bothat](bothat.md) · [morph_grad](morph_grad.md) · [sk_area_opening](sk_area_opening.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
