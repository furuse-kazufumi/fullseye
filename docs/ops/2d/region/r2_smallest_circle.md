---
op: r2_smallest_circle
dim: 2d
category: region
in: region
out: region
halcon: smallest_circle
examples: [gallery2d_region]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# r2_smallest_circle — 2D `region` op

- **データ種**: `region` → `region`
- **呼び出し**: `fullseye.apply(img, "r2_smallest_circle", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `smallest_circle`(意味・パラメータは HALCON リファレンスが参考になる)

![r2_smallest_circle: input → output](../../_fig/r2_smallest_circle.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![r2_smallest_circle: knob a sweep](../../_fig/r2_smallest_circle.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![r2_smallest_circle: stages](../../_fig/r2_smallest_circle.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![r2_smallest_circle: other inputs](../../_fig/r2_smallest_circle.inputs.jpg)

## 使い方

Minimum enclosing circle as a mask (Welzl); a inflates radius (>=0).

領域の全前景画素(画素中心)を含む最小包含円をマスクとして描く。前景座標を
凸包(Andrew の単調鎖、向き判定は ``predicates.orient2d`` の頑健版)に減らして
から Welzl の再帰アルゴリズムで厳密な最小円 ``(cy, cx, r)`` を求める。凸包
頂点の順序は ``numpy.random.default_rng(0)`` で固定シャッフルするので結果は
決定的。

描く半径は ``r_draw = (r + 0.75) * (1 + 0.4*a)``。``a=0`` でも 0.75 画素
余分に膨らませる(画素中心ベースの ``r`` では縁の画素が欠けるため、全前景
画素を確実に含める設計)。``a=1`` で 1.4 倍。``a`` は [0,1] に clip。``b`` は
未使用。返り値は入力と同形の float64 0/1 マスク、前景が無ければ全零。

注意: 出力は常に入力領域を含み、``a`` を上げても縮む方向には動かない。複数の
連結成分があれば全体を囲む 1 つの円。前景が 1 画素なら ``r=0`` で半径 0.75
の円板(1 画素)になる。Welzl の再帰は凸包頂点数ぶん深くなる。円の中心や
半径の数値は返さない。内接円 ``r2_inner_circle`` との半径比が真円度の粗い
指標になり、向きを持つ外接形は ``r2_smallest_rectangle2``。

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
r2_smallest_circle 0.50 0.50
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
