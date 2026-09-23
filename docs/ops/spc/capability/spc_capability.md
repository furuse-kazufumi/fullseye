---
op: spc_capability
dim: spc
category: capability
in: signal
out: table
examples: [poc_spc]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# spc_capability — SPC `capability` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spc_capability(signal, lsl, usl, sigma=None)` (実装を直接呼ぶなら `import spc; spc.spc_capability(signal, lsl, usl, sigma=None)`、台帳から引くなら `opsspc.get("spc_capability")`)

## 使い方

Process capability indices Cp and Cpk from measurements and spec limits.

``signal`` is a 1-D series of individual measurements; ``lsl`` / ``usl`` are the
lower / upper specification limits (``lsl < usl``). With the sample mean ``mu``
and standard deviation ``sigma`` (sample std, ``ddof=1``, unless one is passed
in explicitly)::

    Cp  = (USL - LSL) / (6 sigma)
    Cpk = min(USL - mu, mu - LSL) / (3 sigma)

Returns a dict with ``mean`` / ``std`` / ``cp`` / ``cpk`` and the echoed spec
limits and midpoint. ``Cpk <= Cp`` always, with equality exactly when the
process is centred (``mu`` at the spec midpoint) — pinned in the tests.

**Raises** ``ValueError``: a non-1-D / empty *signal*, fewer than two points
(no spread to estimate), ``lsl >= usl``, non-finite limits, or a non-positive
standard deviation (a constant series has no capability to report).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_spc](../../../../examples/poc_spc.py) — `py -3.11 examples/poc_spc.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`capability`)

—

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
