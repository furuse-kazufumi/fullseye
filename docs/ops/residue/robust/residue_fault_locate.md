---
op: residue_fault_locate
dim: residue
category: robust
in: matrix × signal
out: table
examples: [poc_residue_crt]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# residue_fault_locate — RESIDUE `robust` op

- **データ種**: `matrix × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.residue_fault_locate(residues, periods, weights=None, lo=0.0, hi=None, tol=0.05) -> 'dict'` (実装を直接呼ぶなら `import residue; residue.residue_fault_locate(residues, periods, weights=None, lo=0.0, hi=None, tol=0.05) -> 'dict'`、台帳から引くなら `opsresidue.get("residue_fault_locate")`)

## 使い方

Which band is corrupted? (redundant residue number system) -> ``dict``.

With more bands than ``[lo, hi)`` needs, the bands check each other. Each
band is left out in turn and the rest are solved; the band whose removal
leaves a consistent set (every residual within ``tol`` x its period) while
itself disagreeing by more than ``tol`` is the corrupted one. If no single
removal is consistent, or two different removals both are, the answer is
**undecidable** and the value is NaN — never a guess.

Returns ``{"value", "faulty", "consistent_all", "worst_leave_one_out"}``:
``faulty`` is the band index, ``-1`` = all bands agree (no fault),
``-2`` = undecidable. Localising one fault needs the range to be resolvable by
every subset of ``N-1`` bands (it is refused otherwise); the narrower
``[lo, hi)`` is relative to the periods' least common multiple, the more of
the redundancy is left to localise with.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_residue_crt](../../../../examples/poc_residue_crt.py) — `py -3.11 examples/poc_residue_crt.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`robust`)

[residue_crt](residue_crt.md)

---
*Provenance: residue.py — RESIDUE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
