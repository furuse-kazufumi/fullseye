---
op: seg_wiring_variation
dim: emproof
category: wiring
in: labels2d × labels2d × table
out: table
examples: [poc_em_wiring_errors]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# seg_wiring_variation — EMPROOF `wiring` op

- **データ種**: `labels2d × labels2d × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_wiring_variation(a, b, synapses, spacing=None, background=0)` (実装を直接呼ぶなら `import segcompare; segcompare.seg_wiring_variation(a, b, synapses, spacing=None, background=0)`、台帳から引くなら `opsemproof.get("seg_wiring_variation")`)

## 使い方

How a candidate segmentation ``b`` corrupts the wiring diagram of truth ``a``, in bits.

Two levels, both VOI split / merge (``synapses`` as in :func:`seg_synapse_partners`):

  * **synapse ends** (``split`` / ``merge``, ``voi``): the segmentation VOI measured only
    at the ``2n`` synapse ends instead of every pixel. ``split`` = two ends on one true
    neuron now on different objects (the neuron was cut between its synapses); ``merge``
    = ends on different true neurons now on one object (they were glued). Cutting a
    neuron whose ``s`` ends divide ``s1`` / ``s2`` raises ``split`` by exactly
    ``(s / 2n)·H2(s1 / s)``. Pixels far from any synapse cost nothing here.
  * **connections** (``connection_split`` / ``connection_merge``): synapses grouped by
    their (pre object, post object) pair — one true connection scattered over several,
    or different true connections fused into one (synapses attributed to the wrong
    partner). A connection with a single synapse cannot scatter, so this level is blind
    to cuts that only rename a one-synapse connection; the ends level is not.

Provenance: the ends level is the "synapse VI" of Plaza, Scheffer & Chklovskii 2014
(*Focused proofreading*, arXiv:1409.1199; VI over the voxels carrying synaptic
annotations, implemented in NeuroProof, C++). The connection level, the lost-synapse
convention and the per-edit closed forms (``(s/2n)·H2(s1/s)`` for a cut) are this module's. Synapses with an end on
``background`` in the truth are dropped; in the candidate, each such synapse is **lost**
and counted in ``n_lost`` as its own singleton at both levels (not one shared
"background" object, which would fake a huge merge). Also returns ``split_connections`` (true connections
spread over 2+ candidate ones), ``merged_connections`` (candidate connections holding
synapses of 2+ true ones), ``edges_a`` / ``edges_b`` and ``n`` (synapses scored).

**Raises** ``ValueError``: as :func:`seg_synapse_partners`; shapes of ``a`` and ``b``
differ; no synapse left after dropping background in the truth.

## 詳しい使い方ガイド

- [emproof ファミリ ガイド](../guides/emproof.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_em_wiring_errors](../../../../examples/poc_em_wiring_errors.py) — `py -3.11 examples/poc_em_wiring_errors.py`

## 型が繋がる次の op(`table` を入力に取れる)

[seg_synapse_partners](seg_synapse_partners.md) · [seg_synapse_nri](seg_synapse_nri.md) · [seg_wiring_exposure](seg_wiring_exposure.md)

## 同カテゴリ(`wiring`)

[seg_synapse_partners](seg_synapse_partners.md) · [seg_synapse_nri](seg_synapse_nri.md) · [seg_wiring_exposure](seg_wiring_exposure.md)

---
*Provenance: segcompare.py — EMPROOF operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
