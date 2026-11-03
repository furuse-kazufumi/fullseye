---
op: ocr_classify
dim: symbol
category: ocr
in: matrix × table
out: table
gpu: なし
examples: [poc_symbol_lot_ocr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# ocr_classify — SYMBOL `ocr` op

- **データ種**: `matrix × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ocr_classify(features, model, k=1, blur=None) -> 'dict'` (実装を直接呼ぶなら `import ocrclassic; ocrclassic.ocr_classify(features, model, k=1, blur=None) -> 'dict'`、台帳から引くなら `opssymbol.get("ocr_classify")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

特徴量を k 最近傍で識別し、距離と距離比で棄却する(``table``)。

Parameters
----------
features : (d,) か (m, d)、d = FEATURE_LENGTH。
model : ``ocr_train`` の返り値。
k : 近傍数(奇数推奨)。多数決、同票は最近傍のクラス。
blur : 既知(または推定済み)のぼけ σ/字高。与えると、学習のぼけ格子でそれと隣り合う
    格子点までの試料だけを照合に使う(``ocr_read_line`` は行全体で推定して渡す)。
    Restrict templates to the blur band around ``blur`` (sigma / char height).

Returns
-------
dict
    ``labels`` (list of str、棄却は ``"?"``), ``raw_labels``(棄却前の判定),
    ``distance``(判定クラスの最近傍距離。``model["weights"]`` で重みづけした対角マハラノビス距離),
    ``margin``(**他クラス最近傍距離 / 判定クラス最近傍距離**、1 に近いほど境界上), ``rejected``。
    棄却条件: ``distance > reject_distance_by_class[判定字]`` または ``margin < min_margin_ratio``。

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_lot_ocr](../../../../examples/poc_symbol_lot_ocr.py) — `py -3.11 examples/poc_symbol_lot_ocr.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_symbol](../symbol_capture/render_symbol.md) · [symbol_read_trials](../read_pod/symbol_read_trials.md) · [symbol_read_pod](../read_pod/symbol_read_pod.md) · [ocr_read_line](ocr_read_line.md) · [ocr_read_trials](ocr_read_trials.md)

## 同カテゴリ(`ocr`)

[ocr_font](ocr_font.md) · [ocr_render_text](ocr_render_text.md) · [ocr_segment_line](ocr_segment_line.md) · [ocr_features](ocr_features.md) · [ocr_train](ocr_train.md) · [ocr_read_line](ocr_read_line.md) · [ocr_score](ocr_score.md) · [ocr_read_trials](ocr_read_trials.md)

---
*Provenance: ocrclassic.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
