---
op: stroke_resample_closed
dim: printpath
category: stroke
in: pairs
out: pairs
examples: [poc_one_stroke_epicycles]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# stroke_resample_closed — PRINTPATH `stroke` op

- **データ種**: `pairs` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.stroke_resample_closed(points, n_points, allow_shortening=False)` (実装を直接呼ぶなら `import printpath; printpath.stroke_resample_closed(points, n_points, allow_shortening=False)`、台帳から引くなら `opsprintpath.get("stroke_resample_closed")`)

## 使い方

閉じた線を**等弧長**に打ち直す。→ ``pairs``

フーリエへ渡す前段。★媒介変数の取り方で係数が変わる(実測で最大 47 倍)ので、
ここは**弧長で等間隔**と明示する。弧長の間隔は機械精度で一定(実測 cv 1e-14)。

★**ただし打ち直すと線は短くなる**: 標本と標本を結ぶのは弦なので、折れ点で角を
切る。実測(300 頂点の巡回路): 標本 4000 で長さ 99.1 %、1024 で 96.9 %、
300(頂点と同数)で 89.3 %、100 で 72.8 %、50 で **57.7 %**。長さが変われば
濃淡の再現も壊れるので、**入力の頂点数より少ない標本は既定で拒否する**
(意図してならば ``allow_shortening=True``)。

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_one_stroke_epicycles](../../../../examples/poc_one_stroke_epicycles.py) — `py -3.11 examples/poc_one_stroke_epicycles.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[stipple_energy](stipple_energy.md) · [stroke_tour_closed](stroke_tour_closed.md) · [mst_length](mst_length.md) · [stroke_tone_error](stroke_tone_error.md)

## 同カテゴリ(`stroke`)

[stipple_points_from_image](stipple_points_from_image.md) · [stipple_energy](stipple_energy.md) · [stroke_tour_closed](stroke_tour_closed.md) · [mst_length](mst_length.md) · [stroke_tone_error](stroke_tone_error.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
