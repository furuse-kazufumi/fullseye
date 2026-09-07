---
op: register_spin
dim: 3d
category: feature_register
in: points × points
out: pose
examples: [feature_register]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# register_spin — 3D `feature_register` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import fullseye as fs; fs.ledger.register_spin(src, dst, device='cpu', n_keypoints=220, normal_k=18, support_radius=None, n_alpha=16, n_beta=16, support_angle_deg=60.0, lowe_ratio=0.85, ransac_iters=4000, inlier_thr=None, min_inliers=8, seed=0)` (実装を直接呼ぶなら `import feat_spin; feat_spin.register_spin(src, dst, device='cpu', n_keypoints=220, normal_k=18, support_radius=None, n_alpha=16, n_beta=16, support_angle_deg=60.0, lowe_ratio=0.85, ransac_iters=4000, inlier_thr=None, min_inliers=8, seed=0)`、台帳から引くなら `ops3d.get("register_spin")`)

## 使い方

Spin Image 記述子 + RANSAC による初期推定なし疎特徴剛体位置合わせ。

2 点群 ``src`` (N,3), ``dst`` (M,3) を、初期姿勢の事前情報なしに位置合わせする。
各点の法線(局所 PCA、重心から外向きに符号統一 = 剛体変換で不変)を軸として近傍点を
(α=軸からの距離, β=軸方向の高さ) の 2D ヒストグラムへ「回転(spin)」蓄積した
Spin Image 記述子(Johnson & Hebert 1997)を keypoint ごとに作り、記述子空間の
最近傍でマッチ(Lowe ratio test で選別)、RANSAC(3 点最小標本 + Kabsch)で
外れ値に頑健な剛体変換を推定する。密マッチ(NCC/位相相関/Hough)や PCA 主軸整列と
違い、**大回転 + 部分重なり**でも局所特徴の対応から姿勢を復元できるため、ICP の
前段(coarse init 供給)に使える。返す姿勢は ``dst ~= src @ R.T + t``
(= ``R @ src_i + t``)の規約に従う(``icp_point2point_3d`` と同一)。

引数:
    src: (N,3) 移動側点群(numpy.ndarray か torch.Tensor)。
    dst: (M,3) 固定側(参照)点群。
    device: torch デバイス("cpu" 等)。SVD/最終姿勢をこの上で解く。
    n_keypoints: 各点群から抽出する keypoint 数(等間隔サブサンプル)。
    normal_k: 法線推定に使う近傍点数(局所 PCA)。
    support_radius: Spin Image の支持半径。None なら各点群個別の bbox 対角(大きい方)
        の 0.30 倍(未知並進で汚れないよう和集合でなく個別に測る)。
    n_alpha, n_beta: Spin Image の (α, β) ビン数(記述子は n_alpha*n_beta 次元)。
    support_angle_deg: 支持角しきい値(度)。keypoint 法線とこの角度以内の法線を持つ
        支持点のみ蓄積(遮蔽・裏面に頑健)。>=90 で無効。
    lowe_ratio: Lowe 比率テストしきい値(d1 < ratio*d2 の対応のみ採用)。
    ransac_iters: RANSAC 反復数。
    inlier_thr: RANSAC のインライア距離しきい値。None なら bbox 対角の 0.04 倍。
    min_inliers: 有効姿勢とみなす最小インライア数(``ok`` 判定)。
    seed: RANSAC 乱数シード。
返り値:
    R: (3,3) torch.Tensor。dst ~= src @ R.T + t を満たす回転。
    t: (3,) torch.Tensor。並進。
    info: dict。"n_matches"(ratio test 通過対応数), "inliers"(RANSAC最終),
          "inlier_ratio", "rmse"(インライア上 RMSE), "support_radius",
          "inlier_thr", "ok"(min_inliers 以上か)。

注意:
    - 記述子は法線符号に依存する。重心から外向きの符号統一は、法線が概ね放射状で
      n·(p-重心) の符号が安定な形状(lumpy な閉曲面等)で有効。薄板・管状など
      n·(p-重心)≈0 の領域が多い形状では 2 雲間で符号が反転しうる。
    - 平面・球など曲率が空間的に一様な部位は記述子が縮退し ratio test で対応が消える
      (無特徴形状には不向き)。overlap が概ね 60% を切ると成功率が急落し、失敗時は
      幾何整合だが誤りの解に RANSAC がロックして壊滅的な誤差になりうる(``ok`` /
      ``inlier_ratio`` ゲートの併用を推奨)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [feature_register](../../../../examples_3d/feature_register.py) — `py -3.11 examples_3d/feature_register.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`feature_register`)

[harris3d_keypoints](harris3d_keypoints.md) · [iss_keypoints](iss_keypoints.md) · [compute_fpfh](compute_fpfh.md) · [shot_descriptor](shot_descriptor.md) · [register_fpfh](register_fpfh.md) · [register_shot](register_shot.md)

---
*Provenance: feat_spin.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
