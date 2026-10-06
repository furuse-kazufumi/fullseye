---
op: residue_integer_crt
dim: residue
category: theorem
in: signal × signal
out: table
examples: [poc_residue_crt]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# residue_integer_crt — RESIDUE `theorem` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.residue_integer_crt(residues, moduli) -> 'dict'` (実装を直接呼ぶなら `import residue; residue.residue_integer_crt(residues, moduli) -> 'dict'`、台帳から引くなら `opsresidue.get("residue_integer_crt")`)

## 使い方

Exact integer CRT (Garner's mixed-radix algorithm) -> ``dict``.

``residues`` and ``moduli`` are equal-length integer sequences; the moduli must
be pairwise coprime and >= 2. Returns ``{"value": int, "modulus": int,
"mixed_radix": [digits]}`` where ``value`` is the unique solution in
``[0, prod(moduli))``. Arithmetic is Python's arbitrary-precision ``int`` —
there is no rounding anywhere, which is why this op is the oracle for
:func:`residue_crt`.

The mixed-radix digits ``d_k`` satisfy ``value = d_0 + d_1 m_0 + d_2 m_0 m_1 + ...``:
the *positional* (coarse-to-fine) reading of the same residues, i.e. the
bridge between the residue view and the place-value view.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_residue_crt](../../../../examples/poc_residue_crt.py) — `py -3.11 examples/poc_residue_crt.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`theorem`)

—

---
*Provenance: residue.py — RESIDUE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
