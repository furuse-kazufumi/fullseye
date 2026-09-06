---
op: hx_histo_to_thresh
dim: 2d
category: halcon_ext
in: image
out: region
halcon: histo_to_thresh
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# hx_histo_to_thresh — 2D `halcon_ext` op

- **データ種**: `image` → `region`
- **呼び出し**: `fullseye.apply(img, "hx_histo_to_thresh", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `histo_to_thresh`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_histo_to_thresh: input → output](../../_fig/hx_histo_to_thresh.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![hx_histo_to_thresh: other inputs](../../_fig/hx_histo_to_thresh.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

ヒストグラムの谷から閾値を決めて二値化(Otsu の分散基準でなく谷検出=別 op)。

``v`` の 64 bin ヒストグラム(範囲 [0,1])を σ=1.5 のガウスで平滑化し、最も高い bin ``p1`` と、``p1`` から 5 bin
以上離れた中で次に高い bin ``p2`` を取り、その間で最小の bin(谷)の左端の値をしきい値 ``thr`` にして
``v > thr`` を 1 とする 0/1 の float region を返す。

- ``a``, ``b`` は未使用(しきい値は完全に自動)。
- ``p2`` が見つからない(5 bin 以上離れた bin が無い)ときは ``lo == hi`` となり谷を bin 32、つまり ``thr = 0.5``
に固定する。

注意: ``p2`` は「2 番目のモード」ではなく「p1 から 5 bin 以上離れた 2 番目に高い bin」なので、単峰の裾でも選ばれる。
その場合の谷はピークと裾の間の最小値になり、意図と違う位置で切れる(単峰のガウス雑音画像で大半が前景になる
実測あり)。双峰性がはっきりした画像向け。分散基準で決めたいときは ``otsu``、局所的なら ``dyn_threshold``。

## 詳しい使い方ガイド

- [gallery2d_halcon_ext ファミリ ガイド](../guides/gallery2d_halcon_ext.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
hx_histo_to_thresh 0.50 0.50
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
