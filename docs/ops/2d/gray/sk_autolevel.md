---
op: sk_autolevel
dim: 2d
category: gray
in: image
out: image
halcon: scale_image_max
examples: [gallery2d_gray_arith]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# sk_autolevel — 2D `gray` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "sk_autolevel", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `scale_image_max`(意味・パラメータは HALCON リファレンスが参考になる)

![sk_autolevel: input → output](../../_fig/sk_autolevel.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![sk_autolevel: knob a sweep](../../_fig/sk_autolevel.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![sk_autolevel: other inputs](../../_fig/sk_autolevel.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

局所オートレベル。各画素周辺の局所ヒストグラムの最小〜最大値を 0〜255 いっぱいに引き伸ばす —— グローバルな階調ではなく場所ごとにコントラストを最大化する適応的なレベル補正。

HALCON の `scale_image_max`(Maximum gray value spreading in the value range 0 to 255.)に相当(近似。HALCON 版は画像全体、こちらは局所窓ごと)。実装は ``filters.rank.autolevel(_u8s(v), disk(1+int(a*3)))`` を 255 で割ったもの —— a は円盤半径を 1〜4 に振る。b は未使用。ほぼ一様な領域ではノイズまで強く引き伸ばされる点に注意。

## 詳しい使い方ガイド

- [gallery2d_gray_arith ファミリ ガイド](../guides/gallery2d_gray_arith.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
sk_autolevel 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_gray_arith](../../../../examples/gallery2d_gray_arith.py) — `py -3.11 examples/gallery2d_gray_arith.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`gray`)

[gamma](gamma.md) · [invert](invert.md) · [scale_clip](scale_clip.md) · [equalize](equalize.md) · [sigmoid](sigmoid.md) · [clahe](clahe.md) · [sk_adapthist](sk_adapthist.md) · [sk_enhance_contrast](sk_enhance_contrast.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
