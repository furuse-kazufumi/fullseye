---
op: find_surface_pose
dim: 3d
category: match_pose
in: points × points
out: pose
gpu: なし
examples: [find_surface_pose_bracket]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# find_surface_pose — 3D `match_pose` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import fullseye as fs; fs.ledger.find_surface_pose(model_points, scene_points, model_normals=None, scene_normals=None, dist_step: 'float' = None, angle_bins: 'int' = 30, k_normals: 'int' = 16, **kw) -> 'dict'` (実装を直接呼ぶなら `import ppf; ppf.find_surface_pose(model_points, scene_points, model_normals=None, scene_normals=None, dist_step: 'float' = None, angle_bins: 'int' = 30, k_normals: 'int' = 16, **kw) -> 'dict'`、台帳から引くなら `ops3d.get("find_surface_pose")`)
- **台帳経由の戻り値**: `fullseye.ledger.find_surface_pose(...)` は**宣言 out 型 `pose` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.find_surface_pose.raw(...)`、または `ppf.find_surface_pose` を直接呼ぶ。
  - 本体の返り: `{R, t, rmse, votes, ...}`
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

既知の物体(モデル点群)が場面の点群のどこにあるかを、点対特徴(PPF)の投票と ICP で求める(``pose``)。

HALCON ``find_surface_model`` にあたる初期値の要らない 6-DoF 照合(Drost et al., CVPR 2010):
:func:`ppf_model` でモデルの点対特徴を表にし、:func:`surface_match` で場面の参照点ごとに
投票して上位の仮説を ICP で詰める。同じモデルを多くの場面へ当てるときは 2 段の形を使う。
素の関数(``fullseye.find_surface_pose``)は ``{R, t, rmse, votes, inlier_fraction}`` の
dict を返し、台帳 ``fullseye.ledger.find_surface_pose`` は ``pose`` の正典 ``(R, t)`` を返す
(残りは ``.raw``)。``(R, t)`` はモデルを場面へ写す: ``scene ≈ model @ R.T + t``(点は
(N, 3)、単位はそのまま)。法線を渡さなければ ``k_normals`` 近傍で向きつき法線を推定する。
``dist_step`` の既定はモデルの直径の 1/20、``angle_bins`` は角度の分割数。

★回転対称な物体(球・円柱・平板)は姿勢が一意に決まらない —— 対称の分だけ別の答えが
同じ票を取る。照合が外れたとき(仮説が 1 つも立たない)は ``rmse`` が inf、``votes`` が 0。

空の入力(``model_points`` が 0 要素)は ``ValueError``。
拒否(``ValueError``): 点群が (N, 3) でない、モデル点が 5 個未満、場面の点群が空。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [find_surface_pose_bracket](../../../../examples_3d/find_surface_pose_bracket.py) — `py -3.11 examples_3d/find_surface_pose_bracket.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`match_pose`)

[match_phase_3d](match_phase_3d.md) · [match_pca](match_pca.md) · [moment_axes](moment_axes.md) · [match_logpolar_z](match_logpolar_z.md)

---
*Provenance: ppf.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
