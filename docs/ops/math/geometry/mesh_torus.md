---
op: mesh_torus
dim: math
category: geometry
in: 
out: mesh
examples: [geometry_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# mesh_torus — MATH `geometry` op

- **データ種**: `なし` → `mesh`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_torus(R: 'float' = 2.0, r: 'float' = 0.7, n_u: 'int' = 32, n_v: 'int' = 16) -> 'tuple'` (実装を直接呼ぶなら `import mathgeometry; mathgeometry.mesh_torus(R: 'float' = 2.0, r: 'float' = 0.7, n_u: 'int' = 32, n_v: 'int' = 16) -> 'tuple'`、台帳から引くなら `opsmath.get("mesh_torus")`)

## 使い方

トーラス(ドーナツ)の閉じた三角形メッシュ (vertices, faces)。大きい半径 R・管の半径 r(R > r > 0)。

種数 1 の曲面の見本: χ = 0、角欠損の総和 = 0(外側の凸の部分が正、内側の鞍の部分が負で打ち消し合う)。
頂点は (u, v) の格子(u が大円、v が管のまわり)の順で、``u = i·2π/n_u``、``v = j·2π/n_v`` の頂点が i·n_v + j 番。

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

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_euler_characteristic](mesh_euler_characteristic.md) · [angle_defect](angle_defect.md) · [geodesic_heat](geodesic_heat.md)

## 同カテゴリ(`geometry`)

[mesh_euler_characteristic](mesh_euler_characteristic.md) · [angle_defect](angle_defect.md) · [delaunay_triangulate](delaunay_triangulate.md) · [geodesic_heat](geodesic_heat.md) · [geodesic_heat_grid](geodesic_heat_grid.md) · [nurbs_curve](nurbs_curve.md) · [nurbs_circle](nurbs_circle.md) · [nurbs_surface](nurbs_surface.md)

---
*Provenance: mathgeometry.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
