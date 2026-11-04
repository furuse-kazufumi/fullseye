---
op: derivate_funct_1d
dim: oned
category: function
in: signal
out: signal
halcon: derivate_funct_1d
gpu: 鎖の中だけ(許可リスト)
examples: [poc_tree_ring_dendro, poc_veiling_glare, signal_funct1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# derivate_funct_1d — ONED `function` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.derivate_funct_1d(y)` (実装を直接呼ぶなら `import funct1d; funct1d.derivate_funct_1d(y)`、台帳から引くなら `ops1d.get("derivate_funct_1d")`)
- **HALCON 相当**: `derivate_funct_1d`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: 鎖の中だけ(許可リストの機械的 GPU 経路、CuPy)。隣の段も許可リストのときだけGPU に載せたまま走る。単独の呼び出しは CPU

## 使い方

First derivative by central differences (HALCON ``derivate_funct_1d``).

Units are **y per sample** (the x-grid is the index): for a physical signal
sampled every ``dt`` seconds, divide the result by ``dt``. Interior points
use the second-order central difference; the two boundary points use one-sided
differences (``numpy.gradient``).

:param y: 1-D function, at least 2 samples (a derivative needs a neighbour).
:returns: float64 array of the same length.
:raises ValueError: non-1-D / NaN / Inf input, or fewer than 2 samples.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tree_ring_dendro](../../../../examples/poc_tree_ring_dendro.py) — `py -3.11 examples/poc_tree_ring_dendro.py`
- [poc_veiling_glare](../../../../examples/poc_veiling_glare.py) — `py -3.11 examples/poc_veiling_glare.py`
- [signal_funct1d](../../../../examples/signal_funct1d.py) — `py -3.11 examples/signal_funct1d.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md) · [abs_funct_1d](abs_funct_1d.md)

## 同カテゴリ(`function`)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md) · [abs_funct_1d](abs_funct_1d.md)

---
*Provenance: funct1d.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
