---
op: doe_decode
dim: multivar
category: coding
in: design
out: matrix
examples: [doe_plan_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# doe_decode — MULTIVAR `coding` op

- **データ種**: `design` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.doe_decode(design=None, coded=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import doe; doe.doe_decode(design=None, coded=None) -> 'np.ndarray'`、台帳から引くなら `opsmultivar.get("doe_decode")`)

## 使い方

``design`` -> natural-unit matrix (n, k); or decode any coded point(s) with its ranges.

``coded=None`` returns the design's natural matrix recomputed from its coded matrix
(so a hand-edited ``natural`` cannot drift from ``coded``). Pass ``coded`` (k,) or
(m, k) — e.g. a stationary point from :func:`multivar.rsm_fit` — to map it to bench
settings with the same ranges and scales.

## 詳しい使い方ガイド

- [design_of_experiments ファミリ ガイド](../guides/design_of_experiments.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [doe_plan_tour](../../../../examples/doe_plan_tour.py) — `py -3.11 examples/doe_plan_tour.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[doe_encode](doe_encode.md)

## 同カテゴリ(`coding`)

[doe_encode](doe_encode.md)

---
*Provenance: doe.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
