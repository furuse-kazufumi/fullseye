---
op: m1_measure_pairs
dim: 2d
category: measure1d
in: image
out: feature
halcon: measure_pairs
examples: [gallery2d_contour_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# m1_measure_pairs — 2D `measure1d` op

- **データ種**: `image` → `feature`
- **呼び出し**: `fullseye.apply(img, "m1_measure_pairs", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `measure_pairs`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

中心を通るキャリパー線上で、立ち上がり→立ち下がりのエッジ対（明るい物体の両端）の個数を数える（HALCON ``measure_pairs`` に相当: 矩形/円弧に垂直な直線エッジのペアを抽出する）。

``a`` は線の向き（``theta = a*pi``）。エッジ検出は ``m1_measure_pos``と同じ（勾配ピークのサブピクセル検出）で、``b``（0〜1）は最大振幅に対する相対しきい値。しきい値を超えたエッジを順に走査し、極性がrising→falling と並ぶ組を 1 対として数える（feature、整数値）。エッジが 2 本未満なら 0.0。

## 詳しい使い方ガイド

- [gallery2d_contour_measure ファミリ ガイド](../guides/gallery2d_contour_measure.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_contour_measure](../../../../examples/gallery2d_contour_measure.py) — `py -3.11 examples/gallery2d_contour_measure.py`

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md)

## 同カテゴリ(`measure1d`)

[m1_measure_projection](m1_measure_projection.md) · [m1_measure_pos](m1_measure_pos.md) · [m1_measure_thresh](m1_measure_thresh.md) · [m1_fuzzy_measure_pos](m1_fuzzy_measure_pos.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
