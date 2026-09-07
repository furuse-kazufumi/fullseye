---
op: annotate3d_bbox
dim: 3d
category: annotate3d
in: image2d
out: image2d
examples: [annotate3d_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# annotate3d_bbox — 3D `annotate3d` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.annotate3d_bbox(img, bounds, pose, K, depth=None, color='emphasis', width=1.5, occlusion_tol=0.01, scheme='okabe_ito')` (実装を直接呼ぶなら `import annotate3d; annotate3d.annotate3d_bbox(img, bounds, pose, K, depth=None, color='emphasis', width=1.5, occlusion_tol=0.01, scheme='okabe_ito')`、台帳から引くなら `ops3d.get("annotate3d_bbox")`)

## 使い方

画像(image2d)を返す: 軸平行の 3-D 箱 ``((xmin,ymin,zmin),(xmax,ymax,zmax))`` の 12 辺を射影して描く。

``depth`` を渡すと、**両端が隠れている辺**を破線にする。

Raises
------
ValueError
    bounds の形 / min > max、角がカメラの後ろ。

手順: ``bounds`` から 8 つの角 ``(x_i, y_j, z_k)``(i, j, k ∈ {min, max})を作り、
まとめて射影(``annotate3d_project`` と同じ慣習)。12 辺を
``annotate._aa_polyline`` で描く。辺の両端が ``hidden`` なら破線、片端だけなら
実線。

引数:
- ``bounds``: ``((xmin, ymin, zmin), (xmax, ymax, zmax))`` の ``(2, 3)``(object
  座標、有限、各軸で ``max >= min``。``max == min`` の潰れた箱は許す)。点群なら
  ``points.min(0)`` / ``points.max(0)``、メッシュなら ``V`` から作る。
- ``width``: 線幅 [px]、``>= 0.5`` の実数。``color``: 役割名か RGB。
- ``depth``: 前方距離画像(``render3d.render_mesh`` の ``depth``)。
  ``occlusion_tol``: ``[0, 1)``。

返り値: 描画済みの新しい画像(float64 ``[0, 1]``、入力は変更しない)。

エラーになる条件: ``bounds`` が ``(2, 3)`` でない・非有限・``max < min`` の軸が
ある / **8 角のいずれかが** ``z <= 1e-9``(カメラ面上か後ろ。箱が視点を囲む場合は
描けない) / 姿勢・``K``・``depth`` の不正。角が画像の外に出るのはエラーに
しない(線は枠外まで引かれ、見た目は切れる)。

注意: 軸平行(世界座標に沿った)箱のみ。回転した箱(``smallest_box3`` の
``corners``)を描くには、8 角を自分で射影(``annotate3d_project``)して 2-D の
``annotate`` 線描画で結ぶ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate3d_figure](../../../../examples_3d/annotate3d_figure.py) — `py -3.11 examples_3d/annotate3d_figure.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`annotate3d`)

[annotate3d_project](annotate3d_project.md) · [annotate3d_arrow](annotate3d_arrow.md) · [annotate3d_label](annotate3d_label.md) · [annotate3d_scale_bar](annotate3d_scale_bar.md) · [annotate3d_axes](annotate3d_axes.md) · [annotate3d_measure](annotate3d_measure.md)

---
*Provenance: annotate3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
