---
op: mv_pls
dim: multivar
category: analysis
in: matrix × signal
out: table
examples: [multivar_inspection_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# mv_pls — MULTIVAR `analysis` op

- **データ種**: `matrix × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mv_pls(X=None, Y=None, n_components=None, max_components=10, cv=7, method='nipals', standardize=True) -> 'dict'` (実装を直接呼ぶなら `import multivar; multivar.mv_pls(X=None, Y=None, n_components=None, max_components=10, cv=7, method='nipals', standardize=True) -> 'dict'`、台帳から引くなら `opsmultivar.get("mv_pls")`)

## 使い方

Partial least squares regression of Y on X with cross-validated Q^2, the Q^2 rule and VIP.

PLS finds directions in X that both vary and predict Y — the tool for many
correlated predictors and few runs (image features -> process settings, or the
reverse). ``method="nipals"`` (default, Wold, Sjöström & Eriksson 2001) or
``"simpls"`` (de Jong 1993; identical to NIPALS for a single response — a test pins
it). X and Y are centred and, by default, scaled to unit variance.

Q^2 is computed by ``cv``-fold cross-validation with interleaved folds (run i in fold
i mod cv, as in SIMCA's default of 7 groups): ``Q^2_a = 1 - PRESS_a / SS_{a-1}`` per
component (``SS_0`` = total sum of squares of Y, ``SS_{a-1}`` the residual sum of
squares with a-1 components), cumulative ``Q^2 = 1 - PRESS_A / SS_0``.
``n_components=None`` keeps adding components while ``Q^2_a >= 0.0975``
(= 1 - 0.95^2; Wold et al. 2001) up to ``max_components``; if not even the first
passes, one component is fitted and ``significant`` is False — the data then do not
support a predictive model, and the coefficients should not be used.

VIP (variable importance in projection) ranks X columns; the conventional threshold
is VIP > 1. ``coef`` / ``intercept`` predict Y in its original units from X in its
original units.

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

[mv_pca](mv_pca.md) · [rsm_fit](rsm_fit.md) · [doe_main_effects](doe_main_effects.md)

---
*Provenance: multivar.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
