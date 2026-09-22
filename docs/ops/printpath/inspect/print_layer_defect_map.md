---
op: print_layer_defect_map
dim: printpath
category: inspect
in: image2d × image2d
out: image2d
examples: [poc_print_layer_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# print_layer_defect_map — PRINTPATH `inspect` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.print_layer_defect_map(observed: 'Any', expected: 'Any', tolerance_px: 'int' = 2, threshold: 'float' = 0.5) -> 'np.ndarray'` (実装を直接呼ぶなら `import printpath; printpath.print_layer_defect_map(observed: 'Any', expected: 'Any', tolerance_px: 'int' = 2, threshold: 'float' = 0.5) -> 'np.ndarray'`、台帳から引くなら `opsprintpath.get("print_layer_defect_map")`)

## 使い方

観測した層画像と期待の層画像(``gcode_layer_image``)を比べた**符号つきの欠陥図** ``image2d``:
+1 = あるはずの所に無い(欠け・詰まり)、−1 = 無いはずの所にある(糸引き・はみ出し・spaghetti)、0 = 一致。

両方を ``threshold`` で二値化し、``tolerance_px`` だけ膨らませた相手に含まれない画素だけを欠陥にする(位置ずれと
線幅の揺れを許す)。位置合わせはしない —— カメラ像は先に ``gcode_layer_image`` と同じ画素格子へ写しておく。

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_print_layer_inspection](../../../../examples/poc_print_layer_inspection.py) — `py -3.11 examples/poc_print_layer_inspection.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[stipple_points_from_image](../stroke/stipple_points_from_image.md) · [stipple_energy](../stroke/stipple_energy.md) · [stroke_tone_error](../stroke/stroke_tone_error.md)

## 同カテゴリ(`inspect`)

—

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
