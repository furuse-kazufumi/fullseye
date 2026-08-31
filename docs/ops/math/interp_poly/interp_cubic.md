---
op: interp_cubic
dim: math
category: interp_poly
in: signal × signal × signal
out: signal
examples: [math_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# interp_cubic — MATH `interp_poly` op

- **データ種**: `signal × signal × signal` → `signal`
- **呼び出し**: `import mathops; mathops.interp_cubic(x, y, xq, out_of_range='raise', bc_type='not-a-knot')` (または `opsmath.get("interp_cubic")`)

## 使い方

Cubic-spline interpolation (``scipy.interpolate.CubicSpline``).

    C²-smooth through all nodes — the step up from :func:`interp_linear` when
    the underlying curve is smooth (a lens-distortion or gamma curve). Needs at
    least 4 points. *bc_type* is the boundary condition: ``'not-a-knot'``
    (default — reproduces a global cubic polynomial *exactly*, the property the
    tests pin), ``'natural'`` (zero second derivative at the ends; slightly
    smoother-looking, but it will NOT reproduce a cubic), or ``'clamped'``.

    Same strict grid and the same explicit *out_of_range* policy as
    :func:`interp_linear` ('raise' by default, 'clamp' to hold end values) —
    spline **extrapolation diverges cubically** and is refused outright.

    Honest note: between nodes a spline can overshoot (it is a minimum-
    curvature interpolant, not shape-preserving); for monotone data whose
    interpolant must stay monotone, use a PCHIP-type method instead — not
    provided here, stated so nobody assumes otherwise.

    HALCON: no cubic tuple interpolation operator (``create_funct_1d_pairs``
    feeds linear interpolation only).

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

- [math_metrology](../../../../examples/math_metrology.py) — `py -3.11 examples/math_metrology.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [stat_describe](../stats/stat_describe.md) · [stat_histogram](../stats/stat_histogram.md) · [stat_zscore](../stats/stat_zscore.md) · [interp_linear](interp_linear.md) · [poly_fit](poly_fit.md) · [poly_eval](poly_eval.md)

## 同カテゴリ(`interp_poly`)

[interp_linear](interp_linear.md) · [poly_fit](poly_fit.md) · [poly_eval](poly_eval.md) · [poly_roots](poly_roots.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
