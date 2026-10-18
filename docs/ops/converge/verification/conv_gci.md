---
op: conv_gci
dim: converge
category: verification
in: 
out: table
examples: [converge_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# conv_gci — CONVERGE `verification` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.conv_gci(phi=None, h=None, r=None, n_cells=None, dim=None, safety_factor=1.25) -> 'dict'` (実装を直接呼ぶなら `import converge; converge.conv_gci(phi=None, h=None, r=None, n_cells=None, dim=None, safety_factor=1.25) -> 'dict'`、台帳から引くなら `opsconverge.get("conv_gci")`)

## 使い方

Grid convergence index of the finest solution: Celik et al. 2008 procedure, eqs. (1)-(7).

Takes the same inputs as :func:`conv_observed_order` (three solutions, finest first, and
the refinement) and returns, with p from eq. (3):

    phi_ext21 = (r21^p phi1 - phi2) / (r21^p - 1)                  (4)   (and phi_ext32)
    e_a21     = |(phi1 - phi2) / phi1|                            (5)
    e_ext21   = |(phi_ext12 - phi1) / phi_ext12|                   (6)
    GCI_fine21 = 1.25 e_a21 / (r21^p - 1)                         (7)

(``safety_factor`` = 1.25 as in eq. (7)). Fractions and percentages are both returned, and
``report`` reads "phi1 +- GCI". Note what the GCI is not: it bounds the discretization
error of the fine solution only — "this does not account for modeling errors" (Celik).

Refusal as in :func:`conv_observed_order`, plus phi1 = 0 or phi_ext = 0 (relative errors
undefined). Defaults: Celik Table 1, first column (GCI 2.2 %).

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

## 同カテゴリ(`verification`)

[conv_observed_order](conv_observed_order.md)

---
*Provenance: converge.py — CONVERGE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
