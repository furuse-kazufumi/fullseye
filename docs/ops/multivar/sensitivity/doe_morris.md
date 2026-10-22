---
op: doe_morris
dim: multivar
category: sensitivity
in: 
out: design
examples: [sensitivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# doe_morris — MULTIVAR `sensitivity` op

- **データ種**: `なし` → `design`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.doe_morris(r=10, factors=4, levels=4, seed=0, n_candidates=0) -> 'dict'` (実装を直接呼ぶなら `import sensitivity; sensitivity.doe_morris(r=10, factors=4, levels=4, seed=0, n_candidates=0) -> 'dict'`、台帳から引くなら `opsmultivar.get("doe_morris")`)

## 使い方

Morris one-at-a-time screening plan: ``r`` trajectories of k+1 runs -> ``design``.

Each trajectory starts at a random point of the ``levels``-level grid on the unit
cube and moves one factor at a time by delta = levels / (2 (levels - 1)) (Morris
1991; with an even ``levels`` every grid level is equally likely to be visited),
so r (k+1) runs give r elementary effects per factor. ``n_candidates > r`` draws that
many trajectories and keeps r of them that are spread out: the trajectory distance
of Campolongo et al. 2007 (sum over point pairs of their Euclidean distances), chosen
greedily — a pair of the farthest trajectories first, then repeatedly the trajectory
that adds the most distance (an approximation of their exhaustive search, stated in
``meta['selection']``).

The coded matrix is 2u - 1 of the unit-cube points; ``meta`` keeps the trajectory
bookkeeping that :func:`sens_morris` needs (``changed`` factor and ``sign`` per step).

## 詳しい使い方ガイド

- [design_of_experiments ファミリ ガイド](../guides/design_of_experiments.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sensitivity_tour](../../../../examples/sensitivity_tour.py) — `py -3.11 examples/sensitivity_tour.py`

## 型が繋がる次の op(`design` を入力に取れる)

[doe_decode](../coding/doe_decode.md) · [rsm_fit](../analysis/rsm_fit.md) · [doe_main_effects](../analysis/doe_main_effects.md) · [sens_morris](sens_morris.md) · [sens_sobol](sens_sobol.md)

## 同カテゴリ(`sensitivity`)

[sens_morris](sens_morris.md) · [doe_saltelli](doe_saltelli.md) · [sens_sobol](sens_sobol.md)

---
*Provenance: sensitivity.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
