---
op: sample_funct_1d
dim: oned
category: function
in: signal
out: signal
examples: [poc_cold_chain_excursion, signal_funct1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# sample_funct_1d — ONED `function` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.sample_funct_1d(y, step=2)` (実装を直接呼ぶなら `import funct1d; funct1d.sample_funct_1d(y, step=2)`、台帳から引くなら `ops1d.get("sample_funct_1d")`)

## 使い方

Every *step*-th sample (HALCON ``sample_funct_1d``).

Keeps samples ``0, step, 2*step, ...`` — decimation without an
anti-aliasing filter (smooth first if the signal has content above the new
Nyquist rate).

:param y: 1-D function (may be empty).
:param step: truncated to int, must be >= 1 (``step=1`` copies).
:raises ValueError: non-1-D / NaN / Inf input, or ``step < 1``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_cold_chain_excursion](../../../../examples/poc_cold_chain_excursion.py) — `py -3.11 examples/poc_cold_chain_excursion.py`
- [signal_funct1d](../../../../examples/signal_funct1d.py) — `py -3.11 examples/signal_funct1d.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md)

## 同カテゴリ(`function`)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md)

---
*Provenance: funct1d.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
