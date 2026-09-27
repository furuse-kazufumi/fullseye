---
op: seg_wiring_exposure
dim: emproof
category: wiring
in: labels2d × table
out: table
examples: [poc_em_wiring_errors]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# seg_wiring_exposure — EMPROOF `wiring` op

- **データ種**: `labels2d × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_wiring_exposure(labels, synapses, spacing=None, background=0, p=0.5)` (実装を直接呼ぶなら `import segcompare; segcompare.seg_wiring_exposure(labels, synapses, spacing=None, background=0, p=0.5)`、台帳から引くなら `opsemproof.get("seg_wiring_exposure")`)

## 使い方

How much wiring each object stakes on staying one piece — from synapse end counts alone.

Cutting an object whose ``s`` synapse ends (``synapses`` as in :func:`seg_synapse_partners`)
fall ``s1`` / ``s - s1`` on the two sides costs exactly ``(s / 2n) * H2(s1 / s)`` bits of
ends-level split (:func:`seg_wiring_variation`), and a hidden merge of two neurons inside
one object costs the same expression as merge. So what an object can cost is fixed by its
end count before any geometry is known:

* ``bound = s / 2n`` — the supremum over all cuts (reached when the ends halve). The bounds
  sum to ``n_ends / 2n``: exactly 1 bit when no end lies on ``background``.
* ``worst = (s / 2n) * H2(floor(s / 2) / s)`` — the largest cost a cut can actually reach.
* ``expected = (s / 2n) * E[H2(K / s)]``, ``K ~ Binomial(s, p)`` — the cost of a cut that
  puts each end on the cut-off side independently with probability ``p`` (default 1/2,
  the cut through the object's median voxel with ends spread evenly over it). This is the
  count-only prediction; the gap to the observed cost is the spatial clustering of the ends.
* ``density = (s / 2n) / (voxels / N)`` — the object's share of ends over its share of the
  ``N`` voxels of the volume. For an edit, wiring bits / pixel bits = density × (H2 of the
  end fractions / H2 of the voxel fractions): merges have the second factor near 1 (ends
  follow voxels), so their ratio is the density; a cut's second factor is
  ``H2(s1 / s) / 1`` and is what the binomial predicts.

Objects with no end are not listed. Returns ``labels``, ``voxels``, ``ends``, ``density``,
``bound``, ``worst``, ``expected`` (aligned arrays), ``n`` synapses, ``n_ends`` kept,
``n_background`` ends dropped, ``total_bound``, ``total_expected``.

**Raises** ``ValueError``: as :func:`seg_synapse_partners`; ``p`` not strictly inside
(0, 1); no end outside the background.

## 詳しい使い方ガイド

- [emproof ファミリ ガイド](../guides/emproof.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_em_wiring_errors](../../../../examples/poc_em_wiring_errors.py) — `py -3.11 examples/poc_em_wiring_errors.py`

## 型が繋がる次の op(`table` を入力に取れる)

[seg_synapse_partners](seg_synapse_partners.md) · [seg_wiring_variation](seg_wiring_variation.md) · [seg_synapse_nri](seg_synapse_nri.md)

## 同カテゴリ(`wiring`)

[seg_synapse_partners](seg_synapse_partners.md) · [seg_wiring_variation](seg_wiring_variation.md) · [seg_synapse_nri](seg_synapse_nri.md)

---
*Provenance: segcompare.py — EMPROOF operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
