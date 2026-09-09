---
op: sg_gmm_segment
dim: 2d
category: segment
in: image
out: region
examples: [gallery2d_segmentation, poc_nuclei_ploidy]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# sg_gmm_segment — 2D `segment` op

- **データ種**: `image` → `region`
- **呼び出し**: `fullseye.apply(img, "sg_gmm_segment", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![sg_gmm_segment: input → output](../../_fig/sg_gmm_segment.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![sg_gmm_segment: knob a sweep](../../_fig/sg_gmm_segment.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![sg_gmm_segment: other inputs](../../_fig/sg_gmm_segment.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

輝度値に対する 2 クラス・ガウス混合モデル（EM 法）で明るい方のクラスタを領域として返す（``skimage`` 非依存の自前 EM 実装、HALCON に対応オペレータなし）。

25/75 パーセンタイルで初期化した決定論的 EM で 1 次元 2 成分ガウス混合をフィットし、平均が高い方を「明るいクラス」とする。``a``（0〜1）は事後確率のしきい値 ``t = 0.25 + 0.5*a`` を振り、大きいほど「確実に明るい」と判定された画素だけを拾うようになる。``b`` は未使用。乱数を使わないので再現性がある。

## 詳しい使い方ガイド

- [gallery2d_segmentation ファミリ ガイド](../guides/gallery2d_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
sg_gmm_segment 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_segmentation](../../../../examples/gallery2d_segmentation.py) — `py -3.11 examples/gallery2d_segmentation.py`
- [poc_nuclei_ploidy](../../../../examples/poc_nuclei_ploidy.py) — `py -3.11 examples/poc_nuclei_ploidy.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`segment`)

[sg_slic_superpixels](sg_slic_superpixels.md) · [sg_felzenszwalb](sg_felzenszwalb.md) · [sg_kmeans_intensity](sg_kmeans_intensity.md) · [sg_region_growing_seeded](sg_region_growing_seeded.md) · [sg_normalized_cut_2](sg_normalized_cut_2.md) · [sg_watershed_gradient](sg_watershed_gradient.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
