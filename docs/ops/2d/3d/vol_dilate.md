---
op: vol_dilate
dim: 2d
category: 3d
in: volume
out: volume
examples: [gallery2d_physics_alife_3d, poc_warehouse_flow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_dilate — 2D `3d` op

- **データ種**: `volume` → `volume`
- **呼び出し**: `fullseye.apply(img, "vol_dilate", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![vol_dilate: input → output](../../_fig/vol_dilate.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![vol_dilate: stages](../../_fig/vol_dilate.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![vol_dilate: other inputs](../../_fig/vol_dilate.inputs.jpg)

**動き**(GIF: フレーム / 視点 / スライスを順に。静止の図が完成形で、GIF は補助):

![vol_dilate: animation](../../_fig/vol_dilate.gif)

## 使い方

3D ボリュームのグレースケール膨張。対応する HALCON op は指定されていない。

``_vol_erode`` と同じ式 ``size = 1 + 2*(1 + int(a))`` を使うため、``a`` はほぼ効かない（``a`` が ``[0,1)`` の間は ``int(a)`` が常に 0 で実質サイズ ``3`` 固定、``a=1.0`` のときだけ ``5``）。``b`` も未使用。半径を連続的に振りたい場合は球形構造要素版（``_vol_dilation_ball`` 等、``int(a*3)`` を使い ``a`` が実際に効く）を使うこと。

## 詳しい使い方ガイド

- [gallery2d_physics_alife_3d ファミリ ガイド](../guides/gallery2d_physics_alife_3d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
img_to_volume 0.50 0.50
vol_dilate 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_physics_alife_3d](../../../../examples/gallery2d_physics_alife_3d.py) — `py -3.11 examples/gallery2d_physics_alife_3d.py`
- [poc_warehouse_flow](../../../../examples/poc_warehouse_flow.py) — `py -3.11 examples/poc_warehouse_flow.py`

## 型が繋がる次の op(`volume` を入力に取れる)

[identity](../misc/identity.md) · [vol_gaussian](vol_gaussian.md) · [vol_median](vol_median.md) · [vol_erode](vol_erode.md) · [vol_threshold](vol_threshold.md) · [vol_reg_dilate](vol_reg_dilate.md) · [vol_reg_erode](vol_reg_erode.md) · [vol_dilation_ball](vol_dilation_ball.md)

## 同カテゴリ(`3d`)

[vol_gaussian](vol_gaussian.md) · [vol_median](vol_median.md) · [vol_erode](vol_erode.md) · [vol_threshold](vol_threshold.md) · [vol_reg_dilate](vol_reg_dilate.md) · [vol_reg_erode](vol_reg_erode.md) · [vol_dilation_ball](vol_dilation_ball.md) · [vol_erosion_ball](vol_erosion_ball.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
