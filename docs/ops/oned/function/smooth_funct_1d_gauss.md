---
op: smooth_funct_1d_gauss
dim: oned
category: function
in: signal
out: signal
examples: [poc_fiber_orientation, poc_tree_ring_dendro, poc_web_roll_periodicity, signal_funct1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# smooth_funct_1d_gauss — ONED `function` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.smooth_funct_1d_gauss(y, sigma: 'float' = 1.0)` (実装を直接呼ぶなら `import funct1d; funct1d.smooth_funct_1d_gauss(y, sigma: 'float' = 1.0)`、台帳から引くなら `ops1d.get("smooth_funct_1d_gauss")`)

## 使い方

Gaussian smoothing of a 1-D function (HALCON ``smooth_funct_1d_gauss``).

Convolves *y* with a Gaussian of standard deviation *sigma* (in samples),
``reflect`` boundary handling (scipy default). The DC level is preserved;
zero-mean noise variance shrinks by roughly ``1 / (2 * sigma * sqrt(pi))``.

:param y: 1-D function, at least 1 sample.
:param sigma: Gaussian standard deviation in samples; must be finite and > 0.
:returns: smoothed float64 array, same length as *y*.
:raises ValueError: non-1-D / NaN / Inf input, empty input, or ``sigma <= 0``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fiber_orientation](../../../../examples/poc_fiber_orientation.py) — `py -3.11 examples/poc_fiber_orientation.py`
- [poc_tree_ring_dendro](../../../../examples/poc_tree_ring_dendro.py) — `py -3.11 examples/poc_tree_ring_dendro.py`
- [poc_web_roll_periodicity](../../../../examples/poc_web_roll_periodicity.py) — `py -3.11 examples/poc_web_roll_periodicity.py`
- [signal_funct1d](../../../../examples/signal_funct1d.py) — `py -3.11 examples/signal_funct1d.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md) · [abs_funct_1d](abs_funct_1d.md)

## 同カテゴリ(`function`)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md) · [abs_funct_1d](abs_funct_1d.md)

---
*Provenance: funct1d.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
