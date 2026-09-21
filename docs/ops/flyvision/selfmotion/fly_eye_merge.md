---
op: fly_eye_merge
dim: flyvision
category: selfmotion
in: table × table
out: table
examples: [poc_fly_optomotor_steering]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# fly_eye_merge — FLYVISION `selfmotion` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_eye_merge(lattice_a, lattice_b, *more)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_eye_merge(lattice_a, lattice_b, *more)`、台帳から引くなら `opsflyvision.get("fly_eye_merge")`)

## 使い方

Several lattices seen as one wide eye — the viewing directions of all of them.

:func:`fly_hex_resample` needs a lattice that fits inside one pinhole image,
which caps a single patch at well under a hemisphere. A fly is not so
limited: its two compound eyes together see almost the whole sphere, and the
wide-field cells that read self-motion out of them integrate over all of it.
This op is that integration made explicit — render each patch through its own
camera, run the pathway on each, then merge the *geometry* so that one
least-squares fit sees every ommatidium at once.

It matters more than it looks. In a naturalistic 1/f scene the response of a
correlation detector is contrast-weighted, so a narrow patch is at the mercy
of whichever few large features happen to be in it; widening the field is
what turns the estimate from a guess into a measurement (the PoC measures how
much).

lattice_a / lattice_b / *more: two or more :func:`fly_hex_lattice` results. They must
share the inter-ommatidial angle and the geometry (different spacings are
different eyes and the merged field would silently mix two sampling scales),
and no two ommatidia may look in exactly the same direction (merging a patch
with itself would double its vote without saying so).

Returns a lattice dict with the same keys plus ``"eye"``, the index of the
patch each ommatidium came from, in input order. The merged lattice is what
:func:`fly_matched_filter` and :func:`fly_egomotion_from_flow` take;
:func:`fly_hex_resample` and :func:`fly_flow_from_directions` stay per patch,
because a pinhole image and a hexagonal neighbourhood are both local.

**Raises** ``ValueError``: a malformed lattice (including a sequence handed
in where a lattice was expected), a mismatched ``dphi_rad`` or ``geometry``,
and a direction that appears twice.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_optomotor_steering](../../../../examples/poc_fly_optomotor_steering.py) — `py -3.11 examples/poc_fly_optomotor_steering.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fly_t4t5_field](../direction/fly_t4t5_field.md) · [fly_flow_from_directions](../direction/fly_flow_from_directions.md) · [fly_matched_filter](fly_matched_filter.md) · [fly_egomotion_from_flow](fly_egomotion_from_flow.md) · [fly_hex_resample](../sample/fly_hex_resample.md) · [fly_hs_readout](../integrate/fly_hs_readout.md)

## 同カテゴリ(`selfmotion`)

[fly_matched_filter](fly_matched_filter.md) · [fly_egomotion_from_flow](fly_egomotion_from_flow.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
