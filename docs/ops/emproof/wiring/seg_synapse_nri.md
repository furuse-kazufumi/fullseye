---
op: seg_synapse_nri
dim: emproof
category: wiring
in: labels2d × labels2d × table
out: table
examples: [poc_em_wiring_errors]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# seg_synapse_nri — EMPROOF `wiring` op

- **データ種**: `labels2d × labels2d × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_synapse_nri(a, b, synapses, spacing=None, background=0)` (実装を直接呼ぶなら `import segcompare; segcompare.seg_synapse_nri(a, b, synapses, spacing=None, background=0)`、台帳から引くなら `opsemproof.get("seg_synapse_nri")`)

## 使い方

Neural reconstruction integrity (Reilly et al. 2018) of candidate ``b`` against truth ``a``.

NRI scores the pairs of synapse **ends** that a reconstruction keeps together. Over the
``2n`` ends (``synapses`` as in :func:`seg_synapse_partners`; ends on ``background`` in
the truth are dropped, ends on background in the candidate are singletons), a pair of
ends that lies in one truth neuron **and** one candidate object is a true positive; a
pair in one truth neuron but different candidate objects is a false negative (a split);
a pair in one candidate object but different truth neurons is a false positive (a
merge). ``nri = 2TP / (2TP + FP + FN)`` with the pair ``precision`` and ``recall``.

Identity (checked inside, fail-closed): with ``n_ij`` the contingency table of the ends,
``TP = sum C(n_ij, 2)``, ``TP + FN = sum C(s_i, 2)``, ``TP + FP = sum C(t_j, 2)``, so NRI
is exactly ``1 - adapted_rand_error`` of :func:`seg_rand` taken over the ends (the
``- N`` form of the pair counts is ``2 C(n, 2)``). Both are computed and must agree to
1e-12. Returns ``nri``, ``precision``, ``recall``, ``tp``, ``fp``, ``fn``, ``n_ends``.

**Raises** ``ValueError``: as :func:`seg_wiring_variation`; fewer than 2 ends.

## 詳しい使い方ガイド

- [emproof ファミリ ガイド](../guides/emproof.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_em_wiring_errors](../../../../examples/poc_em_wiring_errors.py) — `py -3.11 examples/poc_em_wiring_errors.py`

## 型が繋がる次の op(`table` を入力に取れる)

[seg_synapse_partners](seg_synapse_partners.md) · [seg_wiring_variation](seg_wiring_variation.md) · [seg_wiring_exposure](seg_wiring_exposure.md)

## 同カテゴリ(`wiring`)

[seg_synapse_partners](seg_synapse_partners.md) · [seg_wiring_variation](seg_wiring_variation.md) · [seg_wiring_exposure](seg_wiring_exposure.md)

---
*Provenance: segcompare.py — EMPROOF operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
