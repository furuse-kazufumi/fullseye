---
op: annotate3d_axes
dim: 3d
category: annotate3d
in: image2d
out: image2d
examples: [annotate3d_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# annotate3d_axes — 3D `annotate3d` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import annotate3d; annotate3d.annotate3d_axes(img, pose, K, origin=(0.0, 0.0, 0.0), length=1.0, depth=None, labels=('X', 'Y', 'Z'), colors=('wrong', 'right', 'reference'), width=2, font_size=11, occlusion_tol=0.01, scheme='okabe_ito', font_path=None)` (または `ops3d.get("annotate3d_axes")`)

## 使い方

画像(image2d)を返す: 世界座標の 3 軸(gnomon)を ``origin`` から射影して描く。

Raises
------
ValueError
    length が非正、原点や軸端がカメラの後ろ、labels/colors が 3 つでない、
    軸の文字が画像に収まらない。

手順: ``origin`` と、そこから世界座標の +X / +Y / +Z 方向に ``length`` 進んだ
3 点を射影(``annotate3d_project`` と同じ慣習)し、原点の画素から各軸端の画素へ
``annotate.arrow``(矢じり 8x6 px)を描く。軸端の先 ``0.7 * font_size`` px の
位置に ``labels[i]`` を背景なし(``box_alpha=0``)の文字で置く。

引数:
- ``origin`` ``(3,)``(object 座標)、``length``: 軸の長さ(メッシュ単位、``> 0``)。
- ``labels``: 3 つの文字列(既定 ``("X", "Y", "Z")``)。``colors``: 3 つの色
  (役割名か RGB。既定 ``("wrong", "right", "reference")`` はパレットの役割名)。
- ``width``: 線幅 [px]、1 以上の整数。``font_size`` [px]。
- ``depth`` / ``occlusion_tol``: 射影に渡すが、**この op は隠れ表示(破線)を
  しない**(判定は ``depth`` の形検査に使うだけ)。

返り値: 描画済みの新しい画像(float64 ``[0, 1]``)。

エラーになる条件: ``length <= 0`` / ``labels`` か ``colors`` の長さが 3 でない /
原点または軸端のいずれかが ``z <= 1e-9`` / 姿勢・``K``・``depth`` の不正 / 軸の
文字が画像に収まらない。**枠外の軸端はエラーにしない**(矢印は枠外まで引く)。
視線と一致して点に潰れた軸(画素長 1e-9 未満)は黙ってスキップする。

使いどころ: 図の姿勢の説明(gnomon)。``render3d.look_at`` の ``pose`` を
そのまま渡し、``origin`` にメッシュの重心や ``bounds`` の角を置く。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate3d_figure](../../../../examples_3d/annotate3d_figure.py) — `py -3.11 examples_3d/annotate3d_figure.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`annotate3d`)

[annotate3d_project](annotate3d_project.md) · [annotate3d_arrow](annotate3d_arrow.md) · [annotate3d_label](annotate3d_label.md) · [annotate3d_scale_bar](annotate3d_scale_bar.md) · [annotate3d_bbox](annotate3d_bbox.md) · [annotate3d_measure](annotate3d_measure.md)

---
*Provenance: annotate3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
