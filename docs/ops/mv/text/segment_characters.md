---
op: segment_characters
dim: mv
category: text
in: image2d
out: labels2d
halcon: segment_characters
gpu: なし
examples: [machine_vision_tour, poc_real_typewritten_ocr]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# segment_characters — MV `text` op

- **データ種**: `image2d` → `labels2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.segment_characters(image, min_area=4, max_gap=1)` (実装を直接呼ぶなら `import mvtext; mvtext.segment_characters(image, min_area=4, max_gap=1)`、台帳から引くなら `opsmv.get("segment_characters")`)
- **HALCON 相当**: `segment_characters`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

文字行の画像を、字ごとの列の塊へ切り分けたラベル画像にする。

連結成分を列の範囲で束ね、列の隙間が ``max_gap`` 以下の成分は同じ字にする(``i`` の点や
``=`` のように上下へ分かれた字を 1 字に数えるため)。``min_area`` 未満の成分は雑音として
捨てる。ラベルは左から順。インクが無い画像は全 0 を返す(理由: 字が無い)。
空の入力(``image`` が 0 要素)は ValueError。

Args:
    image: 灰色画像か bool の領域 (H, W)。
    min_area: 残す連結成分の最小の画素数(>= 1)。
    max_gap: 同じ字と見なす列の隙間(>= 0)。隙間が負(重なり)の成分は必ず束ねる。

Returns:
    ``image`` と同じ形の整数ラベル画像(背景 0、字 1..n)。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`
- [poc_real_typewritten_ocr](../../../../examples/poc_real_typewritten_ocr.py) — `py -3.11 examples/poc_real_typewritten_ocr.py`

## 型が繋がる次の op(`labels2d` を入力に取れる)

[select_characters](select_characters.md)

## 同カテゴリ(`text`)

[text_line_orientation](text_line_orientation.md) · [text_line_slant](text_line_slant.md) · [select_characters](select_characters.md)

---
*Provenance: mvtext.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
