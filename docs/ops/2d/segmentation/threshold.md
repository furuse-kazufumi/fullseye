---
op: threshold
dim: 2d
category: segmentation
in: image
out: region
halcon: threshold
examples: [gallery2d_segmentation, poc_bone_trabecular_thickness, poc_change_detection_misreg, poc_fresco_craquelure, poc_gear_tooth_metrology, poc_metal_grain_size, poc_screw_thread_metrology, poc_traffic_counting, poc_water_level, video_streaming]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# threshold — 2D `segmentation` op

- **データ種**: `image` → `region`
- **呼び出し**: `fullseye.apply(img, "threshold", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `threshold`(意味・パラメータは HALCON リファレンスが参考になる)

![threshold: input → output](../../_fig/threshold.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![threshold: knob a sweep](../../_fig/threshold.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![threshold: other inputs](../../_fig/threshold.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

大域しきい値処理（グローバルスレッショルド）。HALCON の ``threshold``（Segment an image using global threshold.）に相当。

``a`` がしきい値そのもの（``0〜1``）で、``v > a`` を満たす画素を前景（1）とする region を返す。``b`` は未使用。HALCON の ``threshold`` は下限・上限の 2 値を取れる帯域しきい値だが、この実装は下限のみの片側しきい値。

## 詳しい使い方ガイド

- [gallery2d_segmentation ファミリ ガイド](../guides/gallery2d_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
threshold 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_segmentation](../../../../examples/gallery2d_segmentation.py) — `py -3.11 examples/gallery2d_segmentation.py`
- [poc_bone_trabecular_thickness](../../../../examples/poc_bone_trabecular_thickness.py) — `py -3.11 examples/poc_bone_trabecular_thickness.py`
- [poc_change_detection_misreg](../../../../examples/poc_change_detection_misreg.py) — `py -3.11 examples/poc_change_detection_misreg.py`
- [poc_fresco_craquelure](../../../../examples/poc_fresco_craquelure.py) — `py -3.11 examples/poc_fresco_craquelure.py`
- [poc_gear_tooth_metrology](../../../../examples/poc_gear_tooth_metrology.py) — `py -3.11 examples/poc_gear_tooth_metrology.py`
- [poc_metal_grain_size](../../../../examples/poc_metal_grain_size.py) — `py -3.11 examples/poc_metal_grain_size.py`
- [poc_screw_thread_metrology](../../../../examples/poc_screw_thread_metrology.py) — `py -3.11 examples/poc_screw_thread_metrology.py`
- [poc_traffic_counting](../../../../examples/poc_traffic_counting.py) — `py -3.11 examples/poc_traffic_counting.py`
- [poc_water_level](../../../../examples/poc_water_level.py) — `py -3.11 examples/poc_water_level.py`
- [video_streaming](../../../../examples/video_streaming.py) — `py -3.11 examples/video_streaming.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`segmentation`)

[otsu](otsu.md) · [canny](canny.md) · [adaptive_gauss_thresh](adaptive_gauss_thresh.md) · [sk_otsu](sk_otsu.md) · [sk_li](sk_li.md) · [sk_yen](sk_yen.md) · [sk_sauvola](sk_sauvola.md) · [sk_niblack](sk_niblack.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
