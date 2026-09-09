---
op: icp_point2point_3d
dim: 3d
category: refine
in: points × points
out: pose
examples: [gicp_register, itokawa_self_register, itokawa_shape_match, partial_overlap_icp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# icp_point2point_3d — 3D `refine` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import fullseye as fs; fs.ledger.icp_point2point_3d(src, dst, iters=50, init_R=None, init_t=None, tol=1e-06, max_corr_dist=None, trim_ratio=None, device='cpu')` (実装を直接呼ぶなら `import match3d; match3d.icp_point2point_3d(src, dst, iters=50, init_R=None, init_t=None, tol=1e-06, max_corr_dist=None, trim_ratio=None, device='cpu')`、台帳から引くなら `ops3d.get("icp_point2point_3d")`)

## 使い方

点群を point-to-point ICP(Kabsch/SVD)で精緻化する。

粗いマッチ推定(整数NCC / Fourier-Mellin±3° / Hough±0.5voxel)で得た
初期姿勢 (init_R, init_t) を出発点に、src 側点群を dst 側点群へ剛体変換で
位置合わせする。各反復で最近傍対応(cKDTree)を張り直し、Kabsch アルゴリズム
(SVD)で相対回転・並進を求めて累積することで、対応が既知でなくても
サブボクセル精度へ収束させる。

部分重なり・外れ値には Trimmed ICP(距離の小さい対応のみ採用)と
絶対距離ゲート(max_corr_dist)で対処する。最終 RMSE は実際に採用した
対応(インライア)上で評価するため、部分観測でも姿勢品質を正しく反映する。

引数:
    src: (N,3) 移動側点群(torch.Tensor か numpy.ndarray)。
    dst: (M,3) 固定側(参照)点群。
    iters: 最大反復回数。
    init_R: (3,3) 初期回転。None なら単位行列。
    init_t: (3,) 初期並進。None なら零ベクトル。
    tol: RMSE の相対改善がこの値を下回れば収束打ち切り。
    max_corr_dist: この距離を超える対応を外れ値として棄却(None で無効)。
    trim_ratio: 0<r<=1。各反復で最近傍距離の小さい上位 r 割の対応のみ
        採用する Trimmed ICP。部分重なり(重なり率 r)に有効。None で無効。
    device: torch デバイス("cpu" 等)。SVD をこのデバイス上で解く。

返り値:
    R: (3,3) 回転。dst ~= src @ R.T + t を満たす。**torch がある環境では
       ``torch.Tensor``、無ければ同じ値の ``numpy.ndarray``**(2026-09-07 に
       本体を numpy 化したときも、互換のため型は据え置いた)。
       ★同じ族の :func:`icp_point2plane` は**常に numpy を返す** —— 族の中で
       型が揃っていないので、下流では ``np.asarray(R)`` を通すのが安全
       (どちらでも動く。破壊的変更を避けてこの不揃いを残してある)。
    t: (3,) 並進(R と同じ型)。
    info: dict。"rmse"(採用対応上の最終RMSE), "iters"(実反復数),
          "converged"(bool), "inliers"(採用対応数), "rmse_history"(list)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gicp_register](../../../../examples_3d/gicp_register.py) — `py -3.11 examples_3d/gicp_register.py`
- [itokawa_self_register](../../../../examples_3d/itokawa_self_register.py) — `py -3.11 examples_3d/itokawa_self_register.py`
- [itokawa_shape_match](../../../../examples_3d/itokawa_shape_match.py) — `py -3.11 examples_3d/itokawa_shape_match.py`
- [partial_overlap_icp](../../../../examples_3d/partial_overlap_icp.py) — `py -3.11 examples_3d/partial_overlap_icp.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`refine`)

[refine_peak_newton](refine_peak_newton.md) · [refine_translation_lk](refine_translation_lk.md) · [refine_lm](refine_lm.md) · [refine_rotation_z](refine_rotation_z.md) · [icp_point2plane](icp_point2plane.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
