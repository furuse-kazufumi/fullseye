---
op: create_funct_1d_pairs
dim: oned
category: function
in: signal × signal
out: signal
examples: [poc_veiling_glare]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# create_funct_1d_pairs — ONED `function` op

- **データ種**: `signal × signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.create_funct_1d_pairs(x, y)` (実装を直接呼ぶなら `import funct1d; funct1d.create_funct_1d_pairs(x, y)`、台帳から引くなら `ops1d.get("create_funct_1d_pairs")`)

## 使い方

A 1-D function from arbitrary ``(x, y)`` pairs, resampled to an
equidistant grid (HALCON ``create_funct_1d_pairs``).

The pairs are sorted by x and linearly interpolated onto the **integer**
grid ``floor(min(x)) .. ceil(max(x))`` (step 1). Grid points outside the
convex hull of the data (only the two end points can be) hold the nearest
sample's value — ``numpy.interp`` end-hold, no extrapolation. Duplicate x
values keep numpy's interp behaviour (the segment between duplicates is a
step). Note the returned function's index 0 corresponds to physical
``x = floor(min(x))``, not necessarily 0.

:param x: 1-D abscissa values, at least 1 pair, finite.
:param y: 1-D ordinate values, same length as *x*, finite.
:returns: float64 array on the integer grid.
:raises ValueError: non-1-D / NaN / Inf input, empty input, or length mismatch.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_veiling_glare](../../../../examples/poc_veiling_glare.py) — `py -3.11 examples/poc_veiling_glare.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](create_funct_1d_array.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md) · [abs_funct_1d](abs_funct_1d.md)

## 同カテゴリ(`function`)

[create_funct_1d_array](create_funct_1d_array.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md) · [abs_funct_1d](abs_funct_1d.md)

---
*Provenance: funct1d.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
