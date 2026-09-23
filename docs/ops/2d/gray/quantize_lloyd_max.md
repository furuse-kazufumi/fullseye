---
op: quantize_lloyd_max
dim: 2d
category: gray
in: image
out: image
examples: [gallery2d_gray_arith]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# quantize_lloyd_max — 2D `gray` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "quantize_lloyd_max", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![quantize_lloyd_max: input → output](../../_fig/quantize_lloyd_max.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![quantize_lloyd_max: knob a sweep](../../_fig/quantize_lloyd_max.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![quantize_lloyd_max: knob b sweep](../../_fig/quantize_lloyd_max.b.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![quantize_lloyd_max: other inputs](../../_fig/quantize_lloyd_max.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

入力の分布に合わせた**最適な**量子化(Lloyd–Max、1-D の k-means)。

``a`` が段数のビット数 1〜8、``b`` は反復回数(1〜20)。一様量子化が刻みを等間隔に
置くのに対し、こちらは**画素値が混んでいる所に刻みを細かく置く**。代表値は各区間の
重心、区間の境は隣り合う代表値の中点 —— この 2 つを交互に当てるのが Lloyd の反復で、
**二乗誤差は単調に減る**(増えることはない)。

**一様量子化との差が出る条件**: 入力のヒストグラムが偏っているとき。一様分布を
入れると一様量子化と一致するので、**差が出ないこと自体が正しさの確認になる**。
暗部に画素が集中した画像(影の多い検査画像、蛍光像)では同じビット数で誤差が下がる。

**適用条件**: (1) 出力は入力に依存した代表値の集合なので、**画像ごとに符号表が違う**
—— 別の画像と画素値を直接比べられない(比べたいなら一様量子化)。(2) 空いた区間は
そのまま残る(代表値が動かない)。(3) 反復は局所解に落ちうるが、1-D では初期値を
分位点に取れば実用上安定する。

## 詳しい使い方ガイド

- [gallery2d_gray_arith ファミリ ガイド](../guides/gallery2d_gray_arith.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
quantize_lloyd_max 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_gray_arith](../../../../examples/gallery2d_gray_arith.py) — `py -3.11 examples/gallery2d_gray_arith.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`gray`)

[gamma](gamma.md) · [quantize_uniform](quantize_uniform.md) · [quantization_error](quantization_error.md) · [dither_ordered](dither_ordered.md) · [dither_floyd_steinberg](dither_floyd_steinberg.md) · [companding_mu_law](companding_mu_law.md) · [banding_map](banding_map.md) · [invert](invert.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
