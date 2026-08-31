---
op: mean_edge_error
dim: 3d
category: pose_graph
in: pose
out: measurement
examples: [sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# mean_edge_error — 3D `pose_graph` op

- **データ種**: `pose` → `measurement`
- **呼び出し**: `import pose_graph; pose_graph.mean_edge_error(poses, edges)` (または `ops3d.get("mean_edge_error")`)

## 使い方

エッジ残差の RMS(姿勢グラフの整合度)。→ scalar。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`pose_graph`)

[optimize_pose_graph](optimize_pose_graph.md) · [relative_pose](relative_pose.md)

---
*Provenance: pose_graph.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
