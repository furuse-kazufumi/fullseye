---
op: snake_evolve
dim: segmentation
category: contour
in: image2d × pairs
out: table
examples: [poc_active_contours]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# snake_evolve — SEGMENTATION `contour` op

- **データ種**: `image2d × pairs` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.snake_evolve(image, init_points, *, alpha: 'float' = 0.1, beta: 'float' = 0.1, gamma: 'float' = 1.0, external: 'str' = 'edge', w_line: 'float' = 0.0, w_edge: 'float' = 1.0, sigma: 'float' = 1.0, kappa: 'float' = 1.0, gvf=None, gvf_mu: 'float' = 0.2, max_px_move: 'Optional[float]' = None, n_iter: 'int' = 300, spline_order: 'int' = 3, tol: 'float' = 0.0, resample_every: 'int' = 0, record_every: 'int' = 0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segcontour; segcontour.snake_evolve(image, init_points, *, alpha: 'float' = 0.1, beta: 'float' = 0.1, gamma: 'float' = 1.0, external: 'str' = 'edge', w_line: 'float' = 0.0, w_edge: 'float' = 1.0, sigma: 'float' = 1.0, kappa: 'float' = 1.0, gvf=None, gvf_mu: 'float' = 0.2, max_px_move: 'Optional[float]' = None, n_iter: 'int' = 300, spline_order: 'int' = 3, tol: 'float' = 0.0, resample_every: 'int' = 0, record_every: 'int' = 0) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("snake_evolve")`)

## 使い方

離散 snake(Kass–Witkin–Terzopoulos 1988)の半陰的な更新 x_t = (A + γI)^(-1)(γ x_(t-1) − f_x)(式 (19)(20))。

閉じた snake(周期境界)の点 ``init_points``(N, 2)= [row, col]、N ≥ 5。内部エネルギー
E_int = ½ Σ (α |v_(i+1) − v_i|² + β |v_(i+1) − 2v_i + v_(i−1)|²) = ½ xᵀ A x(陰的)。外力(陽的)は ``external`` で選ぶ:
``"edge"`` = ポテンシャル P = w_line · G_σ*I + w_edge · |∇(G_σ*I)|²、E_ext = −κ Σ P(v_i)(Kass の E_line と E_edge)、
``"potential"`` = ``image`` をそのまま P として使う(第 2 実装と同じ P を渡すため)、
``"gvf"`` = 力そのものが −κ (v, u)(GVF、``gvf`` に ``gvf_field`` の返りを渡すか、``gvf_mu`` で内部で作る)、
``"none"`` = 外力 0。P は ``spline_order`` 次の補間スプライン(値と微分が整合)で点の位置へ。
``max_px_move`` を与えると 1 反復の移動を max_px_move · tanh(Δ) に制限(skimage と同じ。近接勾配の性質は失う)。
``resample_every`` > 0 なら k 反復ごとに弧長で等間隔に打ち直す(凹部へ入るとき点が疎になるのを防ぐ。エネルギーの
単調性はその時点で途切れる)。点は画像の範囲 [0, H−1] × [0, W−1] に切り詰める。
返り値: ``points``(N, 2)、``mask``(折れ線の内側)、``energy`` / ``energy_internal`` / ``energy_external``(反復ごと、
先頭 = 初期。GVF では外力のエネルギーが定義されないので total と external は NaN)、``n_increase``(エネルギーが
増えた反復の数、GVF なら None)、``max_increase``、``lipschitz``(κP のヘッセ行列のスペクトルノルムの格子上の最大 =
外力の勾配の Lipschitz 定数の見積り)、``gamma_ge_lipschitz``(γ ≥ L なら降下補題で単調非増加が保証される)、
``radius_factor``(外力 0 の円の 1 反復の縮み γ/(γ + λ_1) の閉形式)、``history``(record_every ごとの点)、
``n_iter``、``converged``。

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

[gvf_field](gvf_field.md) · [chan_vese_energy](chan_vese_energy.md) · [chan_vese_evolve](chan_vese_evolve.md) · [morph_chan_vese](morph_chan_vese.md) · [morph_geodesic_ac](morph_geodesic_ac.md) · [edge_stop_g](edge_stop_g.md) · [level_set_reinit](level_set_reinit.md) · [drle_evolve](drle_evolve.md)

---
*Provenance: segcontour.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
