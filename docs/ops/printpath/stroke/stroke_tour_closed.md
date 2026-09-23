---
op: stroke_tour_closed
dim: printpath
category: stroke
in: pairs
out: pairs
examples: [poc_one_stroke_epicycles]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# stroke_tour_closed — PRINTPATH `stroke` op

- **データ種**: `pairs` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.stroke_tour_closed(points, start='nearest', two_opt_rounds=8, order=None)` (実装を直接呼ぶなら `import printpath; printpath.stroke_tour_closed(points, start='nearest', two_opt_rounds=8, order=None)`、台帳から引くなら `opsprintpath.get("stroke_tour_closed")`)

## 使い方

点を 1 回ずつ通って戻る**閉じた巡回路**に並べ替える。→ ``pairs``

返るのは入力と同じ点を並べ替えた ``(N, 2)``。**最後の点から最初の点へ戻る**
ことで閉じる(末尾に先頭を重複させない)。

★これは最適な巡回路ではない(TSP は NP 困難)。**下界と比べて質を言う**:
閉じた巡回路は最小全域木より短くなれないので ``length / mst_length`` が
1 に近いほど良い。一様な点なら Beardwood–Halton–Hammersley の
``0.7124 √(n A)`` も目安になる。**黄金ファイルは使わない。**

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_one_stroke_epicycles](../../../../examples/poc_one_stroke_epicycles.py) — `py -3.11 examples/poc_one_stroke_epicycles.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[stipple_energy](stipple_energy.md) · [mst_length](mst_length.md) · [stroke_resample_closed](stroke_resample_closed.md) · [stroke_tone_error](stroke_tone_error.md) · [mosaic_tiles_render](../npr/mosaic_tiles_render.md)

## 同カテゴリ(`stroke`)

[stipple_points_from_image](stipple_points_from_image.md) · [stipple_energy](stipple_energy.md) · [mst_length](mst_length.md) · [stroke_resample_closed](stroke_resample_closed.md) · [stroke_tone_error](stroke_tone_error.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
