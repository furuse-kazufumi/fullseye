---
op: spc_xbar_r
dim: spc
category: chart
in: matrix
out: table
examples: [poc_spc]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# spc_xbar_r — SPC `chart` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spc_xbar_r(subgroups)` (実装を直接呼ぶなら `import spc; spc.spc_xbar_r(subgroups)`、台帳から引くなら `opsspc.get("spc_xbar_r")`)

## 使い方

Shewhart Xbar-R control chart from subgroup measurements.

``subgroups`` is a 2-D array of shape ``(m, n)`` — ``m`` subgroups of ``n``
measurements each, ``2 <= n <= 10`` (the range chart is only calibrated for
small subgroups). For each subgroup ``j`` the plotted statistics are the mean
``Xbar_j`` and the range ``R_j = max - min``. The centre lines are the grand
mean ``Xbarbar`` and the mean range ``Rbar``, and with the ISO 8258 constants
``(A2, D3, D4)`` for that ``n``::

    xbar_ucl = Xbarbar + A2*Rbar   xbar_lcl = Xbarbar - A2*Rbar
    r_ucl    = D4*Rbar             r_lcl    = D3*Rbar

Returns a dict (a "table") with the per-subgroup ``xbar`` / ``r`` arrays, the
six limits and three centre lines, the integer indices ``out_of_control`` of
subgroups outside either chart, and ``in_control`` (True when that list is
empty). The constants are fixed by ``n``: for ``n=5`` they are exactly
``A2=0.577, D3=0.000, D4=2.115`` (pinned in the tests).

**Raises** ``ValueError``: a non-2-D / empty *subgroups*, a subgroup size
outside ``[2, 10]``, or non-finite / mislabelled input.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_spc](../../../../examples/poc_spc.py) — `py -3.11 examples/poc_spc.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`chart`)

—

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
