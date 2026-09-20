---
op: seg_boundary_membrane_gap
dim: emproof
category: suspect
in: labels2d × image2d
out: table
examples: [poc_em_second_opinion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# seg_boundary_membrane_gap — EMPROOF `suspect` op

- **データ種**: `labels2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_boundary_membrane_gap(labels, membrane, tau: 'float' = 0.2, min_len: 'int' = 60, normalize: 'bool' = True, ignore_zero: 'bool' = True) -> 'dict'` (実装を直接呼ぶなら `import emproof; emproof.seg_boundary_membrane_gap(labels, membrane, tau: 'float' = 0.2, min_len: 'int' = 60, normalize: 'bool' = True, ignore_zero: 'bool' = True) -> 'dict'`、台帳から引くなら `opsemproof.get("seg_boundary_membrane_gap")`)

## 使い方

**分断の疑い**: 隣接する 2 ラベルの境界画素のうち、膜応答が ``tau`` 未満の割合。隣接対ごとに 1 行。

細胞の境目には必ず膜(暗い線)がある。膜が無いのにラベルが変わる境界は、1 細胞を 2 つに切った
分断の跡(``seg_inject_split`` の直線はまさにこれ)。4 近傍で異ラベルが接する画素を数え、境界の膜応答は
両側の強い方をとる。CREMI sample A の試作で人工分断 vs 他: **AUC 0.99**(tau 0.2、境界長 ≥ 60)。
列: ``label_a`` / ``label_b``(a < b)/ ``length`` / ``gap_fraction`` / ``membrane_mean``(gap_fraction 降順)。
``min_len`` px 未満の短い境界は数えない(数画素の接触は膜の有無を言えない)。

>>> table = seg_boundary_membrane_gap(labels, seg_membrane_response(raw))
>>> table["label_a"][0], table["label_b"][0], table["gap_fraction"][0]   # いちばん怪しい対

## 詳しい使い方ガイド

- [emproof ファミリ ガイド](../guides/emproof.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_em_second_opinion](../../../../examples/poc_em_second_opinion.py) — `py -3.11 examples/poc_em_second_opinion.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`suspect`)

[seg_membrane_chord_score](seg_membrane_chord_score.md)

---
*Provenance: emproof.py — EMPROOF operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
