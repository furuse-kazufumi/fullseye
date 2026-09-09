---
op: hx_rectangle1_domain
dim: 2d
category: halcon_ext
in: image
out: region
halcon: rectangle1_domain
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# hx_rectangle1_domain — 2D `halcon_ext` op

- **データ種**: `image` → `region`
- **呼び出し**: `fullseye.apply(img, "hx_rectangle1_domain", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `rectangle1_domain`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_rectangle1_domain: input → output](../../_fig/hx_rectangle1_domain.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![hx_rectangle1_domain: knob a sweep](../../_fig/hx_rectangle1_domain.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![hx_rectangle1_domain: knob b sweep](../../_fig/hx_rectangle1_domain.b.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![hx_rectangle1_domain: other inputs](../../_fig/hx_rectangle1_domain.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

画像の定義域を軸並行矩形に縮小(中央の a×b の割合)region。

入力 ``v`` と同じ形状で、画像中央に置いた高さ ``hh``・幅 ``ww`` の軸並行矩形を 1 とする 0/1 の float 配列
(region)を返す。入力の中身は見ない。

- ``a`` → 高さの割合 ``hh = int(h * (0.2 + 0.7*a))``(20%〜90%)。
- ``b`` → 幅の割合 ``ww = int(w * (0.2 + 0.7*b))``(20%〜90%)。
- 左上は ``((h-hh)//2, (w-ww)//2)`` で、中央からのずれは整数切り捨てぶんだけ。

画像の周辺(照明落ち・レンズ端)を検査対象から外す ROI を作るのに使う。画像全面が欲しければ ``hx_full_domain``、
既存 region の周辺を削るなら ``hx_clip_region_rel``。

## 詳しい使い方ガイド

- [gallery2d_halcon_ext ファミリ ガイド](../guides/gallery2d_halcon_ext.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
hx_rectangle1_domain 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_halcon_ext](../../../../examples/gallery2d_halcon_ext.py) — `py -3.11 examples/gallery2d_halcon_ext.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`halcon_ext`)

[hx_gen_circle](hx_gen_circle.md) · [hx_gen_ellipse](hx_gen_ellipse.md) · [hx_gen_rectangle2](hx_gen_rectangle2.md) · [hx_gen_checker_region](hx_gen_checker_region.md) · [hx_gen_grid_region](hx_gen_grid_region.md) · [hx_gabor](hx_gabor.md) · [hx_fit_surface1](hx_fit_surface1.md) · [hx_fit_surface2](hx_fit_surface2.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
