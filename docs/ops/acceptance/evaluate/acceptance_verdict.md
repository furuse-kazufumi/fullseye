---
op: acceptance_verdict
dim: acceptance
category: evaluate
in: table × table
out: table
gpu: なし
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# acceptance_verdict — ACCEPTANCE `evaluate` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.acceptance_verdict(results, mpe)` (実装を直接呼ぶなら `import acceptance3d; acceptance3d.acceptance_verdict(results, mpe)`、台帳から引くなら `opsacceptance.get("acceptance_verdict")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

評価量の表を MPE(最大許容誤差)と比べて合否を出す(``table``)。

Compare acceptance results with maximum permissible errors. ``results`` holds lists (one value per
position) under any of ``pf``, ``ps``, ``sd``, ``f`` (the shape :func:`virtual_acceptance_test`
returns; measured values may be assembled by hand). ``mpe`` gives a positive limit per quantity.
A quantity passes when ``max |value| <= mpe`` (PF and F are non-negative by definition).

返す ``dict``: ``passed``(全体)、``by_quantity``(量ごとに ``worst``・``worst_index``・``mpe``・``ratio``・
``passed``)、``decided_by``(``ratio`` が最大の量 = 合否を決めた量)、``max_ratio``。
★MPE の値は規格ではなく**メーカーの仕様**が決める(この op は数字を持たない)。

**Raises** ``ValueError``: ``results``・``mpe`` が dict でない、共通の量が 1 つも無い、値が空・非有限、
MPE が正でない、未知の量の名前。

## 詳しい使い方ガイド

- [optical_3d_acceptance ファミリ ガイド](../guides/optical_3d_acceptance.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[acceptance_scan](../simulate/acceptance_scan.md) · [virtual_acceptance_test](../simulate/virtual_acceptance_test.md) · [acceptance_error_budget](../budget/acceptance_error_budget.md)

## 同カテゴリ(`evaluate`)

[sphere_probing_error](sphere_probing_error.md) · [sphere_spacing_error](sphere_spacing_error.md) · [plane_flatness_error](plane_flatness_error.md)

---
*Provenance: acceptance3d.py — ACCEPTANCE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
