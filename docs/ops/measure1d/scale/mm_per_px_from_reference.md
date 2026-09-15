---
op: mm_per_px_from_reference
dim: measure1d
category: scale
in: measurement
out: measurement
examples: [example_inner_diameter_mm, example_scratch_width]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# mm_per_px_from_reference — MEASURE1D `scale` op

- **データ種**: `measurement` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.mm_per_px_from_reference(measured_px, known_mm)` (実装を直接呼ぶなら `import measuring1d; measuring1d.mm_per_px_from_reference(measured_px, known_mm)`、台帳から引くなら `opsmeasure1d.get("mm_per_px_from_reference")`)

## 使い方

既知寸法の的(スケールバー・基準穴・ゲージ)から画素ピッチ mm/px を出す(校正)。

``mm_per_px = known_mm / measured_px``。``measured_px`` は同じ光学系・同じ
作動距離で **この族の op が実際に測った**値(``measure_pairs`` の ``width``、
``apply_metrology_model`` の ``radius`` の 2 倍など)を渡す。図面値や公称の
倍率から置くと、作動距離が 10 % ずれれば全部の寸法が 10 % ずれる。

- ``measured_px``, ``known_mm``: 有限で正のスカラ(それ以外は ``ValueError``)。
- 返り値: mm/px(float、``measurement`` 型)。``pixel_to_world`` /
  ``table_px_to_mm`` に渡す。
- 透視の効く斜め撮影では場所ごとに mm/px が変わる。この op は**平面視・一定
  倍率**の前提で 1 個の値を返すだけで、それを検証はしない。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [example_inner_diameter_mm](../../../../examples/example_inner_diameter_mm.py) — `py -3.11 examples/example_inner_diameter_mm.py`
- [example_scratch_width](../../../../examples/example_scratch_width.py) — `py -3.11 examples/example_scratch_width.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[pixel_to_world](pixel_to_world.md)

## 同カテゴリ(`scale`)

[pixel_to_world](pixel_to_world.md) · [table_px_to_mm](table_px_to_mm.md)

---
*Provenance: measuring1d.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
