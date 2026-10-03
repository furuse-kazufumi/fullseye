---
op: geodesic_heat_grid
dim: math
category: geometry
in: image2d
out: table
examples: [geometry_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# geodesic_heat_grid — MATH `geometry` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.geodesic_heat_grid(mask, source=None, *, spacing=1.0, t: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import mathgeometry; mathgeometry.geodesic_heat_grid(mask, source=None, *, spacing=1.0, t: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsmath.get("geodesic_heat_grid")`)

## 使い方

2-D 画像・3-D ボリュームの格子の上で、障害物を避けた測地距離を熱法で求める(Crane et al. 2013 の格子版)。

``mask`` は通れる画素/ボクセルが True の bool 配列(2-D か 3-D)、``source`` は始点の添字(1 点 ``(i, j[, k])``
か点の列。省略すると最初の通れる画素)。``spacing`` は軸ごとの画素の大きさ(スカラーか軸ごと)。
1) (I − tΔ) u = δ(熱を広げる、Δ は通れる画素の間だけを結ぶ 2d+1 点の Laplacian = 障害物は断熱)
2) X = −∇u / |∇u|(面の間の差分で)  3) Δφ = ∇·X を解いて始点で 0 にずらす。
返り値 ``{"distance", "t"}``(通れない画素と、始点と繋がらない画素は inf)。
門: 障害物の無い空間ではユークリッド距離へ収束する。画素の Dijkstra(4/8 近傍)は格子の向きの誤差
(4 近傍で最大 41%、8 近傍で最大 8%)が細かくしても消えないが、熱法は消えていく。

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

- [geometry_tour](../../../../examples/geometry_tour.py) — `py -3.11 examples/geometry_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md) · [dwt_inverse](../transform/dwt_inverse.md) · [chebyshev_eval_nd](../numerics/chebyshev_eval_nd.md)

## 同カテゴリ(`geometry`)

[mesh_euler_characteristic](mesh_euler_characteristic.md) · [angle_defect](angle_defect.md) · [delaunay_triangulate](delaunay_triangulate.md) · [geodesic_heat](geodesic_heat.md) · [mesh_torus](mesh_torus.md) · [nurbs_curve](nurbs_curve.md) · [nurbs_circle](nurbs_circle.md) · [nurbs_surface](nurbs_surface.md)

---
*Provenance: mathgeometry.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
