---
op: sens_morris
dim: multivar
category: sensitivity
in: design × signal
out: table
examples: [sensitivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# sens_morris — MULTIVAR `sensitivity` op

- **データ種**: `design × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sens_morris(design=None, y=None, negligible=0.05) -> 'dict'` (実装を直接呼ぶなら `import sensitivity; sensitivity.sens_morris(design=None, y=None, negligible=0.05) -> 'dict'`、台帳から引くなら `opsmultivar.get("sens_morris")`)

## 使い方

Morris elementary effects -> mu, mu*, sigma per factor (Morris 1991; mu* Campolongo et al. 2007).

``design`` must come from :func:`doe_morris` (its trajectory bookkeeping is used) and
``y`` holds the model output for its rows in order. For trajectory t and step s that
moves factor i by ±delta: ``EE_i = (y_s - y_{s-1}) / (±delta)`` in unit-cube units, and
also per natural unit of the factor (``ee_natural``; on a log-scale factor the step
is in log10 units).

``mu`` (mean EE) can cancel when effects change sign; ``mu_star`` (mean |EE|) does
not and is the ranking measure; ``sigma`` (standard deviation, ddof = 1) is large when
the effect depends on where the other factors are (non-linear or interacting).
``class`` per factor: ``negligible`` (mu* below ``negligible`` x the largest mu*),
``linear/additive`` (sigma < 0.1 mu*: the effect is the same everywhere — a
convention of this op, stated), otherwise ``non-linear or interacting``.

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

[doe_morris](doe_morris.md) · [doe_saltelli](doe_saltelli.md) · [sens_sobol](sens_sobol.md)

---
*Provenance: sensitivity.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
