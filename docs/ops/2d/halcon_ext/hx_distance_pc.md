---
op: hx_distance_pc
dim: 2d
category: halcon_ext
in: contour
out: feature
halcon: distance_pc
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# hx_distance_pc — 2D `halcon_ext` op

- **データ種**: `contour` → `feature`
- **呼び出し**: `fullseye.apply(img, "hx_distance_pc", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `distance_pc`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_distance_pc: input → output](../../_fig/hx_distance_pc.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![hx_distance_pc: knob a sweep](../../_fig/hx_distance_pc.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![hx_distance_pc: knob b sweep](../../_fig/hx_distance_pc.b.jpg)

**段階**(前置きの op → この op。左から順):

![hx_distance_pc: stages](../../_fig/hx_distance_pc.chain.jpg)

## 使い方

クエリ点(正規化 a,b)から contour までの最小距離を返す(feature)。

正規化座標 ``(a, b)`` のクエリ点 ``q = (a*H, b*W)`` から、全 contour の頂点までのユークリッド距離の最小値を
``max(H, W)`` で割って 1 で頭打ちした ``np.float64`` で返す。

- ``a`` → クエリ点の行(0〜1)。
- ``b`` → クエリ点の列(0〜1)。
- contour の点が無ければ 0.0(点が contour 上にある場合と区別できない)。

距離は頂点までであって線分までではないので、点の間隔が粗い contour では真の距離より最大で「点間隔の半分」程度
大きく出る。細かい contour(``edges_sub_pix`` の 1 画素刻み)ではほぼ一致する。region までの距離は
``hx_distance_pr``、水平線からの距離は ``hx_distance_sc``、点を含む contour の選択は ``hx_select_xld_point``。

## 詳しい使い方ガイド

- [gallery2d_halcon_ext ファミリ ガイド](../guides/gallery2d_halcon_ext.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
threshold 0.50 0.50
sk_find_contours 0.50 0.50
hx_distance_pc 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_halcon_ext](../../../../examples/gallery2d_halcon_ext.py) — `py -3.11 examples/gallery2d_halcon_ext.py`

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md)

## 同カテゴリ(`halcon_ext`)

[hx_gen_circle](hx_gen_circle.md) · [hx_gen_ellipse](hx_gen_ellipse.md) · [hx_gen_rectangle2](hx_gen_rectangle2.md) · [hx_gen_checker_region](hx_gen_checker_region.md) · [hx_gen_grid_region](hx_gen_grid_region.md) · [hx_gabor](hx_gabor.md) · [hx_fit_surface1](hx_fit_surface1.md) · [hx_fit_surface2](hx_fit_surface2.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
