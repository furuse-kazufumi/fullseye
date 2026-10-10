---
op: text_lines
dim: text
category: layout
in: table
out: table
examples: [poc_text_region_truth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# text_lines — TEXT `layout` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.text_lines(boxes, stroke_width=None, overlap_ratio: 'float' = 0.5, gap_ratio: 'float' = 3.0, width_ratio: 'float' = 3.0)` (実装を直接呼ぶなら `import textregion; textregion.text_lines(boxes, stroke_width=None, overlap_ratio: 'float' = 0.5, gap_ratio: 'float' = 3.0, width_ratio: 'float' = 3.0)`、台帳から引くなら `opstext.get("text_lines")`)

## 使い方

文字候補の矩形を行にまとめる(縦に重なり、横に近く、ストローク幅が近いものを繋ぐ)。

★規則の根拠(2026-09-27 実測): 候補は字画ごとの断片になる(横棒と 'l' では高さが 5 倍
違う)ので「高さが近い」を条件にすると 3 行が 30〜60 行に割れた。行の同一性は**縦の
重なり**(小さい方の高さの ``overlap_ratio`` 以上)で判定し、横の隙間は大きい方の高さの
``gap_ratio`` 倍以内、ストローク幅は ``width_ratio`` 倍以内。

Returns dict: ``lines``(M×4 の矩形)/ ``members``(各行の候補 index のリスト)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_text_region_truth](../../../../examples/poc_text_region_truth.py) — `py -3.11 examples/poc_text_region_truth.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`layout`)

—

---
*Provenance: textregion.py — TEXT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
