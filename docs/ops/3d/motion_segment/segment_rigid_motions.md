---
op: segment_rigid_motions
dim: 3d
category: motion_segment
in: points × points
out: labels
examples: [motion_seg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# segment_rigid_motions — 3D `motion_segment` op

- **データ種**: `points × points` → `labels`
- **呼び出し**: `import motion_seg3d; motion_seg3d.segment_rigid_motions(pts0, pts1, thresh, max_bodies: 'int' = 5, min_inliers=None, n_iter: 'int' = 100, k_sample: 'int' = 6, seed: 'int' = 0) -> 'dict'` (または `ops3d.get("segment_rigid_motions")`)

## 使い方

2 点群を運動が一致する剛体ごとに分割する(反復 RANSAC による multi-body 分割)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_seg](../../../../examples_3d/motion_seg.py) — `py -3.11 examples_3d/motion_seg.py`

## 型が繋がる次の op(`labels` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`motion_segment`)

[estimate_flow](estimate_flow.md) · [fit_rigid](fit_rigid.md)

---
*Provenance: motion_seg3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
