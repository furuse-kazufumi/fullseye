---
op: relative_pose
dim: 3d
category: pose_graph
in: pose × pose
out: pose
examples: [pose_graph_slam, sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# relative_pose — 3D `pose_graph` op

- **データ種**: `pose × pose` → `pose`
- **呼び出し**: `import pose_graph; pose_graph.relative_pose(pose_i, pose_j)` (または `ops3d.get("relative_pose")`)

## 使い方

T_i⁻¹ ∘ T_j = i←j の相対姿勢。pose_* = [rvec|t] (6,)。→ (rvec_ij (3,), t_ij (3,))。

姿勢の規約は world←body(``p_world = R p_body + t``)。``T_i⁻¹ = (R_iᵀ, -R_iᵀ t_i)`` と ``T_j`` を
合成して ``R_ij = R_iᵀ R_j``、``t_ij = R_iᵀ (t_j - t_i)`` を求め、回転は回転ベクトル(軸 × 角
[rad]、scipy の ``as_rotvec``)に戻して返す。これは「フレーム i から見たフレーム j の姿勢」で、
``optimize_pose_graph`` に渡すエッジ ``(i, j, rvec_ij, t_ij)`` の計測値をこの規約で作ればそのまま
整合する(GT 姿勢からの合成エッジ生成にも使う)。

- ``pose_i`` / ``pose_j``: 長さ 6 の ``[rvec(3) | t(3)]``。形状検証はしない(``pose[:3]`` /
  ``pose[3:]`` でスライスするだけ)。
- 単位は並進が座標の単位、回転が rad。返る ``rvec_ij`` の角度は [0, π] に折り畳まれる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pose_graph_slam](../../../../examples_3d/pose_graph_slam.py) — `py -3.11 examples_3d/pose_graph_slam.py`
- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](optimize_pose_graph.md) · [mean_edge_error](mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`pose_graph`)

[optimize_pose_graph](optimize_pose_graph.md) · [mean_edge_error](mean_edge_error.md)

---
*Provenance: pose_graph.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
