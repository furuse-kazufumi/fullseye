---
op: phyllotaxis_pattern
dim: math
category: construct
in: 
out: pairs
examples: [poc_theorems_as_pictures]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# phyllotaxis_pattern — MATH `construct` op

- **データ種**: `なし` → `pairs`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.phyllotaxis_pattern(n_points=400, angle_deg=None, scale=1.0, power=0.5)` (実装を直接呼ぶなら `import mathops; mathops.phyllotaxis_pattern(n_points=400, angle_deg=None, scale=1.0, power=0.5)`、台帳から引くなら `opsmath.get("phyllotaxis_pattern")`)

## 使い方

Vogel's spiral — the angle that packs best, and the spirals it makes.

Point ``k`` sits at ``r = scale * k**power``, ``theta = k * angle_deg``. With
the **golden angle** ``180*(3 - sqrt 5) = 137.50776...`` degrees (the default)
this is the arrangement of sunflower florets, pine-cone scales and the leaves
of most plants.

★**Why this earns its place — two independent theorems, each with a control
group**:

  - *The golden angle packs best.* Sweep the divergence angle and the minimum
    nearest-neighbour distance is **maximised** at 137.50776 deg; a fraction
    of a degree either side is measurably worse. Nothing in the formula says
    this — it has to be measured.
  - *The visible spirals are consecutive Fibonacci numbers.* Take each point's
    nearest neighbours and look at the **difference of their indices**: the
    differences concentrate on 1, 2, 3, 5, 8, 13, 21, 34... At a non-golden
    angle they do not.

Returns ``pairs`` ``(n, 2)`` of ``(x, y)``.

**Raises** ``ValueError``: ``n_points < 1`` or over the cap; non-finite angle
or scale; ``power`` outside ``(0, 1]``.

HALCON: no operator.

## ファミリ共通の入力契約(fail-closed)

mathops の全 op は入力を検証してから計算する(黙って通さない):

- **complex 入力は `ValueError`** — float64 への強制変換は虚部を黙って捨てる(numpy は ComplexWarning だけ出して「もっともらしく間違った」実数を返す)。`.real`/`.imag`/`abs()` を明示するか、複素対応の complexops を使う。
- **masked array(masked 要素あり)は `ValueError`** — マスクを剥がして下の生値を使う暗黙変換を拒否。埋める/落とすを明示する。
- **NaN/Inf は全入力で `ValueError`**(件数を明示して拒否 — 結果全体に伝播するため)。
- **形状は厳格**: 1-D と 2-D を暗黙昇格・ブロードキャストしない(vector 枠に matrix、matrix 枠に vector は `ValueError`。reshape を明示する)。
- **サイズ上限**: 行列を取る op と `stat_histogram` の bins は `mathops.MAX_ELEMENTS`(2^26 ≈ 6700 万要素)超で `ValueError`。

## 詳しい使い方ガイド

- [math_metrology ファミリ ガイド](../guides/math_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_theorems_as_pictures](../../../../examples/poc_theorems_as_pictures.py) — `py -3.11 examples/poc_theorems_as_pictures.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[neighbour_index_gaps](neighbour_index_gaps.md) · [curve_locality](curve_locality.md)

## 同カテゴリ(`construct`)

[circle_packing_apollonian](circle_packing_apollonian.md) · [ford_circles](ford_circles.md) · [neighbour_index_gaps](neighbour_index_gaps.md) · [ifs_fractal](ifs_fractal.md) · [ifs_similarity_dimension](ifs_similarity_dimension.md) · [space_filling_curve](space_filling_curve.md) · [curve_locality](curve_locality.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
