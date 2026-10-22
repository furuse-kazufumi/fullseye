---
op: iterate_fixed_point
dim: converge
category: iterate
in: 
out: table
examples: [converge_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# iterate_fixed_point — CONVERGE `iterate` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.iterate_fixed_point(g='cos', x0=None, method='anderson', tol=1e-10, rtol=0.0, max_iter=500, m=5, on_fail='raise', keep_iterates=False) -> 'dict'` (実装を直接呼ぶなら `import converge; converge.iterate_fixed_point(g='cos', x0=None, method='anderson', tol=1e-10, rtol=0.0, max_iter=500, m=5, on_fail='raise', keep_iterates=False) -> 'dict'`、台帳から引くなら `opsconverge.get("iterate_fixed_point")`)

## 使い方

Solve x = g(x) by fixed-point iteration (plain / Aitken / Anderson) and refuse if it does not converge.

``g`` is a callable mapping an iterate (scalar or array) to one of the same shape, or the
name of a built-in example (``"cos"``: x = cos x, x0 = 1, fixed point 0.7390851332...).
The residual is f_k = g(x_k) - x_k and the run has converged when
``||f_k|| <= tol + rtol * ||x_k||`` (2-norm). The value returned is g(x_k).

``method``:

* ``"plain"``    x_{k+1} = g(x_k) — the bounce-by-bounce Neumann sum for a linear map.
* ``"aitken"``   Aitken's delta-squared on x, g(x), g(g(x)) per step (Steffensen form),
  component-wise; a component whose second difference vanishes takes g(g(x)).
* ``"anderson"`` Anderson acceleration (Walker & Ni 2011, Algorithm AA) with memory ``m``,
  written as their eq. (3.1): gamma = argmin ||f_k - dF_k gamma||_2 with
  dF_k = (f_{k-m_k+1} - f_{k-m_k}, ..., f_k - f_{k-1}), then
  x_{k+1} = g(x_k) - dG_k gamma (dG holds the same differences of g). The least-squares
  problem is solved by a QR factorisation; while cond(R) > ``ANDERSON_COND_MAX`` (1e8) the left-most
  (oldest) column is dropped (section 4 of Walker & Ni, after Yang et al.). On a linear
  map with no columns dropped this reproduces GMRES (their Theorem 2.2): the gates check it.

Returned (a table dict): ``x`` (g(x_k)), ``converged``, ``n_iter``, ``n_evals`` (calls of g),
``residual_history`` (||f_k|| per iterate), ``lipschitz_estimate`` (largest secant ratio
of g over the stored iterates), ``error_estimate`` = L/(1-L) * ||f_k|| — the a-posteriori
contraction bound on |g(x_k) - x*|, ``None`` when the estimated L is not below 1 —
``columns_dropped`` (Anderson conditioning) and ``method``.

**Refusal**: divergence (non-finite residual or growth by ``DIVERGENCE_FACTOR`` = 1e8),
a period-2 oscillation, stagnation or running out of ``max_iter`` raises
:class:`NotConvergedError` (a ``MetricContractError``) with the record attached. With
``on_fail="record"`` the record is returned instead, with ``x = None`` and the last
iterate under ``last_iterate`` — never under ``x``.

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

## 同カテゴリ(`iterate`)

—

---
*Provenance: converge.py — CONVERGE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
