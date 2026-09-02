---
op: measure_with
dim: imgmetrics
category: report
in: metrics × image2d × image2d
out: metrics
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# measure_with — IMGMETRICS `report` op

- **データ種**: `metrics × image2d × image2d` → `metrics`
- **呼び出し**: `import imgmetrics; imgmetrics.measure_with(report, a, b, ms=False)` (または `opsimgmetrics.get("measure_with")`)

## 使い方

**前の測定と厳密に同じ条件で**もう一組を測る。

:func:`compare_images` の返り値(``contract`` を含む)を受け取り、そこに
記録された ``data_range`` / ``bins`` / ``ncd_levels`` をそのまま使って測り直す。

これが要るのは、この repo で実際に起きた事故の型があるから ―― **数値だけを
図注や表に写して、条件が消える**。別々に測った 2 つの PSNR を並べたとき、
片方が ``data_range=1.0``、もう片方が ``255`` なら **48.13 dB の差が「改善」に
見える**。条件を持ち回れば、そもそも比べられない組合せは作れない。

同時に、これが ``metrics`` 型の**消費側**でもある。``compare_images`` だけが
``metrics`` を産んで誰も食わない状態は、この repo が繰り返し踏んできた
「入口はあるが消費 op が無い型」そのものだった(2026-09-02 の点検で検出)。

Parameters
----------
report : dict
    :func:`compare_images` の返り値、または ``contract`` そのもの。
a, b : array_like
    測り直す 2 枚。

Returns
-------
dict
    同じ形の報告。``contract`` は受け取ったものと**同一**。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`metrics` を入力に取れる)

[metrics_table](metrics_table.md)

## 同カテゴリ(`report`)

[compare_images](compare_images.md) · [metrics_table](metrics_table.md) · [data_range_of](data_range_of.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
