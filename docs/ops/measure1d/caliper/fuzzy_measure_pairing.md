---
op: fuzzy_measure_pairing
dim: measure1d
category: caliper
in: image2d × measurehandle
out: table
examples: [poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# fuzzy_measure_pairing — MEASURE1D `caliper` op

- **データ種**: `image2d × measurehandle` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fuzzy_measure_pairing(image, measure, sigma=1.0, threshold=0.1, pair_size=None)` (実装を直接呼ぶなら `import measuring1d; measuring1d.fuzzy_measure_pairing(image, measure, sigma=1.0, threshold=0.1, pair_size=None)`、台帳から引くなら `opsmeasure1d.get("fuzzy_measure_pairing")`)

## 使い方

ファジィ基準(想定幅 pair_size)に最も合うエッジ対を選ぶ(fuzzy_measure_pairing)。

手順: ``measure_pairs(image, measure, sigma, threshold)`` で極性の異なる隣接
エッジの対を取り、各対に ``fuzzy_score = exp(-((width - pair_size) /
(0.5 pair_size))^2)`` を付けて **スコア降順に並べ替える**。想定幅ちょうどで 1、
幅が ``±0.5 pair_size`` ずれると ``e^-1`` ≈ 0.37。先頭要素が最も合う対。

- ``image``: 2-D float(グレー値の単位は入力のまま)。
- ``measure``: ``gen_measure_rectangle2`` / ``gen_measure_arc`` の dict。
- ``sigma``: プロファイルの平滑化 σ [サンプル]。``threshold``: 採用するエッジの
  最小 |グレー差|(画像の単位)。
- ``pair_size``: 想定幅 [px]。``None`` なら並べ替えもスコア付けもせず
  ``measure_pairs`` の結果(測定線に沿った順)をそのまま返す。0 や負は検証
  しない(0 だと分母が 1e-9 になり全対のスコアがほぼ 0 か 1 に潰れる)。
- 返り値: 対の dict の list(``table`` 型)。各 dict は ``first`` / ``second``
  (サンプル index)、``width`` [px]、``first_point`` / ``second_point``
  (``(row, col)``)、``first_amplitude`` / ``second_amplitude``、``fuzzy_score``。
  対が 1 つも無ければ空 list(例外にはしない)。

幅の下限・上限で切りたい場合はこの結果を ``width`` で自分でフィルタする
(この op は順位付けだけで、閾での除外はしない)。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`caliper`)

[gen_measure_rectangle2](gen_measure_rectangle2.md) · [gen_measure_arc](gen_measure_arc.md) · [translate_measure](translate_measure.md) · [measure_pos](measure_pos.md) · [measure_pairs](measure_pairs.md)

---
*Provenance: measuring1d.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
