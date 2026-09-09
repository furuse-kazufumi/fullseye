---
op: get_y_value_funct_1d
dim: oned
category: function
in: signal
out: measurement
examples: [poc_veiling_glare, signal_funct1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# get_y_value_funct_1d — ONED `function` op

- **データ種**: `signal` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.get_y_value_funct_1d(y, x, interpolate=True)` (実装を直接呼ぶなら `import funct1d; funct1d.get_y_value_funct_1d(y, x, interpolate=True)`、台帳から引くなら `ops1d.get("get_y_value_funct_1d")`)

## 使い方

The y-value at (fractional) position *x* (HALCON ``get_y_value_funct_1d``).

With ``interpolate=True`` (default) the value is linearly interpolated
between the two neighbouring samples; with ``interpolate=False`` the nearest
sample is returned.

Domain policy (documented, not extrapolated): *x* outside ``[0, n-1]``
**clamps** to the boundary value (``numpy.interp`` end-hold semantics /
index clip). HALCON's ``'zero'``-border variant is not offered.

:param y: 1-D function, at least 1 sample.
:param x: finite scalar position in index units.
:param interpolate: linear interpolation (True) or nearest sample (False).
:returns: float.
:raises ValueError: non-1-D / NaN / Inf input, empty input, or non-finite *x*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_veiling_glare](../../../../examples/poc_veiling_glare.py) — `py -3.11 examples/poc_veiling_glare.py`
- [signal_funct1d](../../../../examples/signal_funct1d.py) — `py -3.11 examples/signal_funct1d.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`function`)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md)

---
*Provenance: funct1d.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
