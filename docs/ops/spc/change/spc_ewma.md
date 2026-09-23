---
op: spc_ewma
dim: spc
category: change
in: signal
out: table
examples: [poc_spc]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# spc_ewma — SPC `change` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spc_ewma(signal, target, lam=0.2, L=3.0, sigma=None)` (実装を直接呼ぶなら `import spc; spc.spc_ewma(signal, target, lam=0.2, L=3.0, sigma=None)`、台帳から引くなら `opsspc.get("spc_ewma")`)

## 使い方

EWMA control chart for individual measurements (Roberts 1959).

``signal`` is a 1-D series of individual measurements. With a reference value
``target`` (the in-control mean), a smoothing constant ``lam`` in ``(0, 1]`` and
a control-limit width ``L`` (in sigmas), the exponentially weighted moving
average and its time-varying limits are::

    z_i  = lam * x_i + (1 - lam) * z_{i-1},          z_0 = target
    var_i = sigma^2 * (lam / (2 - lam)) * (1 - (1 - lam) ** (2 (i + 1)))
    UCL_i / LCL_i = target +/- L * sqrt(var_i)

``sigma`` is the process standard deviation; if ``None`` it is estimated from the
series as the sample std (``ddof=1``). The limits widen from the first sample to
the asymptote ``target +/- L * sigma * sqrt(lam / (2 - lam))``. EWMA, like CUSUM,
catches small sustained shifts that a single-point Shewhart chart misses; ``lam``
trades memory (small = long memory, sensitive to small shifts) against speed.

Returns a dict with the ``z`` / ``ucl`` / ``lcl`` arrays, the integer ``alarms``
indices (``z_i`` outside its limits), the first alarm index (or ``-1``), the
asymptotic ``ucl_inf`` / ``lcl_inf``, and the echoed ``target`` / ``lam`` / ``L``
/ ``sigma`` / ``in_control``.

Ground truth (pinned in the tests): a series constant at ``target`` keeps
``z == target`` with no alarm; ``z`` is exactly the recursion above; ``ucl``
increases monotonically toward ``ucl_inf``; with ``lam = 1`` the chart reduces to
a Shewhart individuals chart (``z == x``, limits constant at ``target +/- L
sigma``).

**Raises** ``ValueError``: a non-1-D / empty *signal*, a non-finite
*target* / *lam* / *L*, ``lam`` outside ``(0, 1]``, a non-positive *L*, a
non-finite or non-positive *sigma*, or (when estimating) a constant series whose
sample std is zero.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_spc](../../../../examples/poc_spc.py) — `py -3.11 examples/poc_spc.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`change`)

[spc_cusum](spc_cusum.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
