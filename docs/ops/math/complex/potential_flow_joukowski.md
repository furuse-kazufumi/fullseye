---
op: potential_flow_joukowski
dim: math
category: complex
in: 
out: cimage
examples: [poc_complex_plane_fields]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# potential_flow_joukowski — MATH `complex` op

- **データ種**: `なし` → `cimage`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.potential_flow_joukowski(alpha_deg=5.0, speed=1.0, chord_b=1.0, centre_offset=(-0.09+0.09j), centre=0j, half_width=3.0, shape=(256, 256))` (実装を直接呼ぶなら `import mathops; mathops.potential_flow_joukowski(alpha_deg=5.0, speed=1.0, chord_b=1.0, centre_offset=(-0.09+0.09j), centre=0j, half_width=3.0, shape=(256, 256))`、台帳から引くなら `opsmath.get("potential_flow_joukowski")`)

## 使い方

Inviscid flow past a Joukowski aerofoil, as a complex velocity field.

Returns the **complex velocity** ``w(z) = dW/dz = u - i*v`` sampled over a
window of the physical plane. Inside the solid body the field is set to
exactly ``0`` (there is no flow there), so ``field == 0`` is the body mask
and nothing is silently ``nan``.

The construction is the classical one: flow past a circle of radius
``a = |chord_b - centre_offset|`` centred at ``centre_offset``, plus the
circulation the **Kutta condition** demands, pushed through the Joukowski
map ``z = zeta + chord_b**2 / zeta``. The window is inverted back to the
circle plane by choosing, of the two preimages, the one outside the circle.

★**What makes this checkable rather than merely plotted**:
  - The field is holomorphic outside the body, so this family's own
    ``cplx_cr_residual`` must read ~0 on it — an existing operator is the
    oracle, and it is not the formula used to build the field.
  - The **Kutta condition** is the whole point: ``dW/dzeta`` vanishes at the
    trailing edge exactly where ``dz/dzeta`` does, so the velocity there
    stays finite. Perturb the circulation by any amount and the trailing-edge
    velocity diverges — the gate has a control group.
  - ``Re(closed integral of w dz)`` around the body is the circulation, and
    it is **path independent** (Cauchy) — a big rectangle and a small one
    must agree.
  - Far from the body ``w -> speed * exp(-i*alpha)``, decaying like ``1/|z|``.
  - The zeroed region is the aerofoil, whose area the shoelace formula on
    ``cplx_joukowski`` of the circle gives independently.

Parameters
----------
alpha_deg : float
    Angle of attack in degrees.
speed : float > 0
    Free-stream speed.
chord_b : float > 0
    Half the flat-plate chord; the map is ``zeta + chord_b**2/zeta``.
centre_offset : complex
    Circle centre. Negative real part thickens, positive imaginary part
    cambers. The default is a thin cambered section.
centre, half_width, shape :
    The window in the physical plane, as in :func:`cplx_plane_grid`.

**Raises** ``ValueError``: ``speed <= 0``; non-finite angle; a circle that
does not enclose ``-chord_b`` (the image would fold over itself) or whose
centre is at or beyond ``+chord_b``; degenerate window.

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

## 型が繋がる次の op(`cimage` を入力に取れる)

[cplx_cr_residual](cplx_cr_residual.md) · [cplx_domain_colour](cplx_domain_colour.md) · [mandelbrot_interior](mandelbrot_interior.md)

## 同カテゴリ(`complex`)

[cplx_contour_circle](cplx_contour_circle.md) · [cplx_poly_eval](cplx_poly_eval.md) · [cplx_contour_integral](cplx_contour_integral.md) · [cplx_winding_number](cplx_winding_number.md) · [cplx_cauchy_value](cplx_cauchy_value.md) · [cplx_argument_principle](cplx_argument_principle.md) · [cplx_laurent_coeffs](cplx_laurent_coeffs.md) · [cplx_joukowski](cplx_joukowski.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
