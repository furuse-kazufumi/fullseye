---
op: text_candidates
dim: text
category: detect
in: matrix
out: table
examples: [poc_text_region_truth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# text_candidates — TEXT `detect` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.text_candidates(swt, min_area: 'int' = 8, max_var_ratio: 'float' = 0.5, aspect_range=(0.1, 10.0), max_height: 'int' = 300)` (実装を直接呼ぶなら `import textregion; textregion.text_candidates(swt, min_area: 'int' = 8, max_var_ratio: 'float' = 0.5, aspect_range=(0.1, 10.0), max_height: 'int' = 300)`、台帳から引くなら `opstext.get("text_candidates")`)

## 使い方

SWT の連結成分を文字候補に絞る(幅のばらつき・縦横比・大きさ)。

Epshtein 2010 §4 の規則: 成分内のストローク幅の分散が平均に対して小さい /
縦横比が極端でない / 大きすぎない。``swt`` は :func:`swt_map` の ``swt``。
Returns dict: ``boxes``(N×4 の [y0, x0, y1, x1]、半開区間)/ ``labels`` /
``stroke_width``(各成分の中央値)/ ``n_components``(絞る前の数)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_text_region_truth](../../../../examples/poc_text_region_truth.py) — `py -3.11 examples/poc_text_region_truth.py`

## 型が繋がる次の op(`table` を入力に取れる)

[text_lines](../layout/text_lines.md)

## 同カテゴリ(`detect`)

—

---
*Provenance: textregion.py — TEXT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
