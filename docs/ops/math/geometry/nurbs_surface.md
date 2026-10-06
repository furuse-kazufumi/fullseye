---
op: nurbs_surface
dim: math
category: geometry
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# nurbs_surface — MATH `geometry` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.nurbs_surface(control_net, weights=None, *, degree=(3, 3), knots_u=None, knots_v=None, n=(48, 48)) -> 'dict'` (実装を直接呼ぶなら `import mathgeometry; mathgeometry.nurbs_surface(control_net, weights=None, *, degree=(3, 3), knots_u=None, knots_v=None, n=(48, 48)) -> 'dict'`、台帳から引くなら `opsmath.get("nurbs_surface")`)

## 使い方

NURBS 曲面(テンソル積)を評価する。

Args:
    control_net: (mu, mv, 3) の制御網。
    weights: (mu, mv) の正の重み(省略で全部 1)。
    degree: (p, q)。
    knots_u, knots_v: 各方向の節点列(省略で clamped 一様)。
    n: (nu, nv) 評価点の格子。

Returns:
    ``points`` (nu, nv, 3)、``mesh`` = (V, F) の三角形メッシュ(``geodesic_heat`` などにそのまま渡せる)、
    ``u``・``v``・``knots_u``・``knots_v``・``weights``。

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

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md) · [dwt_inverse](../transform/dwt_inverse.md) · [chebyshev_eval_nd](../numerics/chebyshev_eval_nd.md)

## 同カテゴリ(`geometry`)

[mesh_euler_characteristic](mesh_euler_characteristic.md) · [angle_defect](angle_defect.md) · [delaunay_triangulate](delaunay_triangulate.md) · [geodesic_heat](geodesic_heat.md) · [geodesic_heat_grid](geodesic_heat_grid.md) · [mesh_torus](mesh_torus.md) · [nurbs_curve](nurbs_curve.md) · [nurbs_circle](nurbs_circle.md)

---
*Provenance: mathgeometry.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
