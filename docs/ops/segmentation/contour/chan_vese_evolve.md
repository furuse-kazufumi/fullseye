---
op: chan_vese_evolve
dim: segmentation
category: contour
in: image2d × mask
out: table
examples: [poc_active_contours]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# chan_vese_evolve — SEGMENTATION `contour` op

- **データ種**: `image2d × mask` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.chan_vese_evolve(image, init, *, method: 'str' = 'convex', mu: 'float' = 0.1, nu: 'float' = 0.0, lambda1: 'float' = 1.0, lambda2: 'float' = 1.0, eps: 'float' = 1.0, eta: 'float' = 0.1, dt: 'float' = 5.0, n_iter: 'int' = 200, n_inner: 'int' = 200, tol: 'float' = 0.0, record_every: 'int' = 0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segcontour; segcontour.chan_vese_evolve(image, init, *, method: 'str' = 'convex', mu: 'float' = 0.1, nu: 'float' = 0.0, lambda1: 'float' = 1.0, lambda2: 'float' = 1.0, eps: 'float' = 1.0, eta: 'float' = 0.1, dt: 'float' = 5.0, n_iter: 'int' = 200, n_inner: 'int' = 200, tol: 'float' = 0.0, record_every: 'int' = 0) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("chan_vese_evolve")`)

## 使い方

Chan–Vese 2001 の 2 相のエネルギーを最小化する(既定は凸緩和の交互最小化、レベルセットの勾配降下も選べる)。

2 つの方法:

``method="convex"``(既定)= c の更新(内外の平均 = 最適)と、c を固定した分割の更新の交互最小化。分割の更新は
Chan–Esedoglu–Nikolova 2006 の凸緩和 min_(u∈[0,1]) μ TV(u) + Σ (ν + λ1 (I − c1)² − λ2 (I − c2)²) u を
Chambolle–Pock で ``n_inner`` 回解いて 1/2 で 2 値化する(TV は異方的な前進差分 = 2 値なら 4 近傍の割れ目の数 =
``chan_vese_energy`` の ``perimeter_sharp``。離散の余面積公式で、緩和の最小解をどの閾値で切っても 2 値の最小解)。
鋭いエネルギー(``energy`` = ``chan_vese_energy`` の ``energy_sharp``)は交互最小化で単調非増加 —— 内側の解法の誤差で
増えそうなら更新を捨てて止める(``n_guard``、0 のはず)。
``method="level_set"`` = 滑らかなエネルギー(``chan_vese_energy`` の ``energy``)を **離散エネルギーの厳密な勾配** で降下する。

勾配 = μ(δ_ε'(φ) |Dφ|_η + Dᵀ(δ_ε(φ) Dφ / |Dφ|_η)) − δ_ε(φ)(ν + λ1 (I − c1)² − λ2 (I − c2)²)(D = 前進差分、
Dᵀ = その随伴。連続の極限で −δ_ε κ μ の項になり論文の式 (9) の右辺の符号反転と一致)。c1, c2 は φ ごとの最適値なので
包絡線定理で勾配に入らない。刻みは ``dt`` から始め、Armijo 条件 E_new ≤ E − 10⁻⁴ dt |∇E|² を満たすまで半分にする
(満たしたら次の反復は 1.1 倍、上限 dt)。よってエネルギーは単調非増加(``n_increase`` は 0 のはず、後退の回数は
``n_rejected``)。**実測の限界**: 厳密な勾配は界面を動かすより |φ| を膨らませて H_ε を鋭くする向きにも下がるので、
遠い画素(δ_ε が小さい)は事実上動かず局所解で止まる(楕円 + 雑音 σ = 0.2 で 300 反復後も誤り約 800 画素、convex は
数十画素)。論文が再初期化を「任意」として載せている理由の 1 つ。``init`` = bool のマスク(内側)か φ(内側 φ < 0)。
返り値: ``mask``(φ < 0)、``phi``(convex は 2 値の符号付き距離)、``energy``(先頭 = 初期)、``c1`` / ``c2``、
``n_rejected``、``n_guard``、``n_increase``、``duality_gap``(convex の内側の解法の主双対ギャップ、外側の反復ごと)、
``history``(record_every ごとのマスク)、``n_iter``、``converged``、``method``。

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

[snake_evolve](snake_evolve.md) · [gvf_field](gvf_field.md) · [chan_vese_energy](chan_vese_energy.md) · [morph_chan_vese](morph_chan_vese.md) · [morph_geodesic_ac](morph_geodesic_ac.md) · [edge_stop_g](edge_stop_g.md) · [level_set_reinit](level_set_reinit.md) · [drle_evolve](drle_evolve.md)

---
*Provenance: segcontour.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
