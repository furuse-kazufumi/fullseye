---
op: seg_variation_of_information
dim: emproof
category: score
in: labels2d × labels2d
out: table
examples: [poc_em_split_merge_score, poc_em_wiring_errors, poc_skeleton_run_length_vs_voi]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# seg_variation_of_information — EMPROOF `score` op

- **データ種**: `labels2d × labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_variation_of_information(a, b, ignore_label=None)` (実装を直接呼ぶなら `import segcompare; segcompare.seg_variation_of_information(a, b, ignore_label=None)`、台帳から引くなら `opsemproof.get("seg_variation_of_information")`)

## 使い方

Variation of information between truth ``a`` and candidate ``b``, in bits.

Returns ``voi`` = ``split`` + ``merge``, with ``split = H(b|a)`` (how much the candidate
cuts true objects apart) and ``merge = H(a|b)`` (how much it glues different true objects
together), plus the entropies ``h_a``, ``h_b`` and the mutual information ``mi``.

**Raises** ``ValueError``: as :func:`seg_contingency`.

## 詳しい使い方ガイド

- [emproof ファミリ ガイド](../guides/emproof.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_em_split_merge_score](../../../../examples/poc_em_split_merge_score.py) — `py -3.11 examples/poc_em_split_merge_score.py`
- [poc_em_wiring_errors](../../../../examples/poc_em_wiring_errors.py) — `py -3.11 examples/poc_em_wiring_errors.py`
- [poc_skeleton_run_length_vs_voi](../../../../examples/poc_skeleton_run_length_vs_voi.py) — `py -3.11 examples/poc_skeleton_run_length_vs_voi.py`

## 型が繋がる次の op(`table` を入力に取れる)

[seg_synapse_partners](../wiring/seg_synapse_partners.md) · [seg_wiring_variation](../wiring/seg_wiring_variation.md)

## 同カテゴリ(`score`)

[seg_contingency](seg_contingency.md) · [seg_rand](seg_rand.md)

---
*Provenance: segcompare.py — EMPROOF operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
