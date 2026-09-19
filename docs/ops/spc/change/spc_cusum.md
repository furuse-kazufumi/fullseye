---
op: spc_cusum
dim: spc
category: change
in: signal
out: table
examples: [poc_spc]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# spc_cusum — SPC `change` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spc_cusum(signal, target, k=0.5, h=5.0)` (実装を直接呼ぶなら `import spc; spc.spc_cusum(signal, target, k=0.5, h=5.0)`、台帳から引くなら `opsspc.get("spc_cusum")`)

## 使い方

Tabular CUSUM chart for individual measurements.

``signal`` is a 1-D series of individual measurements. With a reference value
``target``, a slack ``k`` (in the same units as the measurements — commonly half
the shift you want to catch) and a decision interval ``h``::

    C+_i = max(0, C+_{i-1} + (x_i - target) - k)
    C-_i = max(0, C-_{i-1} - (x_i - target) - k)

starting from ``C+_0 = C-_0 = 0``, alarming at index ``i`` when ``C+_i > h`` or
``C-_i > h``. Returns a dict with the ``c_plus`` / ``c_minus`` arrays, the
integer ``alarms`` indices, the first alarm index (or ``-1``), and the echoed
``target`` / ``k`` / ``h``.

Ground truth (pinned in the tests): a series constant at ``target`` keeps
``C+ == C- == 0``; after a sustained upward step of size ``d > k`` the upper sum
grows at exactly ``d - k`` per sample.

**Raises** ``ValueError``: a non-1-D / empty *signal*, a non-finite
*target* / *k* / *h*, a negative *k*, or a non-positive *h*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_spc](../../../../examples/poc_spc.py) — `py -3.11 examples/poc_spc.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`change`)

[spc_ewma](spc_ewma.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
