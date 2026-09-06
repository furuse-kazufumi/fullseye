---
op: register_shot
dim: 3d
category: feature_register
in: points × points
out: pose
examples: [feature_register]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# register_shot — 3D `feature_register` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import feat_shot; feat_shot.register_shot(src, dst, radius=None, normal_k=16, ratio=0.9, ransac_iters=2000, inlier_thr=None, refine_icp=True, max_kp=400, device='cpu', seed=0)` (または `ops3d.get("register_shot")`)

## 使い方

SHOT 記述子による疎特徴マッチング + RANSAC 剛体姿勢推定(全パイプライン)。

初期推定なしに、大回転・部分重なりの 2 点群を対応付けて剛体変換
(回転 R + 並進 t)を返す。密マッチ(NCC/Hough/PCA)と異なり、ISS
キーポイントごとに局所参照フレーム(LRF)を張り、球状分割セルの
法線角度ヒストグラム(SHOT)で記述 → Lowe 比率テスト + 相互最近傍で
マッチ → RANSAC で外れ値に頑健に姿勢推定する。得た姿勢は ICP の
粗初期値(coarse init)供給にも使える。

LRF の符号曖昧性: 距離重み付き共分散の固有ベクトルは符号が定まらない
ため、各軸(x=最大, z=最小 固有値)を近傍ベクトル (p_i-p) の投影多数派
へ合わせ(Tombari の符号則)、y=z×x で右手系を構成する。点法線も同則で
近傍質量から離れる向き(局所外向き)に統一するため回転に共変で部分
重なりにも安定。両点群に同一則を適用することで記述子の repeatability を担保。

引数:
    src, dst: (N,3)/(M,3) 点群(numpy か torch)。src を dst へ合わせる。
    radius: SHOT 支持半径。None なら各点群自身の bbox 対角(小さい方)の 0.15 倍
        (結合 bbox は並進で対角が水増しされスケールが狂うため使わない)。
    normal_k: 法線推定の knn 数。
    ratio: Lowe 比率テスト閾値(小さいほど厳格)。
    ransac_iters: RANSAC 反復数。
    inlier_thr: RANSAC インライア距離。None なら bbox 対角の 0.03 倍。
    refine_icp: True なら得た姿勢を初期値に Trimmed ICP(icp_point2point_3d)で精緻化。
    max_kp: キーポイント上限。
    device: torch デバイス("cpu" 等)。SVD/ICP をこの上で解く。
    seed: RANSAC 乱数種。

返り値:
    R: (3,3) numpy。dst ≈ src @ R.T + t を満たす回転(icp と同規約)。
    t: (3,) numpy。並進。
    info: dict。"n_kp_src","n_kp_dst","n_matches","n_inliers","inlier_ratio",
          "icp_rmse"(refine_icp 時),"ok"(True=推定成功; インライア<4 は
          信頼不可として False + 単位変換を返す)。

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

[harris3d_keypoints](harris3d_keypoints.md) · [iss_keypoints](iss_keypoints.md) · [compute_fpfh](compute_fpfh.md) · [shot_descriptor](shot_descriptor.md) · [register_spin](register_spin.md) · [register_fpfh](register_fpfh.md)

---
*Provenance: feat_shot.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
