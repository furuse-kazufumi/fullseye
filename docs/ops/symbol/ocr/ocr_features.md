---
op: ocr_features
dim: symbol
category: ocr
in: image2d
out: signal
gpu: なし
examples: [poc_symbol_lot_ocr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# ocr_features — SYMBOL `ocr` op

- **データ種**: `image2d` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.ocr_features(glyph_image) -> 'np.ndarray'` (実装を直接呼ぶなら `import ocrclassic; ocrclassic.ocr_features(glyph_image) -> 'np.ndarray'`、台帳から引くなら `opssymbol.get("ocr_features")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

1 字のインク地図から 88 次元の特徴量(区画の濃度 + 射影)を作る(``signal``)。

入力の約束 / Input contract
    ``glyph_image`` は**インク量の地図**(1 = インク、0 = 地、float)で、
    **行は字高の範囲(行の上端〜下端)、列はその字を含む範囲**を切り出したもの
    (``ocr_read_line`` はインク重心を中心に送り幅 1 つぶんの幅で切る)。
    行を字高にそろえるので ``.`` ``-`` ``:`` の縦位置と大きさが特徴量に残る
    (インクの外接箱で正規化すると ``.`` は大きな円板になり、何にでも似てしまう)。

正規化 / Normalisation
    縦: 切り出しの高さを ``FEATURE_GRID`` (24) 画素に拡縮。横: **同じ倍率**(縦横比保持)で、
    インクの重心列をキャンバス中央に置く(字幅を推定しないので、ぼけで箱が太っても位置がずれない)。
    縮小時は先に Gaussian で前置平滑(エイリアス防止)し、map_coordinates(双線形)で標本化。

構成 / Layout (length ``FEATURE_LENGTH`` = 88)
    [0:64]  8x8 区画濃度(各 3x3 画素の平均インク、0..1)/ zoning densities
    [64:76] 水平射影(行方向の平均インク、12 ビン)/ horizontal projection profile
    [76:88] 垂直射影(列方向の平均インク、12 ビン)/ vertical projection profile

交差数(crossing count)は使わない: 離散値で、ぼけとドットの途切れに不安定なため。
Crossing counts are not used: they are discrete and unstable under blur / dot gaps.

インクが無ければ全 0 を返す。/ Returns zeros for an empty glyph.

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_lot_ocr](../../../../examples/poc_symbol_lot_ocr.py) — `py -3.11 examples/poc_symbol_lot_ocr.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[decode_barcode_profile](../barcode1d/decode_barcode_profile.md) · [grade_barcode_profile](../print_quality/grade_barcode_profile.md)

## 同カテゴリ(`ocr`)

[ocr_font](ocr_font.md) · [ocr_render_text](ocr_render_text.md) · [ocr_segment_line](ocr_segment_line.md) · [ocr_train](ocr_train.md) · [ocr_classify](ocr_classify.md) · [ocr_read_line](ocr_read_line.md) · [ocr_score](ocr_score.md) · [ocr_read_trials](ocr_read_trials.md)

---
*Provenance: ocrclassic.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
