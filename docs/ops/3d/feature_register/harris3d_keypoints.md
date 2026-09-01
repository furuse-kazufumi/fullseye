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
version: 0.1.0  # fullseye lib version this note was generated for
---

# harris3d_keypoints — 3D `feature_register` op

- **データ種**: `voxel` → `keypoints`
- **呼び出し**: `import feat_harris; feat_harris.harris3d_keypoints(vol, device='cpu', k=0.005, nms=3, topn=64, sigma_i=1.5, response='mineig', rel_thresh=0.01, border=2)` (または `ops3d.get("harris3d_keypoints")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

3D Harris キーポイント検出(2D Harris コーナー検出の 3D 版)。

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
