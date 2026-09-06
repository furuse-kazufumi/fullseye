---
op: match_pca
dim: 3d
category: match_pose
in: points × points
out: pose
examples: [shape_desc_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# match_pca — 3D `match_pose` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import match3d; match3d.match_pca(pts_scene, pts_model)` (または `ops3d.get("match_pca")`)

## 使い方

PCA 姿勢マッチング(構造=point cloud × 手法=主軸整列)。

両雲の主軸を合わせる粗い剛体変換(回転 R + 並進 t)を返す。NCC/位相相関が扱えない
**回転**をここで担う(符号の 4 通り曖昧性は最小二乗で解消。この残差は両雲の点が
同じ並び順で対応している前提の粗い基準 — 無対応の実測雲では ICP 等で後段精密化を)。
返り値 (R(3,3), t(3,))。

返り値の意味: ``pts_scene ≈ (R @ pts_model.T).T + t``(``t = c_scene − R·c_model``)。R は
必ず ``det=+1`` の回転(反射は出さない)。残差は点を index 順に対応させて測るので、無対応の
雲では 4 候補の選択が当てにならない(その場合は ``icp_point2point_3d`` に ``init_R/init_t``
として渡して精緻化する)。主軸が縮退している(球・円柱など固有値が等しい)雲では軸が不定で
結果は安定しない。点数は両雲で違ってよい。入力は (N,3)(検証は ``moment_axes`` 任せで無い)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape_desc_pose](../../../../examples_3d/shape_desc_pose.py) — `py -3.11 examples_3d/shape_desc_pose.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`match_pose`)

[match_phase_3d](match_phase_3d.md) · [moment_axes](moment_axes.md) · [match_logpolar_z](match_logpolar_z.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
