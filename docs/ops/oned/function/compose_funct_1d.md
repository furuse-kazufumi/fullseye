---
op: compose_funct_1d
dim: oned
category: function
in: signal × signal
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# compose_funct_1d — ONED `function` op

- **データ種**: `signal × signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.compose_funct_1d(y1, y2)` (実装を直接呼ぶなら `import funct1d; funct1d.compose_funct_1d(y1, y2)`、台帳から引くなら `ops1d.get("compose_funct_1d")`)

## 使い方

Composition ``y1(y2)``: the values of *y2* used as positions into *y1*
(HALCON ``compose_funct_1d``).

Each ``y2[i]`` is rounded to the nearest integer and **clamped** into
``[0, len(y1) - 1]``, then ``out[i] = y1[that index]``. Nearest-neighbour
lookup, no interpolation.

Domain policy (documented difference from HALCON, which errors when the
range of *y2* leaves the domain of *y1*): out-of-domain positions are
clamped to the first / last sample of *y1*, never extrapolated. If you need
the strict check, compare ``y_range_funct_1d(y2)`` against
``x_range_funct_1d(y1)`` before composing.

:param y1: outer function, at least 1 sample.
:param y2: inner function supplying positions (may be empty).
:returns: float64 array with the length of *y2*.
:raises ValueError: non-1-D / NaN / Inf input, or empty *y1*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md)

## 同カテゴリ(`function`)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md)

---
*Provenance: funct1d.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
