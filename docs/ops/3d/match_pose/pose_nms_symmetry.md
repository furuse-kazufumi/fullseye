---
op: pose_nms_symmetry
dim: 3d
category: match_pose
in: table × points × table
out: table
gpu: なし
examples: [bop_pose_stage1]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# pose_nms_symmetry — 3D `match_pose` op

- **データ種**: `table × points × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pose_nms_symmetry(hypotheses, model_points, symmetries=(), distance_threshold: 'float' = 1.0, top_n: 'int | None' = None) -> 'list[PoseHypothesis]'` (実装を直接呼ぶなら `import ppf; ppf.pose_nms_symmetry(hypotheses, model_points, symmetries=(), distance_threshold: 'float' = 1.0, top_n: 'int | None' = None) -> 'list[PoseHypothesis]'`、台帳から引くなら `ops3d.get("pose_nms_symmetry")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Suppress only symmetry-equivalent poses within a model-space distance.

Candidates are processed by descending ``score`` (then votes).  A candidate
is removed only if the maximum transformed-model-point distance to a kept
pose, minimized over the supplied BOP 4x4 symmetries, is at most
``distance_threshold``.  Consequently a symmetry-equivalent orientation is
merged, while a non-equivalent orientation or another object instance whose
translation is farther away remains.  Identity is inserted automatically.

This is an exact point-set test over the supplied points, not a bounding-box
proxy.  The threshold uses the same unit as ``model_points`` and ``t``.
Empty, non-finite or malformed inputs fail closed.

score と票の順に候補を見て、BOP 4x4 対称変換のどれかを介したモデル点の最大距離が
閾値以下の時だけ抑制する。したがって対称で同じ向きはまとまり、非対称な向きと、
並進の離れた別個体は残る。箱・球の代用ではなく指定モデル点を直接測る。

Examples
--------
>>> points = np.array([[1., 0., 0.], [-1., 0., 0.], [0., .3, .2]])
>>> a = PoseHypothesis(np.eye(3), np.zeros(3), 9, .9, .9, .1)
>>> b = PoseHypothesis(np.eye(3), np.array([5., 0., 0.]), 8, .8, .8, .2)
>>> len(pose_nms_symmetry([a, b], points, distance_threshold=.5))
2

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bop_pose_stage1](../../../../examples_3d/bop_pose_stage1.py) — `py -3.11 examples_3d/bop_pose_stage1.py`

## 型が繋がる次の op(`table` を入力に取れる)

[ppf_pose_hypotheses](ppf_pose_hypotheses.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`match_pose`)

[match_phase_3d](match_phase_3d.md) · [match_pca](match_pca.md) · [find_surface_pose](find_surface_pose.md) · [ppf_pose_hypotheses](ppf_pose_hypotheses.md) · [moment_axes](moment_axes.md) · [match_logpolar_z](match_logpolar_z.md)

---
*Provenance: ppf.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
