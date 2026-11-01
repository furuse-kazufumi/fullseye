---
op: doe_saltelli
dim: multivar
category: sensitivity
in: 
out: design
gpu: なし
examples: [sensitivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# doe_saltelli — MULTIVAR `sensitivity` op

- **データ種**: `なし` → `design`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.doe_saltelli(n=1024, factors=3, seed=0) -> 'dict'` (実装を直接呼ぶなら `import sensitivity; sensitivity.doe_saltelli(n=1024, factors=3, seed=0) -> 'dict'`、台帳から引くなら `opsmultivar.get("doe_saltelli")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Sample matrices for Sobol' indices (Saltelli et al. 2010) -> ``design`` of n (k + 2) runs.

A Sobol' sequence of dimension 2k gives two independent n x k matrices A (first k
columns) and B (last k). For each factor i, ``A_B^(i)`` is A with column i taken from
B. Rows are stacked as ``[A; B; A_B^(1); ...; A_B^(k)]`` (``meta['blocks']``), which is
the layout :func:`sens_sobol` reads.

``n`` must be a power of two: the balance properties of a Sobol' sequence hold for
2^m points, and the estimators' error behaves erratically otherwise — the op refuses
rather than silently degrading. ``seed`` scrambles the sequence (Owen scrambling via
scipy); ``seed=None`` uses the plain sequence.

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

[doe_morris](doe_morris.md) · [sens_morris](sens_morris.md) · [sens_sobol](sens_sobol.md)

---
*Provenance: sensitivity.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
