---
op: zero_crossings_funct_1d
dim: oned
category: function
in: signal
out: indices
examples: [signal_funct1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# zero_crossings_funct_1d — ONED `function` op

- **データ種**: `signal` → `indices`
- **呼び出し**: `import fullseye as fs; fs.ledger.zero_crossings_funct_1d(y)` (実装を直接呼ぶなら `import funct1d; funct1d.zero_crossings_funct_1d(y)`、台帳から引くなら `ops1d.get("zero_crossings_funct_1d")`)

## 使い方

Indices where the function changes sign (HALCON ``zero_crossings_funct_1d``).

Returns the integer indices ``i`` with ``sign(y[i]) * sign(y[i+1]) < 0`` —
the sample *before* each crossing. An empty input returns an empty index
array (degenerate case, not an error).

Honest limitation: the test is a **strict** sign product, so a crossing that
lands exactly on a zero sample (``[-1, 0, 1]``) is *not* reported, nor is a
touch of zero without a sign change (``[1, 0, 1]``).

:param y: 1-D function (may be empty).
:returns: int index array (possibly empty).
:raises ValueError: non-1-D / NaN / Inf input.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [signal_funct1d](../../../../examples/signal_funct1d.py) — `py -3.11 examples/signal_funct1d.py`

## 型が繋がる次の op(`indices` を入力に取れる)

[peak_subbin](../signal/peak_subbin.md)

## 同カテゴリ(`function`)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md) · [abs_funct_1d](abs_funct_1d.md)

---
*Provenance: funct1d.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
