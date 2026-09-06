---
op: invert
dim: 2d
category: gray
in: image
out: image
halcon: invert_image
examples: [gallery2d_gray_arith]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# invert — 2D `gray` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "invert", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `invert_image`(意味・パラメータは HALCON リファレンスが参考になる)

![invert: input → output](../../_fig/invert.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![invert: other inputs](../../_fig/invert.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

階調反転（ネガポジ反転）。HALCON の ``invert_image``（Invert an image.）に相当。

``1 - clip(v,0,1)`` を返すだけ。``a``, ``b`` は未使用。

- 入力を先に [0,1] へ clip してから反転するので、範囲外の値は**飽和してから**反転される(1.3 → 0、-0.2 → 1)。値域が [0,1] でない配列は前段で正規化しておくこと。
- 返り値は入力と同形の float、値域 [0,1]。NaN は clip を素通りして NaN のまま返る(``ops.py`` 直登録の op なので backend の guard は掛からない —— 非有限を止めたいなら ``fullseye.apply`` 経由で ``on_error="raise"``)。
- 2 回掛けると元に戻る(対合)。region に掛ければ前景/背景が入れ替わるが、region 用には ``invert_region``(補集合)がある。
- 使いどころ: 暗い対象を ``threshold`` で「明るい側」として拾う前の反転、``dc_rpca_sparse`` の暗い残差や ``xpil_contour`` の黒い線を正の信号にする、距離変換の「内側ほど暗い」を「内側ほど明るい」に読み替える。

## 詳しい使い方ガイド

- [gallery2d_gray_arith ファミリ ガイド](../guides/gallery2d_gray_arith.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
invert 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_gray_arith](../../../../examples/gallery2d_gray_arith.py) — `py -3.11 examples/gallery2d_gray_arith.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`gray`)

[gamma](gamma.md) · [scale_clip](scale_clip.md) · [equalize](equalize.md) · [sigmoid](sigmoid.md) · [clahe](clahe.md) · [sk_adapthist](sk_adapthist.md) · [sk_enhance_contrast](sk_enhance_contrast.md) · [sk_autolevel](sk_autolevel.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
