---
op: carve_look_at
dim: 3d
category: space_carving
in: vector
out: pose
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# carve_look_at — 3D `space_carving` op

- **データ種**: `vector` → `pose`
- **呼び出し**: `import fullseye as fs; fs.ledger.carve_look_at(eye, target=(0.0, 0.0, 0.0), up=(0.0, 0.0, 1.0))` (実装を直接呼ぶなら `import visualhull; visualhull.carve_look_at(eye, target=(0.0, 0.0, 0.0), up=(0.0, 0.0, 1.0))`、台帳から引くなら `ops3d.get("carve_look_at")`)

## 使い方

``carve`` / ``synthesize_silhouette`` に渡せるカメラ姿勢 ``(R, t)`` を作る。

:func:`look_at` と同じ実装の、**公開層から引ける名前**。2026-09-08 に追加した ——
それまで空間彫刻の正しい姿勢ヘルパは ``fs.`` / ``fs.op.`` / ``fs.ledger.`` の
どこからも引けず、``fs.op_find("look")`` も 0 件だった。一方で ``fs.look_at`` は
**別物**(``render3d`` の gluLookAt 版、4x4・**−Z 前方**)なので、その ``M[:3,:3]``
と ``M[:3,3]`` を渡すと全点がカメラ後方に落ち、**例外を出さずに空のシルエット**が
返る。同じ名前で規約が逆という、いちばん静かに間違える組み合わせだった。

こちらは OpenCV 規約(``X_cam = R X + t``、+Z 前方・+X 右・+Y 下)。

Parameters
----------
eye : (3,) array_like       カメラ中心(ワールド座標)。
target : (3,) array_like    注視点(既定は原点)。
up : (3,) array_like        上方向(視線とほぼ平行なら自動で代替軸へ切り替える)。

Returns
-------
(R (3,3), t (3,))  ``synthesize_silhouette(pts, K, R, t, size)`` にそのまま渡せる。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`space_carving`)

[carve](carve.md) · [visual_hull](visual_hull.md) · [synthesize_silhouette](synthesize_silhouette.md)

---
*Provenance: visualhull.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
