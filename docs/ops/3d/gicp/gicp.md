---
op: gicp
dim: 3d
category: gicp
in: points × points
out: pose
examples: [gicp_register]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# gicp — 3D `gicp` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import fullseye as fs; fs.ledger.gicp(source, target, max_iter: 'int' = 30, k: 'int' = 20, epsilon: 'float' = 0.001, tol: 'float' = 1e-08, init=None) -> 'dict'` (実装を直接呼ぶなら `import gicp; gicp.gicp(source, target, max_iter: 'int' = 30, k: 'int' = 20, epsilon: 'float' = 0.001, tol: 'float' = 1e-08, init=None) -> 'dict'`、台帳から引くなら `ops3d.get("gicp")`)
- **台帳経由の戻り値**: `fullseye.ledger.gicp(...)` は**宣言 out 型 `pose` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.gicp.raw(...)`、または `gicp.gicp` を直接呼ぶ。

## 使い方

Generalized-ICP(共分散重みマハラノビス ICP)で剛体変換 (R,t) を推定する。

各反復で source→target の最近傍対応を張り、残差 ``d_i = R·s_i + t - q_i`` を
重み ``W_i = (C_target[q_i] + R·C_source[s_i]·Rᵀ)⁻¹`` で測るマハラノビス
コスト ``Σ d_iᵀ W_i d_i`` を、小角線形化 ``R ← (I+[ω]×)R`` の Gauss-Newton で
最小化する。各対応のヤコビアン ``J_i = [-[R·s_i+t]× | I]``(3×6)から
正規方程式 ``(Σ J_iᵀ W_i J_i) x = -(Σ J_iᵀ W_i d_i)``(6×6)を解いて増分
``x=[ω|τ]`` を得、Rodrigues で回転に戻して累積する。

共分散は plane-to-plane(``estimate_covariances``)。point-to-plane が target の
法線方向へ残差を射影する(rank-1)のに対し、GICP は source・target 双方の
full 3×3 共分散を合成した重みを使うため、平面的・ノイズを含む点群で頑健。

ICP はローカル最適化なので **近い初期化を前提**(粗マッチや ``init`` を渡す)。

引数:
    source (N,3): 動かす側の点群。
    target (M,3): 参照側(固定)の点群。
    max_iter: 最大反復数。
    k: 共分散推定の近傍数。
    epsilon: plane-to-plane の法線方向小分散(0<ε<1)。
    tol: 収束閾値。増分並進 ‖τ‖ が ``tol×(target のRMS半径)`` 未満かつ
         増分回転 ‖ω‖(rad)が ``tol`` 未満で打ち切り(スケール相対)。
    init: (R0(3,3), t0(3,)) の初期姿勢タプル、または None(単位)。

返り値:
    dict:
      "R" (3,3) ndarray  — target ≈ R·source + t を満たす回転。
      "t" (3,) ndarray   — 並進。
      "rmse" float       — 最終対応上のユークリッド RMSE(採用点)。
      "iterations" int   — 実反復数。

例外:
    ValueError: 入力形状不正 / 点数不足 / 数値発散(非有限)= fail-closed。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gicp_register](../../../../examples_3d/gicp_register.py) — `py -3.11 examples_3d/gicp_register.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`gicp`)

[estimate_covariances](estimate_covariances.md)

---
*Provenance: gicp.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
