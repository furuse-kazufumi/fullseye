---
op: conv_observed_order
dim: converge
category: verification
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# conv_observed_order — CONVERGE `verification` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.conv_observed_order(phi=None, h=None, r=None, n_cells=None, dim=None) -> 'dict'` (実装を直接呼ぶなら `import converge; converge.conv_observed_order(phi=None, h=None, r=None, n_cells=None, dim=None) -> 'dict'`、台帳から引くなら `opsconverge.get("conv_observed_order")`)

## 使い方

Apparent order of convergence p from three systematically refined solutions (Celik et al. 2008, eq. 3).

``phi`` = (phi1, phi2, phi3) on grids 1 (finest) .. 3 (coarsest). The refinement is given
by exactly one of ``h`` = (h1, h2, h3) representative cell sizes, ``r`` = (r21, r32) with
r21 = h2/h1 and r32 = h3/h2, or ``n_cells`` = (N1, N2, N3) with ``dim`` (h from Celik eqs.
(1)-(2)). With eps32 = phi3 - phi2 and eps21 = phi2 - phi1 (Step 3):

    p = |ln|eps32/eps21| + q(p)| / ln(r21)                       (3a)
    q(p) = ln((r21^p - s) / (r32^p - s))                          (3b)
    s = sign(eps32 / eps21)                                       (3c)

solved by fixed-point iteration from the first term (q = 0) with :func:`iterate_fixed_point`
(plain, as the paper prescribes; |p_k+1 - p_k| <= 1e-13, at most 1000 steps). q = 0 when r is constant. s = -1 flags **oscillatory
convergence** (reported, not refused — Celik keeps the absolute values so the extrapolation
goes toward h = 0).

**Refusal**: eps21 or eps32 "very close" to zero (|eps| <= 1e-12 * max|phi|) — Celik: the
procedure does not work there (oscillation or an exact solution; refine further) — and a
fixed-point iteration for p that does not converge.

Defaults: the first column of Celik et al. 2008 Table 1 (p = 1.53).

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

## 同カテゴリ(`verification`)

[conv_gci](conv_gci.md)

---
*Provenance: converge.py — CONVERGE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
