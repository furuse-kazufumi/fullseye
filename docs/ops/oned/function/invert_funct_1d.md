---
op: invert_funct_1d
dim: oned
category: function
in: signal
out: pairs
examples: [poc_veiling_glare]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# invert_funct_1d — ONED `function` op

- **データ種**: `signal` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.invert_funct_1d(y)` (実装を直接呼ぶなら `import funct1d; funct1d.invert_funct_1d(y)`、台帳から引くなら `ops1d.get("invert_funct_1d")`)
- **台帳経由の戻り値**: `fullseye.ledger.invert_funct_1d(...)` は**宣言 out 型 `pairs` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.invert_funct_1d.raw(...)`、または `funct1d.invert_funct_1d` を直接呼ぶ。

## 使い方

Swap the roles of x and y: ``x = f^-1(y)`` (HALCON ``invert_funct_1d``).

Returns ``{"x": y-values sorted ascending, "y": their original indices}``,
i.e. the (y, x) pairs ordered so the new abscissa is monotonic — ready for
``numpy.interp``-style lookup.

Honest limitation: this is a true inverse only when *y* is monotonic. A
non-monotonic function is multi-valued; the sort interleaves its branches
instead of resolving them (ties keep index order — numpy stable-ish
argsort). An empty input returns two empty arrays.

:param y: 1-D function (may be empty).
:returns: dict ``{"x": float64 array, "y": float64 array}``.
:raises ValueError: non-1-D / NaN / Inf input.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_veiling_glare](../../../../examples/poc_veiling_glare.py) — `py -3.11 examples/poc_veiling_glare.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

—

## 同カテゴリ(`function`)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md)

---
*Provenance: funct1d.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
