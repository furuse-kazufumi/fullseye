---
op: get_pair_funct_1d
dim: oned
category: function
in: signal
out: pairs
examples: [signal_funct1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# get_pair_funct_1d — ONED `function` op

- **データ種**: `signal` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.get_pair_funct_1d(y, index=0)` (実装を直接呼ぶなら `import funct1d; funct1d.get_pair_funct_1d(y, index=0)`、台帳から引くなら `ops1d.get("get_pair_funct_1d")`)
- **台帳経由の戻り値**: `fullseye.ledger.get_pair_funct_1d(...)` は**宣言 out 型 `pairs` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.get_pair_funct_1d.raw(...)`、または `funct1d.get_pair_funct_1d` を直接呼ぶ。

## 使い方

The ``(x, y)`` pair at *index* (HALCON ``get_pair_funct_1d``).

*index* is truncated to int and **clamped** into ``[0, n-1]`` (historical
behaviour, kept and documented rather than made an error): asking for
index -3 returns pair 0, asking past the end returns the last pair.

:param y: 1-D function, at least 1 sample.
:param index: sample position (clamped).
:returns: float64 array ``[x, y[x]]``.
:raises ValueError: non-1-D / NaN / Inf input, empty input, or non-finite *index*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [signal_funct1d](../../../../examples/signal_funct1d.py) — `py -3.11 examples/signal_funct1d.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

—

## 同カテゴリ(`function`)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md)

---
*Provenance: funct1d.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
