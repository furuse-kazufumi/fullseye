---
op: joint_entropy
dim: imgmetrics
category: information
in: image2d × image2d
out: scalar
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# joint_entropy — IMGMETRICS `information` op

- **データ種**: `image2d × image2d` → `scalar`
- **呼び出し**: `import imgmetrics; imgmetrics.joint_entropy(a, b, bins=64, data_range=None)` (または `opsimgmetrics.get("joint_entropy")`)

## 使い方

同時エントロピー H(A, B) [bit]。

式: ``-sum(p log2 p)`` を ``joint_histogram(a, b, bins, data_range)`` の全セル
(``p > 0`` のみ)について取る。

- ``a``, ``b``: 同じ形、有限。dtype と ``data_range`` の扱いは ``joint_histogram``
  と同じ(float は ``[0, 1]`` 以外なら明示必須)。
- ``bins``: 2 以上の整数。**値はビン数に依存する** ―― 上限は ``2 log2(bins)``
  (既定 64 で 12 bit)。他所の数値と比べるときは ``bins`` と ``data_range`` を揃える。
- 返り値: Python の ``float``、単位 bit、``0`` 以上。2 枚とも一様なら 0。
  ``H(A) + H(B) - H(A, B)`` が相互情報量(``mutual_information``)。
- 失敗(``MetricContractError``): 形が違う / 空 / 非有限 / ``bins < 2`` /
  ``data_range`` を推定できない。

位置合わせ(レジストレーション)の目的関数として、``mutual_information`` /
``normalized_mutual_information`` と併せて使う。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`information`)

[image_entropy](image_entropy.md) · [mutual_information](mutual_information.md) · [normalized_mutual_information](normalized_mutual_information.md) · [joint_histogram](joint_histogram.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
