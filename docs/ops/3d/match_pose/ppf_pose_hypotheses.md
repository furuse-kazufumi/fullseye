---
op: ppf_pose_hypotheses
dim: 3d
category: match_pose
in: table × points
out: table
gpu: なし
examples: [bop_pose_stage1]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.2.0  # fullseye lib version this note was generated for
---

# ppf_pose_hypotheses — 3D `match_pose` op

- **データ種**: `table × points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ppf_pose_hypotheses(model: 'dict', scene_points, scene_normals=None, top_n: 'int' = 5, ref_fraction: 'float' = 0.3, refine: 'bool' = True, k_normals: 'int' = 16, seed: 'int' = 0) -> 'list[PoseHypothesis]'` (実装を直接呼ぶなら `import ppf; ppf.ppf_pose_hypotheses(model: 'dict', scene_points, scene_normals=None, top_n: 'int' = 5, ref_fraction: 'float' = 0.3, refine: 'bool' = True, k_normals: 'int' = 16, seed: 'int' = 0) -> 'list[PoseHypothesis]'`、台帳から引くなら `ops3d.get("ppf_pose_hypotheses")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Return the top-N PPF poses instead of collapsing the vote to one pose.

``model`` is the reusable descriptor from :func:`ppf_model`.  Each result is
a :class:`PoseHypothesis` containing ``R``, ``t``, raw votes, a bounded score,
inlier fraction and ICP RMSE.  The score is
``inlier_fraction / (1 + rmse / model_diameter)``; it is used only for
ranking and is not a calibrated probability.  The inlier distance is two
PPF distance steps.  With ``refine=False`` RMSE is measured from the voted
pose rather than reported as NaN.

Empty/non-finite input, bad normals, invalid ``top_n``/``ref_fraction`` and
an accumulator with no votes raise ``ValueError``.  The returned list can
contain symmetry-equivalent or same-instance poses; pass it to
:func:`pose_nms_symmetry` when those should be merged.

既存 PPF 表から最良1件へ潰さず上位 N 姿勢を返す。返りは R、t、票、順位用
score、インライア率、ICP RMSE を持つ。空、非有限値、法線不正、無投票は
fail-closed。対称で等価な候補の統合は :func:`pose_nms_symmetry` が担う。

Examples
--------
>>> import numpy as np
>>> x = np.linspace(-1.0, 1.0, 6)
>>> model_points = np.array([(a, b, 0.2*a*b) for a in x for b in x])
>>> normals = np.tile([0.0, 0.0, 1.0], (len(model_points), 1))
>>> descriptor = ppf_model(model_points, normals, angle_bins=24)
>>> t_true = np.array([0.3, -0.2, 1.4])
>>> scene = model_points + t_true
>>> poses = ppf_pose_hypotheses(descriptor, scene, normals, top_n=2, seed=3)
>>> bool(np.linalg.norm(poses[0].t - t_true) < 1e-6)
True

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bop_pose_stage1](../../../../examples_3d/bop_pose_stage1.py) — `py -3.11 examples_3d/bop_pose_stage1.py`

## 型が繋がる次の op(`table` を入力に取れる)

[pose_nms_symmetry](pose_nms_symmetry.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`match_pose`)

[match_phase_3d](match_phase_3d.md) · [match_pca](match_pca.md) · [find_surface_pose](find_surface_pose.md) · [pose_nms_symmetry](pose_nms_symmetry.md) · [moment_axes](moment_axes.md) · [match_logpolar_z](match_logpolar_z.md)

---
*Provenance: ppf.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
