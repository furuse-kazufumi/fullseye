---
op: doe_main_effects
dim: multivar
category: analysis
in: design × signal
out: table
examples: [multivar_inspection_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# doe_main_effects — MULTIVAR `analysis` op

- **データ種**: `design × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.doe_main_effects(design=None, y=None, goal='larger') -> 'dict'` (実装を直接呼ぶなら `import multivar; multivar.doe_main_effects(design=None, y=None, goal='larger') -> 'dict'`、台帳から引くなら `opsmultivar.get("doe_main_effects")`)

## 使い方

Level means per factor — the response table of a designed experiment — with dispersion and SN.

``y`` is (n,) or (n, r) with r repeated measurements (or noise-array conditions) per
run. For each factor and level: the mean of y (location), the mean of log s over the
runs at that level (dispersion, needs r >= 2), the main-effect range (max - min of the
level means) and its share of the total sum of squares.

SN ratios are computed per run (Taguchi): larger-the-better
``-10 log10(mean(1/y^2))`` (the same formula as ``spc.spc_mt_sn_ratio``, reused),
smaller-the-better ``-10 log10(mean(y^2))``, nominal-the-best ``10 log10(ybar^2/s^2)``,
and their level means are reported in ``sn``. **They are not the basis of the
recommended levels**: an SN ratio mixes location and dispersion in one number, and a
level can raise it by lowering the mean (Box 1988; Nair 1992). ``best_levels`` chooses
from the location table by ``goal`` (``"larger"``, ``"smaller"``, or ``"nominal"`` —
which picks the levels of smallest dispersion and leaves the mean to an adjustment
factor), and ``sn_agrees`` says where the SN table would have chosen differently.

## 詳しい使い方ガイド

- [design_of_experiments ファミリ ガイド](../guides/design_of_experiments.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [multivar_inspection_tour](../../../../examples/multivar_inspection_tour.py) — `py -3.11 examples/multivar_inspection_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`analysis`)

[mv_pca](mv_pca.md) · [mv_pls](mv_pls.md) · [rsm_fit](rsm_fit.md)

---
*Provenance: multivar.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
