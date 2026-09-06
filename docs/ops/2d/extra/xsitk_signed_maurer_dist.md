---
op: xsitk_signed_maurer_dist
dim: 2d
category: extra
in: region
out: image
examples: [gallery2d_color_artistic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# xsitk_signed_maurer_dist — 2D `extra` op

- **データ種**: `region` → `image`
- **呼び出し**: `fullseye.apply(img, "xsitk_signed_maurer_dist", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![xsitk_signed_maurer_dist: input → output](../../_fig/xsitk_signed_maurer_dist.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*出力は viridis 風の疑似カラー(暗い紫 = 小、黄 = 大)。距離・位相・向き・深度のような「量の場」を読むため。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![xsitk_signed_maurer_dist: knob a sweep](../../_fig/xsitk_signed_maurer_dist.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![xsitk_signed_maurer_dist: stages](../../_fig/xsitk_signed_maurer_dist.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![xsitk_signed_maurer_dist: other inputs](../../_fig/xsitk_signed_maurer_dist.inputs.jpg)

## 使い方

符号付き距離マップ(SimpleITK ``SignedMaurerDistanceMap``)を tanh で [0,1] に押し込んだもの。二値領域の境界からの距離(内側/外側とも)を、境界付近ほど 0.5 から離れる連続値の画像として表す。

``a`` は tanh のスケール(``1.0+9.0*a`` で 1〜10。大きいほど遷移が緩やかで広い範囲がグレーになる)を振る。``b`` は未使用。距離を画素座標のスケールで解釈する点、符号(内側/外側どちらが正か)は SimpleITK のデフォルト規約に従う点に注意。

## 詳しい使い方ガイド

- [gallery2d_color_artistic ファミリ ガイド](../guides/gallery2d_color_artistic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
threshold 0.50 0.50
xsitk_signed_maurer_dist 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_color_artistic](../../../../examples/gallery2d_color_artistic.py) — `py -3.11 examples/gallery2d_color_artistic.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`extra`)

[xsitk_curvature_flow](xsitk_curvature_flow.md) · [xsitk_minmax_curv_flow](xsitk_minmax_curv_flow.md) · [xsitk_curv_aniso_diff](xsitk_curv_aniso_diff.md) · [xsitk_laplacian_sharpen](xsitk_laplacian_sharpen.md) · [xsitk_grayscale_fillhole](xsitk_grayscale_fillhole.md) · [xsitk_grayscale_grindpeak](xsitk_grayscale_grindpeak.md) · [xsitk_opening_by_recon](xsitk_opening_by_recon.md) · [xsitk_closing_by_recon](xsitk_closing_by_recon.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
