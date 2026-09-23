---
op: stipple_energy
dim: printpath
category: stroke
in: image2d × pairs
out: measurement
examples: [poc_beats_fringes_and_screens, poc_one_stroke_epicycles]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# stipple_energy — PRINTPATH `stroke` op

- **データ種**: `image2d × pairs` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.stipple_energy(image, points, gamma=1.0, floor=0.02)` (実装を直接呼ぶなら `import printpath; printpath.stipple_energy(image, points, gamma=1.0, floor=0.02)`、台帳から引くなら `opsprintpath.get("stipple_energy")`)

## 使い方

重みつき Lloyd のエネルギー ``Σ w(x) |x - c(x)|^2``(単調減少の検査用)。

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_beats_fringes_and_screens](../../../../examples/poc_beats_fringes_and_screens.py) — `py -3.11 examples/poc_beats_fringes_and_screens.py`
- [poc_one_stroke_epicycles](../../../../examples/poc_one_stroke_epicycles.py) — `py -3.11 examples/poc_one_stroke_epicycles.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`stroke`)

[stipple_points_from_image](stipple_points_from_image.md) · [stroke_tour_closed](stroke_tour_closed.md) · [mst_length](mst_length.md) · [stroke_resample_closed](stroke_resample_closed.md) · [stroke_tone_error](stroke_tone_error.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
