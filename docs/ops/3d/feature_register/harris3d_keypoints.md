---
op: harris3d_keypoints
dim: 3d
category: feature_register
in: voxel
out: keypoints
gpu: true
examples: [feature_register]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# harris3d_keypoints — 3D `feature_register` op

- **データ種**: `voxel` → `keypoints`
- **呼び出し**: `import feat_harris; feat_harris.harris3d_keypoints(vol, device='cpu', k=0.005, nms=3, topn=64, sigma_i=1.5, response='mineig', rel_thresh=0.01, border=2)` (または `ops3d.get("harris3d_keypoints")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

3D Harris キーポイント検出(2D Harris コーナー検出の 3D 版)。

voxel 密度場の 3D 勾配 g=(gz,gy,gx) から、各ボクセルで局所構造テンソル
M=Σ_w w·g gᵀ(3x3 対称、gaussian 窓 sigma_i で積和)を組み、コーナー性を
測る。応答が周囲で極大かつ閾値超のボクセルを keypoint とする(初期姿勢
推定なしに検出できるため、大回転+部分重なりの対応付けや ICP の coarse
init 供給に使える)。

コーナー性の指標:
  - "mineig"(既定): 3x3 対称行列の最小固有値(Shi-Tomasi 流)。3 方向すべて
    に構造がある(=角)ほど最小固有値が大きい。閉形式(三角関数法)で算出。
    k 調整不要で頑健(実測 mean repeatability 85%、min 72.5%)。
  - "harris": R = det(M) - k·tr(M)³。3D では固有値 3 個なので tr の 3 乗で
    無次元化。★注意: 密度 voxel の角では det/tr³ 比が経験的に ~0.01 しか
    ないため、2D 標準の k=0.04〜0.06 では全応答が負になり検出 0 になる。
    3D では k≈0.005 が必要(実測 k=0.005 で mean 89.6%)。

引数:
    vol: (D,H,W) 密度 voxel(numpy / torch)。points_to_voxel の出力を想定。
    device: torch デバイス("cpu" 等)。全演算をこのデバイス上で行う。
    k: Harris の感度係数(response="harris" 時のみ有効)。3D 密度場では
        0.005 前後(2D 慣習の 0.04〜0.06 は 3D では強すぎ検出 0 になる)。
    nms: 非最大抑制の立方体窓の一辺(奇数、標準 3 = 3x3x3 近傍)。
    topn: 応答降順で返す keypoint の最大数。
    sigma_i: 構造テンソルの積分窓(gaussian)の標準偏差(voxel)。
    response: "mineig"(既定, 頑健)か "harris"。
    rel_thresh: 応答の閾値 = rel_thresh × 有効領域の最大応答(雑音抑制)。
    border: 端から border ボクセル以内は検出しない(勾配の端効果を除去)。

返り値:
    keypoints: (M,3) float64。keypoint の voxel 座標 (z,y,x)(sobel3d と
        同じ軸順)。応答降順、最大 topn 個。
    responses: (M,) float64。対応する応答値(降順)。

依存: sobel3d(3D 勾配)、_gauss3d(積分窓平滑)。いずれも device 上で動作。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [feature_register](../../../../examples_3d/feature_register.py) — `py -3.11 examples_3d/feature_register.py`

## 型が繋がる次の op(`keypoints` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [dlt_pose](../pose_estimation/dlt_pose.md) · [pnp_ransac](../pose_estimation/pnp_ransac.md) · [reprojection_error](../pose_estimation/reprojection_error.md)

## 同カテゴリ(`feature_register`)

[iss_keypoints](iss_keypoints.md) · [compute_fpfh](compute_fpfh.md) · [shot_descriptor](shot_descriptor.md) · [register_spin](register_spin.md) · [register_fpfh](register_fpfh.md) · [register_shot](register_shot.md)

---
*Provenance: feat_harris.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
