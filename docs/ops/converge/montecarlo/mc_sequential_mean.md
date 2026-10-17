---
op: mc_sequential_mean
dim: converge
category: montecarlo
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# mc_sequential_mean — CONVERGE `montecarlo` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.mc_sequential_mean(sampler='pi', tol=0.01, rel_tol=0.0, confidence=0.95, batch=4096, max_samples=4000000, seed=0, on_fail='raise') -> 'dict'` (実装を直接呼ぶなら `import converge; converge.mc_sequential_mean(sampler='pi', tol=0.01, rel_tol=0.0, confidence=0.95, batch=4096, max_samples=4000000, seed=0, on_fail='raise') -> 'dict'`、台帳から引くなら `opsconverge.get("mc_sequential_mean")`)

## 使い方

Sequential Monte Carlo mean: add samples until the confidence interval is narrower than the tolerance.

``sampler(rng, n)`` returns n i.i.d. samples (a 1-D array) — or the built-in ``"pi"``
(4 * [u^2 + v^2 <= 1], mean pi). Batch b is drawn from ``default_rng((seed, b))``, so the
result is reproducible and does not depend on how many batches came before.

Stops at the first batch boundary, from the second batch on, where the half-width
z * s / sqrt(n) <= ``tol`` + ``rel_tol`` * |mean| (z from ``confidence``; s the running
sample standard deviation). This is the fixed-width sequential interval of Chow & Robbins
1965; never stopping inside the first two batches guards against an early, accidentally
small variance (raise ``batch`` to guard more) — the actual coverage is checked by the
gates, not assumed.

Returns ``mean``, ``se``, ``ci`` (lower, upper), ``half_width``, ``n_samples`` (used),
``converged`` and ``history`` (n, mean, se per batch). **Refusal**: ``max_samples`` reached
first raises ``NotConvergedError`` (``on_fail="record"`` returns the record with
``mean = None`` and the running values under ``last_mean`` / ``last_se``).

## 詳しい使い方ガイド

- [convergent_computation ファミリ ガイド](../guides/convergent_computation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`montecarlo`)

[mc_photon_slab](mc_photon_slab.md)

---
*Provenance: converge.py — CONVERGE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
