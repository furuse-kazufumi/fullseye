---
op: hx_gen_bandfilter
dim: 2d
category: halcon_ext
in: image
out: image
halcon: gen_bandfilter
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# hx_gen_bandfilter — 2D `halcon_ext` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "hx_gen_bandfilter", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `gen_bandfilter`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_gen_bandfilter: input → output](../../_fig/hx_gen_bandfilter.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![hx_gen_bandfilter: knob a sweep](../../_fig/hx_gen_bandfilter.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![hx_gen_bandfilter: knob b sweep](../../_fig/hx_gen_bandfilter.b.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![hx_gen_bandfilter: other inputs](../../_fig/hx_gen_bandfilter.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

理想バンドフィルタ画像(周波数円環、中心半径 a・幅 b)。gen_bandpass と別 operator。

``hx_gen_lowpass`` と同じ ``fftshift`` 済の正規化周波数半径 ``r``(中心=DC)に対し
``c - half <= r <= c + half`` の円環を 1 とする 0/1 の float 画像(周波数領域マスク)を返す。入力 ``v`` は
形状の取得にのみ使う。

- ``a`` → 円環の中心半径 ``c = 0.05 + 0.4*a``(0.05〜0.45)。
- ``b`` → 半幅 ``half = 0.03 + 0.15*b``(0.03〜0.18)。内半径 ``c - half`` が負になる組み合わせ(小さい a と
大きい b)では DC を含む円板になり、実質ローパスになる。

``hx_gen_bandpass`` が「内半径と幅」なのに対し、こちらは「中心と半幅」で同じ円環を指定する。特定の空間周波数
(縞の周期 ``1/c`` 画素)だけを抜き出すマスクを作り、``fft_generic`` などの中心=DC スペクトルと画素積で使う。

## 詳しい使い方ガイド

- [gallery2d_halcon_ext ファミリ ガイド](../guides/gallery2d_halcon_ext.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
hx_gen_bandfilter 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_halcon_ext](../../../../examples/gallery2d_halcon_ext.py) — `py -3.11 examples/gallery2d_halcon_ext.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`halcon_ext`)

[hx_gen_circle](hx_gen_circle.md) · [hx_gen_ellipse](hx_gen_ellipse.md) · [hx_gen_rectangle2](hx_gen_rectangle2.md) · [hx_gen_checker_region](hx_gen_checker_region.md) · [hx_gen_grid_region](hx_gen_grid_region.md) · [hx_gabor](hx_gabor.md) · [hx_fit_surface1](hx_fit_surface1.md) · [hx_fit_surface2](hx_fit_surface2.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
