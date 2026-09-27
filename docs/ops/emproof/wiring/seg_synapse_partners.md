---
op: seg_synapse_partners
dim: emproof
category: wiring
in: labels2d × table
out: table
examples: [poc_em_wiring_errors]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# seg_synapse_partners — EMPROOF `wiring` op

- **データ種**: `labels2d × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_synapse_partners(labels, synapses, spacing=None, background=0)` (実装を直接呼ぶなら `import segcompare; segcompare.seg_synapse_partners(labels, synapses, spacing=None, background=0)`、台帳から引くなら `opsemproof.get("seg_synapse_partners")`)

## 使い方

Read the wiring diagram a segmentation implies: which object each synapse connects.

``synapses`` is a table ``{"pre": (n, ndim), "post": (n, ndim)}`` (or an ``(n, 2, ndim)``
array) holding the two ends of ``n`` synapses in physical units (divided by ``spacing`` per axis, default 1, then floored to a voxel).
Returns ``pre_ids`` / ``post_ids`` (the object under each end), ``connection`` (index
of each synapse's connection in ``edges``), ``edges`` (``(k, 2)`` distinct
(pre object, post object) pairs), ``synapses_per_edge``, ``n_background`` (synapses
with an end on ``background``) and ``n_autapse`` (both ends in the same non-background
object — a merge, or a real autapse).

**Raises** ``ValueError``: bad labels (as :func:`seg_contingency`); ``synapses`` not a
table with ``pre`` / ``post`` nor an ``(n, 2, ndim)`` array; points not ``(n, ndim)``, non-finite, of different counts or outside the volume; bad spacing.

## 詳しい使い方ガイド

- [emproof ファミリ ガイド](../guides/emproof.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_em_wiring_errors](../../../../examples/poc_em_wiring_errors.py) — `py -3.11 examples/poc_em_wiring_errors.py`

## 型が繋がる次の op(`table` を入力に取れる)

[seg_wiring_variation](seg_wiring_variation.md) · [seg_synapse_nri](seg_synapse_nri.md)

## 同カテゴリ(`wiring`)

[seg_wiring_variation](seg_wiring_variation.md) · [seg_synapse_nri](seg_synapse_nri.md)

---
*Provenance: segcompare.py — EMPROOF operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
