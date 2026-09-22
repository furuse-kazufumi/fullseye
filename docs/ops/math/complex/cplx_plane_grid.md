---
op: cplx_plane_grid
dim: math
category: complex
in: 
out: cimage
examples: [poc_complex_plane_fields]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# cplx_plane_grid — MATH `complex` op

- **データ種**: `なし` → `cimage`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.cplx_plane_grid(centre=0j, half_width=2.0, shape=(256, 256))` (実装を直接呼ぶなら `import mathops; mathops.cplx_plane_grid(centre=0j, half_width=2.0, shape=(256, 256))`、台帳から引くなら `opsmath.get("cplx_plane_grid")`)

## 使い方

複素平面の矩形窓を格子にする(画像と同じ並び: 行 0 が上 = 虚部が大きい側)。

返すのは ``(h, w)`` の複素配列。実部は ``[-half_width, +half_width]`` を
``w`` 点で等間隔、虚部は**アスペクト比を保って** ``h`` 点。窓が正方形でない
ときに円が楕円に潰れないようにするためで、``half_width`` は常に**横**半幅。

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
