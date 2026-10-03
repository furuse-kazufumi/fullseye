---
op: angle_defect
dim: math
category: geometry
in: mesh
out: table
examples: [geometry_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# angle_defect — MATH `geometry` op

- **データ種**: `mesh` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.angle_defect(vertices, faces=None) -> 'dict'` (実装を直接呼ぶなら `import mathgeometry; mathgeometry.angle_defect(vertices, faces=None) -> 'dict'`、台帳から引くなら `opsmath.get("angle_defect")`)

## 使い方

頂点ごとの角欠損(離散 Gauss 曲率)K_v = 2π − Σ(その頂点での三角形の角)。境界の頂点は π − Σ(測地曲率)。

閉じたメッシュでは Σ K_v = 2πχ が**厳密に**成り立つ(Descartes の定理)。境界があるときは
Σ(内部の K) + Σ(境界の π − Σθ) = 2πχ(離散 Gauss–Bonnet)。
返り値 ``{"defect", "total", "two_pi_chi", "is_boundary"}``。

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

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md)

## 同カテゴリ(`geometry`)

[mesh_euler_characteristic](mesh_euler_characteristic.md) · [delaunay_triangulate](delaunay_triangulate.md) · [geodesic_heat](geodesic_heat.md) · [geodesic_heat_grid](geodesic_heat_grid.md) · [mesh_torus](mesh_torus.md)

---
*Provenance: mathgeometry.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
