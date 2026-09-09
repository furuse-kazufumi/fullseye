---
op: project_points
dim: 3d
category: render
in: points
out: keypoints
examples: [pnp_pose_outliers, pose_estimation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# project_points — 3D `render` op

- **データ種**: `points` → `keypoints`
- **呼び出し**: `import fullseye as fs; fs.ledger.project_points(points, K, R=None, t=None)` (実装を直接呼ぶなら `import match3d; match3d.project_points(points, K, R=None, t=None)`、台帳から引くなら `ops3d.get("project_points")`)
- **台帳経由の戻り値**: `fullseye.ledger.project_points(...)` は**宣言 out 型 `keypoints` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.project_points.raw(...)`、または `match3d.project_points` を直接呼ぶ。
  - 本体の返り: `(uv (N,2), depth (N,)) → uv`

## 使い方

3D 点群 (N,3) → 画像座標 (u,v) と深度。ピンホール(depth_to_points の順方向)。

K=カメラ内部行列 [[fx,0,cx],[0,fy,cy],[0,0,1]]。R,t で外部姿勢。世界モデルの観測写像。

``P_cam = R @ P + t``(``R`` (3,3)、``t`` (3,)。None は恒等・零)を ``u = fx·X/Z + cx``、
``v = fy·Y/Z + cy`` で投影する。返り値 ``(uv (N,2), depth (N,))``: ``uv[:,0] = u``(列)、
``uv[:,1] = v``(行)、``depth`` はカメラ座標の Z(clip 前の生値で、負もそのまま)。
``K`` は ``K[0,0]`` 等で添字するので numpy 配列(nested list は不可)。
Z は ``1e-6`` 以上に clip してから割るので、**カメラ後方の点も捨てず**巨大な u,v になる
(``depth > 0`` で呼び手が除く)。画像外の点も返す(``render_point_depth`` が範囲で切る)。
``depth_to_points`` の逆で、``depth_to_points(render_point_depth(...))`` が往復になる。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pnp_pose_outliers](../../../../examples_3d/pnp_pose_outliers.py) — `py -3.11 examples_3d/pnp_pose_outliers.py`
- [pose_estimation](../../../../examples_3d/pose_estimation.py) — `py -3.11 examples_3d/pose_estimation.py`

## 型が繋がる次の op(`keypoints` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [dlt_pose](../pose_estimation/dlt_pose.md) · [pnp_ransac](../pose_estimation/pnp_ransac.md) · [reprojection_error](../pose_estimation/reprojection_error.md)

## 同カテゴリ(`render`)

[render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md) · [supersample_mesh](supersample_mesh.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
