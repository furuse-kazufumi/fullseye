---
op: seg_contingency
dim: emproof
category: score
in: labels2d × labels2d
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# seg_contingency — EMPROOF `score` op

- **データ種**: `labels2d × labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_contingency(a, b, ignore_label=None)` (実装を直接呼ぶなら `import segcompare; segcompare.seg_contingency(a, b, ignore_label=None)`、台帳から引くなら `opsemproof.get("seg_contingency")`)

## 使い方

The contingency table of truth ``a`` against candidate ``b`` (sparse).

Returns ``labels_a`` / ``labels_b`` (the distinct labels), ``rows`` / ``cols`` (indices
into them) and ``counts`` for every co-occurring pair, plus ``n`` (pixels counted),
``row_sums`` (size of each truth object) and ``col_sums`` (size of each candidate object).
``counts.sum() == n``, ``row_sums.sum() == col_sums.sum() == n``.

**Raises** ``ValueError``: non-integer, non-finite, boolean-free-but-string or masked input;
not 2-D / 3-D; empty; different shapes; every pixel ignored.

## 詳しい使い方ガイド

- [emproof ファミリ ガイド](../guides/emproof.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[seg_synapse_partners](../wiring/seg_synapse_partners.md) · [seg_wiring_variation](../wiring/seg_wiring_variation.md) · [seg_synapse_nri](../wiring/seg_synapse_nri.md) · [seg_wiring_exposure](../wiring/seg_wiring_exposure.md)

## 同カテゴリ(`score`)

[seg_variation_of_information](seg_variation_of_information.md) · [seg_rand](seg_rand.md)

---
*Provenance: segcompare.py — EMPROOF operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
