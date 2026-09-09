---
op: annotate3d_project
dim: 3d
category: annotate3d
in: points
out: table
examples: [annotate3d_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# annotate3d_project — 3D `annotate3d` op

- **データ種**: `points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.annotate3d_project(points, pose, K, depth=None, shape=None, occlusion_tol=0.01)` (実装を直接呼ぶなら `import annotate3d; annotate3d.annotate3d_project(points, pose, K, depth=None, shape=None, occlusion_tol=0.01)`、台帳から引くなら `ops3d.get("annotate3d_project")`)

## 使い方

table(dict)を返す: 3-D 点の画素座標・前方距離・画像内/遮蔽の判定(:func:`project_anchors`)。

描画を伴わない「射影だけ」の op。annotate3d の全描画 op が内部で使う判定を
そのまま表として返すので、自前のプロット・数値検証・「この点は見えるか」の
分岐に使う。

射影(閉形式、render3d と同一慣習): ``X_c = R X + t``(``pose`` は 4x4 の
object→camera、または ``(R, t)`` の 2-tuple)。カメラは **local -Z を見る**ので
前方距離は ``z = -X_c[2]``。画素は ``u = fx X_c[0]/z + skew X_c[1]/z + cx``、
``v = cy - fy X_c[1]/z``(``K`` は 3x3、``K[0,1]`` の skew も使う。画素中心は
整数座標、``u`` = 列、``v`` = 行)。

引数:
- ``points``: ``(N, 3)`` または ``(3,)``(object 座標、有限)。
- ``depth``: ``(H, W)`` の前方距離画像(``render3d.render_mesh`` の ``depth``、
  背景は ``+inf``)。渡すと ``shape`` はこれから取り、遮蔽を判定する。
- ``shape``: ``(H, W)``。``depth`` が無いときの画像内判定に使う。
- ``occlusion_tol``: ``[0, 1)``。画素の深度 ``d`` が ``d < z * (1 - tol)`` なら
  隠れ(z-buffer 離散化の許容)。

返り値(dict、全て長さ ``N``):
- ``uv`` ``(N, 2)`` float — ``(u, v)`` 画素座標。後ろの点は NaN。
- ``depth`` ``(N,)`` — 前方距離 ``z``(後ろは負)。
- ``in_front`` — ``z > 1e-9``。
- ``in_image`` — ``0 <= u <= W-1`` かつ ``0 <= v <= H-1``(前方の点のみ)。
  ``shape`` も ``depth`` も無ければ全 True(未判定)。
- ``hidden`` — ``depth`` があるときだけ判定(画素は最近傍丸め)。無ければ全 False。
- ``visible`` = ``in_front & in_image & ~hidden``。

検証(``ValueError``): ``pose`` が 4x4 でも ``(R, t)`` でもない・非有限・回転部の
行列式がほぼ 0 / ``K`` が 3x3 でない・非有限・``fx`` か ``fy`` が 0 / ``points`` の
形・非有限 / ``depth`` が 2-D でない・``shape`` と不一致・NaN を含む /
``occlusion_tol`` が ``[0, 1)`` の外。**後ろの点はここではエラーにしない**
(``in_front=False`` で返す。描画 op はそこで ``ValueError`` にする)。

注意: ``camera.project_points`` は +Z を見る別慣習(OpenCV 流)なので、その
姿勢を渡すと全点が後ろ扱いになる。``render3d.render_mesh`` に渡した ``pose`` /
``intrinsics`` をそのまま渡す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate3d_figure](../../../../examples_3d/annotate3d_figure.py) — `py -3.11 examples_3d/annotate3d_figure.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`annotate3d`)

[annotate3d_arrow](annotate3d_arrow.md) · [annotate3d_label](annotate3d_label.md) · [annotate3d_scale_bar](annotate3d_scale_bar.md) · [annotate3d_axes](annotate3d_axes.md) · [annotate3d_bbox](annotate3d_bbox.md) · [annotate3d_measure](annotate3d_measure.md)

---
*Provenance: annotate3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
