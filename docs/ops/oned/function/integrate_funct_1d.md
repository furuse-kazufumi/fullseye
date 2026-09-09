---
op: integrate_funct_1d
dim: oned
category: function
in: signal
out: signal
examples: [poc_cold_chain_excursion, poc_search_sweep_width, signal_funct1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# integrate_funct_1d — ONED `function` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.integrate_funct_1d(y)` (実装を直接呼ぶなら `import funct1d; funct1d.integrate_funct_1d(y)`、台帳から引くなら `ops1d.get("integrate_funct_1d")`)

## 使い方

Cumulative integral by the trapezoidal rule (HALCON ``integrate_funct_1d``).

``out[i]`` is the integral of *y* from x=0 to x=i in **y-units times
samples** (multiply by the physical sample spacing ``dt`` yourself);
``out[0]`` is always 0. For smooth signals
``integrate_funct_1d(derivate_funct_1d(y)) ~= y - y[0]`` to second order.

:param y: 1-D function, at least 1 sample (a single sample integrates to ``[0.]``).
:returns: float64 array of the same length.
:raises ValueError: non-1-D / NaN / Inf input, or empty input.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_cold_chain_excursion](../../../../examples/poc_cold_chain_excursion.py) — `py -3.11 examples/poc_cold_chain_excursion.py`
- [poc_search_sweep_width](../../../../examples/poc_search_sweep_width.py) — `py -3.11 examples/poc_search_sweep_width.py`
- [signal_funct1d](../../../../examples/signal_funct1d.py) — `py -3.11 examples/signal_funct1d.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md) · [abs_funct_1d](abs_funct_1d.md)

## 同カテゴリ(`function`)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md) · [abs_funct_1d](abs_funct_1d.md)

---
*Provenance: funct1d.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
