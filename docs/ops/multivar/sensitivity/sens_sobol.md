---
op: sens_sobol
dim: multivar
category: sensitivity
in: design × signal
out: table
examples: [sensitivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# sens_sobol — MULTIVAR `sensitivity` op

- **データ種**: `design × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sens_sobol(design=None, y=None, n_boot=500, level=0.95, seed=0) -> 'dict'` (実装を直接呼ぶなら `import sensitivity; sensitivity.sens_sobol(design=None, y=None, n_boot=500, level=0.95, seed=0) -> 'dict'`、台帳から引くなら `opsmultivar.get("sens_sobol")`)

## 使い方

First-order and total Sobol' indices with bootstrap confidence intervals.

From the outputs on a :func:`doe_saltelli` design (blocks A, B, A_B^(i)):

* ``S1_i = (1/N) sum_j f(B)_j (f(A_B^(i))_j - f(A)_j) / V`` (Saltelli et al. 2010,
  Table 2 (b));
* ``ST_i = (1/(2N)) sum_j (f(A)_j - f(A_B^(i))_j)^2 / V`` (Jansen 1999; Saltelli et al.
  2010, Table 2 (f));
* ``V`` = variance of the outputs at A and B together.

S1 is the share of output variance a factor explains alone; ST adds every interaction
it takes part in. ST ~ 0 means the factor can be fixed anywhere in its range;
ST - S1 large means it acts through interactions. Confidence intervals come from
``n_boot`` bootstrap resamples of the N rows (the same row index across A, B and
A_B^(i)) at ``level``. The sum of S1 (``sum_s1``) is <= 1 up to estimation error; a value
far below 1 says interactions carry the rest.

## 詳しい使い方ガイド

- [design_of_experiments ファミリ ガイド](../guides/design_of_experiments.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sensitivity_tour](../../../../examples/sensitivity_tour.py) — `py -3.11 examples/sensitivity_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`sensitivity`)

[doe_morris](doe_morris.md) · [sens_morris](sens_morris.md) · [doe_saltelli](doe_saltelli.md)

---
*Provenance: sensitivity.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
