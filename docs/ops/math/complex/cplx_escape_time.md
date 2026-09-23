---
op: cplx_escape_time
dim: math
category: complex
in: 
out: image2d
examples: [poc_complex_plane_fields]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# cplx_escape_time — MATH `complex` op

- **データ種**: `なし` → `image2d`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.cplx_escape_time(kind='mandelbrot', param=0j, centre=0j, half_width=2.0, shape=(256, 256), max_iter=64, escape_radius=2.0)` (実装を直接呼ぶなら `import mathops; mathops.cplx_escape_time(kind='mandelbrot', param=0j, centre=0j, half_width=2.0, shape=(256, 256), max_iter=64, escape_radius=2.0)`、台帳から引くなら `opsmath.get("cplx_escape_time")`)

## 使い方

How many steps of ``z -> z**2 + c`` it takes to leave the escape disc.

``kind="mandelbrot"`` varies ``c`` over the window from ``z = 0``;
``kind="julia"`` fixes ``c = param`` and varies the starting ``z``. The
result is a float image of iteration counts; points that never escape carry
``max_iter``.

★**This one is gated by theorems, not by a reference picture.**
  - *Escape radius*: once ``|z| > 2`` (with ``|c| <= 2``) the orbit diverges,
    so ``escape_radius = 2`` is not a tuning knob but the exact threshold.
  - *Main cardioid*: ``c`` lies in the main cardioid iff the fixed point
    ``z* = (1 - sqrt(1 - 4c)) / 2`` is attracting, i.e. ``|2 z*| < 1``.
    Every such ``c`` **provably never escapes**, so those pixels must read
    exactly ``max_iter`` — a closed-form interior test for a set usually
    drawn by iteration alone. The period-2 bulb ``|c + 1| < 1/4`` is the
    same kind of statement.
  - *Symmetry*: both families are invariant under conjugation, so the image
    must be **exactly** mirror-symmetric about the real axis (bit for bit,
    not to a tolerance) when the window is.

**Raises** ``ValueError``: unknown ``kind``; non-finite ``param``;
``max_iter < 1``; ``escape_radius <= 0``; degenerate window.

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

- [poc_complex_plane_fields](../../../../examples/poc_complex_plane_fields.py) — `py -3.11 examples/poc_complex_plane_fields.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[wave_fringe_period](../wave/wave_fringe_period.md)

## 同カテゴリ(`complex`)

[cplx_contour_circle](cplx_contour_circle.md) · [cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
