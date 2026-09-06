---
op: m1_fuzzy_measure_pos
dim: 2d
category: measure1d
in: image
out: contour
halcon: fuzzy_measure_pos
examples: [gallery2d_contour_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# m1_fuzzy_measure_pos — 2D `measure1d` op

- **データ種**: `image` → `contour`
- **呼び出し**: `fullseye.apply(img, "m1_fuzzy_measure_pos", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `fuzzy_measure_pos`(意味・パラメータは HALCON リファレンスが参考になる)

![m1_fuzzy_measure_pos: input → output](../../_fig/m1_fuzzy_measure_pos.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![m1_fuzzy_measure_pos: knob a sweep](../../_fig/m1_fuzzy_measure_pos.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![m1_fuzzy_measure_pos: other inputs](../../_fig/m1_fuzzy_measure_pos.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

中心を通るキャリパー線上のエッジを、ファジィなメンバーシップスコアでふるいにかけて返す（HALCON ``fuzzy_measure_pos`` に相当: 矩形/円弧に垂直な直線エッジをファジィ判定で検出する）。

エッジ検出は ``m1_measure_pos`` と同じ。各エッジの振幅を``(amp - lo) / (gmax - lo)``（``lo = 0.05*gmax``）で [0,1] のファジィスコアに写像し、``b``（0〜1）以上のものだけを残す（0/1 のハードしきい値ではなく振幅に応じた連続的な信頼度で選別する点が ``measure_pos`` と違う）。``a`` は線の向き（``theta = a*pi``）。戻り値は CONTOUR、座標単位はピクセル。

## 詳しい使い方ガイド

- [gallery2d_contour_measure ファミリ ガイド](../guides/gallery2d_contour_measure.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
m1_fuzzy_measure_pos 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_contour_measure](../../../../examples/gallery2d_contour_measure.py) — `py -3.11 examples/gallery2d_contour_measure.py`

## 型が繋がる次の op(`contour` を入力に取れる)

[identity](../misc/identity.md) · [select_contours](../contour/select_contours.md) · [smooth_contours](../contour/smooth_contours.md) · [fit_line_contours](../contour/fit_line_contours.md) · [contours_to_region](../contour/contours_to_region.md) · [count_contours](../features/count_contours.md) · [total_length](../features/total_length.md) · [select_contours_xld](../contour/select_contours_xld.md)

## 同カテゴリ(`measure1d`)

[m1_measure_projection](m1_measure_projection.md) · [m1_measure_pos](m1_measure_pos.md) · [m1_measure_thresh](m1_measure_thresh.md) · [m1_measure_pairs](m1_measure_pairs.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
