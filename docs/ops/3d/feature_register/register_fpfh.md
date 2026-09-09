---
op: register_fpfh
dim: 3d
category: feature_register
in: points × points
out: pose
examples: [feature_register]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# register_fpfh — 3D `feature_register` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import fullseye as fs; fs.ledger.register_fpfh(src, dst, src_normals=None, dst_normals=None, voxel_size=None, normal_k=16, feature_k=60, n_bins=11, ransac_iters=8000, inlier_thr=None, edge_sim=0.9, mutual=True, ratio=0.95, seed=0, device='cpu')` (実装を直接呼ぶなら `import feat_fpfh; feat_fpfh.register_fpfh(src, dst, src_normals=None, dst_normals=None, voxel_size=None, normal_k=16, feature_k=60, n_bins=11, ransac_iters=8000, inlier_thr=None, edge_sim=0.9, mutual=True, ratio=0.95, seed=0, device='cpu')`、台帳から引くなら `ops3d.get("register_fpfh")`)

## 使い方

FPFH 記述子 + RANSAC で **初期推定なし** の剛体位置合わせ (R,t) を推定する。

2D の Harris/SIFT に相当する疎 feature マッチの 3D 版。両雲を FPFH 記述子で表し、
記述子空間の最近傍で対応を張り(相互最近傍 + Lowe ratio でフィルタ)、RANSAC で
外れ値に頑健な剛体姿勢を解く。密マッチ(NCC/Hough)や PCA と違い、大回転(50-70°)
+並進+部分重なりでも初期推定なしに姿勢を出せるのが価値。得た (R,t) は ICP の初期値
(coarse init)として渡すと表面精度まで締められる(dst ≈ src @ R.T + t の ICP 慣習)。

パイプライン:
    1) voxel ダウンサンプル(独立サンプリング 2 雲の近傍を共通解像度へ揃える。
       FPFH の対応正答率を大きく左右する必須前処理)。
    2) 法線推定(局所 PCA)。src_normals/dst_normals を渡せばそれを使う。
    3) FPFH 記述子(SPFH→距離重み合成)。
    4) 記述子 NN マッチ(mutual + ratio)。
    5) RANSAC: 3 点サンプル → edge-length 整合プレフィルタ → Kabsch → **全点フィットネス**
       (src 全点を変換し dst 最近傍が閾値内に入る割合)で採点。対応(~100点)だけの
       採点は誤姿勢に固着しやすいため、全点フィットネスで頑健化する。
    6) 最良姿勢の対応インライアで再フィット。

引数:
    src (N,3), dst (M,3): 位置合わせする 2 点群(numpy/torch)。
    src_normals, dst_normals ((N,3)/(M,3) or None): 事前法線。None なら内部推定
        (ただし voxel_size>0 のときは座標が変わるため常に再推定)。
    voxel_size (float or None): ダウンサンプル辺長。None で dst 解像度×2.5 を自動採用。
        0/None で無効化(生点群のまま。独立サンプリングでは非推奨)。
    normal_k (int): 法線推定の近傍数。
    feature_k (int): FPFH の近傍数(大きいほど記述子が安定・識別的。60 前後を推奨)。
    n_bins (int): 1 特徴あたりのヒストグラムビン数(記述子次元 = 3*n_bins)。
    ransac_iters (int): RANSAC 反復数。
    inlier_thr (float or None): インライア距離閾値。None で(ダウンサンプル後)解像度×3。
    edge_sim (float): 三つ組の辺長比の許容(0<edge_sim<=1、1 に近いほど厳格)。
    mutual (bool): 相互最近傍フィルタ。ratio (float or None): Lowe ratio。
    seed (int): RANSAC 乱数種(restart 時に変える)。device (str): 返り値テンソルの device。

返り値:
    R (3,3) torch.Tensor(device 上), t (3,) torch.Tensor,
    info dict: {"n_corr"(対応数), "inliers"(インライア数), "inlier_ratio",
                "fitness"(全点フィットネス=restart 選択の指標), "rmse"(インライア RMSE),
                "inlier_thr", "src_corr","dst_corr"(対応 index)}。

注意(honest): FPFH は coarse registration であり、独立サンプリング+ノイズ+部分重なり
の難条件では回転誤差が数度残る(実測: 62°回転・重なり~64%・ノイズ0.5×解像度で
RANSAC 後 中央値 ~4.4°、~90% が <8°、残り ~10% は 8-9° の境界。ICP で締めると 100%
が <8°・中央値 ~0.5°)。ノイズが点間隔(解像度)並み以上になると法線・角特徴が
崩れ記述子が識別力を失う(実測: ノイズ≥1.0×解像度で成功率が低下)。RANSAC は乱択
なので実運用では数回 restart し info["fitness"] 最大の結果を採るとよい。

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

[harris3d_keypoints](harris3d_keypoints.md) · [iss_keypoints](iss_keypoints.md) · [compute_fpfh](compute_fpfh.md) · [shot_descriptor](shot_descriptor.md) · [register_spin](register_spin.md) · [register_shot](register_shot.md)

---
*Provenance: feat_fpfh.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
