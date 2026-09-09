---
op: hx_char_threshold
dim: 2d
category: halcon_ext
in: image
out: region
halcon: char_threshold
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# hx_char_threshold — 2D `halcon_ext` op

- **データ種**: `image` → `region`
- **呼び出し**: `fullseye.apply(img, "hx_char_threshold", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `char_threshold`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_char_threshold: input → output](../../_fig/hx_char_threshold.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![hx_char_threshold: knob a sweep](../../_fig/hx_char_threshold.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![hx_char_threshold: other inputs](../../_fig/hx_char_threshold.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

暗い文字を明るい背景から抽出(region): thresh = mean - k*std(k は a)で下側を選ぶ。

画像全体の平均 ``mean`` と標準偏差 ``std`` から ``thr = mean - k*std`` を計算し、``v < thr`` の画素を 1 とする
0/1 の float region を返す。暗い文字が少数派で明るい背景が多数派、という前提の大域しきい値。

- ``a`` → 係数 ``k = 0.2 + 1.8*a``(0.2〜2.0)。大きいほど厳しく(より暗い画素だけ)、小さいほど多く拾う。
- ``b`` は未使用。

濃淡が一様な画像では ``std = 0`` となり ``thr = mean`` で「平均未満」だけが残る。照明ムラがあると 1 本の
しきい値では片側が欠けるので、前に ``hx_plane_deviation`` で背景を引くか、局所版の ``dyn_threshold`` /
``local_threshold`` を使う。明るい文字を取りたい場合は先に画像を反転する(この op は下側しか選ばない)。

## 詳しい使い方ガイド

- [gallery2d_halcon_ext ファミリ ガイド](../guides/gallery2d_halcon_ext.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
hx_char_threshold 0.50 0.50
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
