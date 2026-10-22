---
op: mc_photon_slab
dim: converge
category: montecarlo
in: 
out: table
examples: [converge_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# mc_photon_slab — CONVERGE `montecarlo` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.mc_photon_slab(layers=None, n_above=1.0, n_below=1.0, n_photons=100000, tol=None, confidence=0.95, batch=50000, seed=1, w_threshold=0.0001, roulette_m=10) -> 'dict'` (実装を直接呼ぶなら `import mcphoton; mcphoton.mc_photon_slab(layers=None, n_above=1.0, n_below=1.0, n_photons=100000, tol=None, confidence=0.95, batch=50000, seed=1, w_threshold=0.0001, roulette_m=10) -> 'dict'`、台帳から引くなら `opsconverge.get("mc_photon_slab")`)

## 使い方

Diffuse reflectance, total transmittance and absorption of a layered turbid slab by MCML-type Monte Carlo, with confidence intervals.

``layers``: list of ``{"n", "mua", "mus", "g", "d"}`` from the top (coefficients in 1/length,
thickness in the same length; ``d = inf`` for a semi-infinite last layer). ``n_above`` /
``n_below``: ambient refractive indices. A pencil beam enters at normal incidence.

The tracing rules are those of the MCML manual (Wang & Jacques), eqs. 3.2a-3.31 — see the
module docstring for which equation does what. Every packet's contribution is kept, so the
standard error is the sample standard deviation over packets / sqrt(N) and the interval is
mean +- z se (``confidence``). Batch b uses ``default_rng((seed, b))``.

* ``tol=None``: trace ``n_photons`` packets.
* ``tol=h``: sequential Monte Carlo — add batches of ``batch`` packets until the
  half-width of R_d and of T_t is <= h (the stopping rule of ``converge``, from the second
  batch on), with ``n_photons`` as the budget: refusing (``NotConvergedError``) if the
  budget is spent first.

Returns ``Rd``, ``Tt``, ``A`` (absorbed fraction) and ``A_layers``, each with ``*_se`` and
``*_ci``; ``Rsp`` (specular, deterministic: eq. 3.2a); ``energy_balance`` = R_sp + R_d +
T_t + A (1 in expectation — roulette conserves energy only on average, so its deviation is
compared with its own standard error); ``R_total`` = R_sp + R_d (specular plus diffuse, with
the interval of R_d shifted by the deterministic R_sp); ``n_photons``. Defaults: the MCML manual Table 6.1
slab (van de Hulst: R_d = 0.09739, T_t = 0.66096); ``MCML_TABLE_6_2`` holds Table 6.2.

## 詳しい使い方ガイド

- [convergent_computation ファミリ ガイド](../guides/convergent_computation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [converge_tour](../../../../examples/converge_tour.py) — `py -3.11 examples/converge_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`montecarlo`)

[mc_sequential_mean](mc_sequential_mean.md)

---
*Provenance: mcphoton.py — CONVERGE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
