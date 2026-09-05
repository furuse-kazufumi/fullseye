---
op: sg_normalized_cut_2
dim: 2d
category: segment
in: image
out: region
examples: [gallery2d_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# sg_normalized_cut_2 — 2D `segment` op

- **データ種**: `image` → `region`
- **呼び出し**: `fullseye.apply(img, "sg_normalized_cut_2", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

輝度グラフの正規化カット（スペクトラル 2 分割、Shi & Malik）で画像を明暗 2 領域に分ける（HALCON に対応オペレータなし）。

計算量を抑えるため画像を ``sdim = round(10+b*14)`` 程度まで間引いてから、輝度差と距離で重みを決めたアフィニティグラフを作り、一般化固有値問題 ``(D-W)y = lambda*D*y`` の第 2 固有ベクトル（Fiedler ベクトル）を中央値でしきい値化して 2 群に分ける。``a``（0〜1）は輝度方向の帯域幅``sig_i = 0.05 + a*0.5`` を振り、``b``（0〜1）は間引きの解像度を振る。明るい方の群を最近傍で元解像度に拡大して region として返す。

## 詳しい使い方ガイド

- [gallery2d_segmentation ファミリ ガイド](../guides/gallery2d_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_segmentation](../../../../examples/gallery2d_segmentation.py) — `py -3.11 examples/gallery2d_segmentation.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`segment`)

[sg_slic_superpixels](sg_slic_superpixels.md) · [sg_felzenszwalb](sg_felzenszwalb.md) · [sg_gmm_segment](sg_gmm_segment.md) · [sg_kmeans_intensity](sg_kmeans_intensity.md) · [sg_region_growing_seeded](sg_region_growing_seeded.md) · [sg_watershed_gradient](sg_watershed_gradient.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
