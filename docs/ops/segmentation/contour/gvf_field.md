---
op: gvf_field
dim: segmentation
category: contour
in: image2d
out: table
examples: [poc_active_contours]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# gvf_field — SEGMENTATION `contour` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gvf_field(image, *, mu: 'float' = 0.2, sigma: 'float' = 1.0, method: 'str' = 'direct', n_iter: 'int' = 2000, dt: 'Optional[float]' = None, edge_map=None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segcontour; segcontour.gvf_field(image, *, mu: 'float' = 0.2, sigma: 'float' = 1.0, method: 'str' = 'direct', n_iter: 'int' = 2000, dt: 'Optional[float]' = None, edge_map=None) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("gvf_field")`)

## 使い方

勾配ベクトル流(Xu–Prince 1998): 辺の地図 f の勾配を、辺から離れた所へ滑らかに拡散した場 (u, v)。

E = ∬ μ(u_x² + u_y² + v_x² + v_y²) + |∇f|² |(u, v) − ∇f|² の最小化。Euler 方程式
μ∇²u − (u − f_x)(f_x² + f_y²) = 0、μ∇²v − (v − f_y)(f_x² + f_y²) = 0(線形)。
``method="iterate"`` = 論文の時間発展 u ← u + Δt(μ∇²u − b(u − f_x))、b = |∇f|²(陽的、Δt ≤ 1/(4μ + max b))。
``method="direct"`` = 同じ離散方程式 (μL − diag b) u = −b f_x を疎行列で直接解く(定常解そのもの)。
辺の地図 f は既定で |∇(G_σ * I)| を最大 1 に正規化したもの(``edge_map`` で直接与えてもよい)。境界は Neumann。
u = 列(x)方向、v = 行(y)方向の成分。
返り値: ``u`` / ``v``、``edge_map``、``fx`` / ``fy``、``residual_max``(Euler 方程式の残差の最大)、``residual_rel``
(残差 / max(b |∇f|))、``n_iter``、``method``、``mu``。f が平坦なら場は 0(残差 0)。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [active_contours_and_level_sets](../guides/active_contours_and_level_sets.md) — 変分・動的輪郭とレベルセット — どの輪郭がどこで止まり、何を保証するか

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_active_contours](../../../../examples/poc_active_contours.py) — `py -3.11 examples/poc_active_contours.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`contour`)

[snake_evolve](snake_evolve.md) · [chan_vese_energy](chan_vese_energy.md) · [chan_vese_evolve](chan_vese_evolve.md) · [morph_chan_vese](morph_chan_vese.md) · [morph_geodesic_ac](morph_geodesic_ac.md) · [edge_stop_g](edge_stop_g.md) · [level_set_reinit](level_set_reinit.md) · [drle_evolve](drle_evolve.md)

---
*Provenance: segcontour.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
