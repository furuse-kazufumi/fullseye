---
op: xsitk_connected_threshold
dim: 2d
category: extra
in: image
out: region
examples: [gallery2d_color_artistic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# xsitk_connected_threshold — 2D `extra` op

- **データ種**: `image` → `region`
- **呼び出し**: `fullseye.apply(img, "xsitk_connected_threshold", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![xsitk_connected_threshold: input → output](../../_fig/xsitk_connected_threshold.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![xsitk_connected_threshold: knob a sweep](../../_fig/xsitk_connected_threshold.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![xsitk_connected_threshold: knob b sweep](../../_fig/xsitk_connected_threshold.b.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![xsitk_connected_threshold: other inputs](../../_fig/xsitk_connected_threshold.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

連結閾値領域拡張(SimpleITK ``ConnectedThreshold``、region growing)。画像中心の画素を種(シード)にし、その画素値を中心とした強度区間内で中心と連結している画素だけを領域として拡張する。

``a`` は下限マージン(``0.1+0.3*a``)、``b`` は上限マージン(``0.1+0.3*b``)を振る —— 区間は [中心値-下限, 中心値+上限]。画像中心付近に対象があることを前提とした op。

## 詳しい使い方ガイド

- [gallery2d_color_artistic ファミリ ガイド](../guides/gallery2d_color_artistic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
xsitk_connected_threshold 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_color_artistic](../../../../examples/gallery2d_color_artistic.py) — `py -3.11 examples/gallery2d_color_artistic.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`extra`)

[xsitk_curvature_flow](xsitk_curvature_flow.md) · [xsitk_minmax_curv_flow](xsitk_minmax_curv_flow.md) · [xsitk_curv_aniso_diff](xsitk_curv_aniso_diff.md) · [xsitk_laplacian_sharpen](xsitk_laplacian_sharpen.md) · [xsitk_grayscale_fillhole](xsitk_grayscale_fillhole.md) · [xsitk_grayscale_grindpeak](xsitk_grayscale_grindpeak.md) · [xsitk_opening_by_recon](xsitk_opening_by_recon.md) · [xsitk_closing_by_recon](xsitk_closing_by_recon.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
