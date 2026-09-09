---
op: add_noise_white
dim: 2d
category: noise
in: image
out: image
halcon: add_noise_white
examples: [gallery2d_smoothing_rank]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# add_noise_white — 2D `noise` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "add_noise_white", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `add_noise_white`(意味・パラメータは HALCON リファレンスが参考になる)

![add_noise_white: input → output](../../_fig/add_noise_white.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![add_noise_white: knob a sweep](../../_fig/add_noise_white.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![add_noise_white: knob b sweep](../../_fig/add_noise_white.b.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![add_noise_white: other inputs](../../_fig/add_noise_white.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

ガウス性ホワイトノイズを加える(``np.random.default_rng`` で生成、
標準偏差 ``0.02+0.2*b``)。乱数シードは ``int(a*997)+7`` で ``a`` から
決定的に導出されるため、**同じ ``a`` なら常に同じノイズパターンが再現
される**(真にランダムではなく、``a`` を「ノイズの見え方の型」を選ぶ
擬似的なノブとして使っている点に注意)。HALCON の ``add_noise_white``
（Add noise to an image.）に相当。

``a`` は乱数シード(=ノイズパターン)を、``b`` はノイズの強さ(標準偏差)
を振る。両方が使われるが、``a`` の意味は「強さ」ではなく「パターン」で
ある点が他の op と異なる。

## 詳しい使い方ガイド

- [gallery2d_smoothing_rank ファミリ ガイド](../guides/gallery2d_smoothing_rank.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [mv_image_sensors](../../optics/guides/mv_image_sensors.md) — 産業用イメージセンサ（現行品中心）

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
add_noise_white 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_smoothing_rank](../../../../examples/gallery2d_smoothing_rank.py) — `py -3.11 examples/gallery2d_smoothing_rank.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`noise`)

[add_noise_distribution](add_noise_distribution.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
