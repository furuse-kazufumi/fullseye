---
op: r2_sort_region
dim: 2d
category: region
in: region
out: region
halcon: sort_region
examples: [gallery2d_region]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# r2_sort_region — 2D `region` op

- **データ種**: `region` → `region`
- **呼び出し**: `fullseye.apply(img, "r2_sort_region", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `sort_region`(意味・パラメータは HALCON リファレンスが参考になる)

![r2_sort_region: input → output](../../_fig/r2_sort_region.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![r2_sort_region: knob a sweep](../../_fig/r2_sort_region.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![r2_sort_region: stages](../../_fig/r2_sort_region.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![r2_sort_region: other inputs](../../_fig/r2_sort_region.inputs.jpg)

## 使い方

Keep the k-th largest connected component; k = round(a*(n-1)).

前景マスク(``> 0.5``)を ``scipy.ndimage.label``(既定の 4 連結)で連結成分に
分け、面積(画素数)の降順に並べて ``k`` 番目の成分だけを残す。``k`` は
``round(a*(n-1))`` を ``[0, n-1]`` に clip した整数で、``a=0`` で最大成分、
``a=1`` で最小成分、``a=0.5`` でおおよそ中央の順位の成分。``n`` は成分数。
``b`` は未使用。

返り値は入力と同形の float64 0/1 マスク。成分が無ければ全零。同面積の成分が
複数あるときの順位は保証されない(``numpy.argsort`` の順序に依存)。成分数
``n`` が変わると同じ ``a`` でも選ばれる順位が変わる(相対指定)ので、
「最大成分」を確実に取りたいだけなら ``a=0`` か ``select_largest`` を使う。
斜め接続だけでつながった画素は別成分として数えられる(4 連結)。前段に
``opening_circle`` でくびれを切っておくと成分単位の選択が安定する。

## 詳しい使い方ガイド

- [gallery2d_region ファミリ ガイド](../guides/gallery2d_region.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
threshold 0.50 0.50
r2_sort_region 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_region](../../../../examples/gallery2d_region.py) — `py -3.11 examples/gallery2d_region.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](reg_erode.md) · [reg_dilate](reg_dilate.md) · [reg_open](reg_open.md) · [reg_close](reg_close.md) · [fill_holes](fill_holes.md) · [select_largest](select_largest.md) · [remove_small](remove_small.md)

## 同カテゴリ(`region`)

[reg_erode](reg_erode.md) · [reg_dilate](reg_dilate.md) · [reg_open](reg_open.md) · [reg_close](reg_close.md) · [fill_holes](fill_holes.md) · [select_largest](select_largest.md) · [remove_small](remove_small.md) · [invert_region](invert_region.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
