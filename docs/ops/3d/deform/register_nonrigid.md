---
op: register_nonrigid
dim: 3d
category: deform
in: points × points
out: points
examples: [nonrigid_deform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# register_nonrigid — 3D `deform` op

- **データ種**: `points × points` → `points`
- **呼び出し**: `import deform3d; deform3d.register_nonrigid(src, dst, iters=20, lam=1.0, k_smooth=None)` (または `ops3d.get("register_nonrigid")`)

## 使い方

非剛体 ICP で ``src`` を ``dst`` へ寄せる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [nonrigid_deform](../../../../examples_3d/nonrigid_deform.py) — `py -3.11 examples_3d/nonrigid_deform.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md) · [icp_point2plane](../refine/icp_point2plane.md)

## 同カテゴリ(`deform`)

[tps_fit](tps_fit.md) · [tps_warp](tps_warp.md) · [register_cpd_rigid](register_cpd_rigid.md)

---
*Provenance: deform3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
