---
op: spc_mt_distance
dim: spc
category: mt
in: matrix
out: table
examples: [poc_mt_hidden_fault, poc_spc]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# spc_mt_distance — SPC `mt` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spc_mt_distance(data, mean=None, std=None, inv_corr=None, threshold=3.0)` (実装を直接呼ぶなら `import spc; spc.spc_mt_distance(data, mean=None, std=None, inv_corr=None, threshold=3.0)`、台帳から引くなら `opsspc.get("spc_mt_distance")`)

## 使い方

Score observations against an MT-method unit space.

``data`` is a 2-D array of shape ``(m, p)``. Pass the ``mean``, ``std`` and
``inv_corr`` from :func:`spc_mt_unit_space` to score new product against a
stored unit space; omit all three and the unit space is built from ``data``
itself, which is the training case and makes ``md_sq_mean`` land on
``(m-1)/m``.

Each row's distance is ``MD_i = sqrt(z_i' R^-1 z_i / p)`` with
``z_i = (x_i - mean) / std``. Rows with ``MD > threshold`` are reported in
``flagged``; the rest in ``inside``. Dividing the quadratic form by ``p`` is
what puts the unit space at 1 regardless of how many features are used, so a
threshold carries over when features are added or removed.

Returns a dict with the per-row ``md`` and ``md_sq`` arrays, ``flagged``,
``inside``, the ``threshold``, ``md_sq_mean``, and ``n``/``p``.

Relationship to :func:`spc_hotelling_t2` (used as the oracle in the tests):
on the standardised matrix the covariance *is* the correlation, so
``md**2 == t2 / p`` exactly for the same data.

**Raises** ``ValueError``: a non-2-D / empty *data*, a non-positive
``threshold``, a unit space given only in part, a ``mean`` / ``std`` /
``inv_corr`` whose shape disagrees with ``p``, a non-positive entry in
``std``, or non-finite input.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_mt_hidden_fault](../../../../examples/poc_mt_hidden_fault.py) — `py -3.11 examples/poc_mt_hidden_fault.py`
- [poc_spc](../../../../examples/poc_spc.py) — `py -3.11 examples/poc_spc.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`mt`)

[spc_mt_unit_space](spc_mt_unit_space.md) · [spc_mt_sn_ratio](spc_mt_sn_ratio.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
