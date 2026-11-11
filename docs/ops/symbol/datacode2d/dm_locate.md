---
op: dm_locate
dim: symbol
category: datacode2d
in: image2d
out: table
gpu: なし
examples: [poc_symbol_part_dpm]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# dm_locate — SYMBOL `datacode2d` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dm_locate(image) -> 'dict'` (実装を直接呼ぶなら `import dmsym; dmsym.dm_locate(image) -> 'dict'`、台帳から引くなら `opssymbol.get("dm_locate")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

画像から Data Matrix を見つけ、モジュール空間 → 画像の射影変換を推定する(``table``)。

Locate a dark-on-light ECC200 symbol (quiet zone >= 1 module). Global
binarisation (Otsu start, then the midpoint of the dark/light means), dark pixels grouped after a distance-based closing at several
radii (so separated dot-peen dots join), near max-area quadrilateral in the
convex hull, sub-pixel edge lines (grey-level threshold crossings, inward
outliers from the clock gaps trimmed), corners = line intersections, then the
size and which corner is the L corner are chosen by the agreement of the
sampled function pattern (finder + clock + alignment) for every supported size
and corner correspondence.

Returns
-------
dict
    ``homography`` 3x3(module 空間 [x=列, y=行, 1] → 画像 [列, 行, w])、``rows``, ``cols``,
    ``corners`` (4, 2) 画素の (行, 列)、順は module 空間の (0,0), (C,0), (C,R), (0,R)、
    ``module_px``, ``score``(機能パターンの一致率), ``threshold``(大域閾値 / global threshold)。

Raises
------
ValueError
    2-D でない・NaN/inf・小さすぎる。
DMDecodeError
    記号が見つからない。

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_part_dpm](../../../../examples/poc_symbol_part_dpm.py) — `py -3.11 examples/poc_symbol_part_dpm.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_symbol](../symbol_capture/render_symbol.md) · [symbol_read_trials](../read_pod/symbol_read_trials.md) · [symbol_read_pod](../read_pod/symbol_read_pod.md) · [ocr_classify](../ocr/ocr_classify.md) · [ocr_read_line](../ocr/ocr_read_line.md) · [ocr_read_trials](../ocr/ocr_read_trials.md)

## 同カテゴリ(`datacode2d`)

[qr_encode](qr_encode.md) · [qr_decode_modules](qr_decode_modules.md) · [qr_locate](qr_locate.md) · [qr_sample](qr_sample.md) · [qr_read](qr_read.md) · [dm_encode](dm_encode.md) · [dm_decode_modules](dm_decode_modules.md) · [dm_sample](dm_sample.md)

---
*Provenance: dmsym.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
