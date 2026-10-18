---
op: rsm_fit
dim: multivar
category: analysis
in: design × signal
out: table
examples: [multivar_inspection_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# rsm_fit — MULTIVAR `analysis` op

- **データ種**: `design × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.rsm_fit(design=None, y=None, model='quadratic') -> 'dict'` (実装を直接呼ぶなら `import multivar; multivar.rsm_fit(design=None, y=None, model='quadratic') -> 'dict'`、台帳から引くなら `opsmultivar.get("rsm_fit")`)

## 使い方

Fit a response surface on a ``design`` (coded units): ANOVA, lack of fit, stationary point.

``model``: ``"linear"`` (b0 + sum b_i x_i), ``"interaction"`` (+ b_ij x_i x_j) or
``"quadratic"`` (+ b_ii x_i^2) — fitted by least squares on the **coded** matrix of
the design (so coefficients are comparable across factors).

**Refuses a model the plan cannot support**: if the model matrix is rank-deficient
(a two-level plan cannot see x^2 — every x_i^2 equals the intercept; a resolution III
fraction cannot separate a main effect from a two-factor interaction) the op raises
``ValueError`` naming the aliased terms, instead of returning one of infinitely many
least-squares solutions. It also needs more runs than terms (a residual to judge with).

Returns coefficients with standard errors and t, the ANOVA (model / residual and, when
the plan has replicated points, lack of fit vs pure error with its F test), R^2,
adjusted R^2, predicted R^2 (from PRESS). For the quadratic model, the stationary
point x_s = -B^{-1} b / 2 (B symmetric with b_ii on the diagonal and b_ij/2 off it) in
coded and natural units, the predicted response there, the eigenvalues of B
(canonical analysis: all negative = maximum, all positive = minimum, mixed = saddle,
any near zero = ridge) and whether x_s lies inside the explored region.

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

[mv_pca](mv_pca.md) · [mv_pls](mv_pls.md) · [doe_main_effects](doe_main_effects.md)

---
*Provenance: multivar.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
