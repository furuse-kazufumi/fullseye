---
op: doe_central_composite
dim: multivar
category: plan
in: 
out: design
examples: [doe_plan_tour, multivar_inspection_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# doe_central_composite — MULTIVAR `plan` op

- **データ種**: `なし` → `design`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.doe_central_composite(factors=3, alpha='rotatable', center=4, generators=None, inscribed=False) -> 'dict'` (実装を直接呼ぶなら `import doe; doe.doe_central_composite(factors=3, alpha='rotatable', center=4, generators=None, inscribed=False) -> 'dict'`、台帳から引くなら `opsmultivar.get("doe_central_composite")`)

## 使い方

Central composite design (Box & Wilson 1951) -> ``design``.

Three parts: the two-level factorial (full 2^k, or a fraction from ``generators``
as in :func:`doe_fractional_factorial` — it must be resolution V or better so that
every two-factor interaction of the quadratic model stays estimable), 2k axial
points at ±alpha on each axis, and ``center`` centre points.

``alpha``: ``"rotatable"`` — alpha = F^(1/4) with F the number of factorial points
(the prediction variance then depends only on the distance from the centre;
Box & Hunter 1957), ``"face"`` — alpha = 1 (face-centred, three levels only),
``"spherical"`` — alpha = sqrt(k), or a number > 0.

``inscribed=True`` shrinks the whole design by 1/alpha so that the axial points sit at
the ends of the range (lo/hi) and the factorial points inside it; otherwise the
factorial points sit at lo/hi and the axial points go **outside** the range —
``meta['outside_range']`` then names the factors whose natural values leave lo..hi
(check that the bench can be set there).

## 詳しい使い方ガイド

- [design_of_experiments ファミリ ガイド](../guides/design_of_experiments.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [doe_plan_tour](../../../../examples/doe_plan_tour.py) — `py -3.11 examples/doe_plan_tour.py`
- [multivar_inspection_tour](../../../../examples/multivar_inspection_tour.py) — `py -3.11 examples/multivar_inspection_tour.py`

## 型が繋がる次の op(`design` を入力に取れる)

[doe_decode](../coding/doe_decode.md) · [rsm_fit](../analysis/rsm_fit.md) · [doe_main_effects](../analysis/doe_main_effects.md)

## 同カテゴリ(`plan`)

[doe_lhs](doe_lhs.md) · [doe_orthogonal_array](doe_orthogonal_array.md) · [doe_fractional_factorial](doe_fractional_factorial.md) · [doe_box_behnken](doe_box_behnken.md)

---
*Provenance: doe.py — MULTIVAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
