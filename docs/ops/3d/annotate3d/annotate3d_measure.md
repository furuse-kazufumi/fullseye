---
op: annotate3d_measure
dim: 3d
category: annotate3d
in: image2d
out: image2d
examples: [annotate3d_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# annotate3d_measure — 3D `annotate3d` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.annotate3d_measure(img, p0, p1, pose, K, unit='', depth=None, color='emphasis', width=1.5, tick=8.0, font_size=12, label_fmt='{:.3g}', box_alpha=0.6, text_color=None, occlusion_tol=0.01, scheme='okabe_ito', font_path=None)` (実装を直接呼ぶなら `import annotate3d; annotate3d.annotate3d_measure(img, p0, p1, pose, K, unit='', depth=None, color='emphasis', width=1.5, tick=8.0, font_size=12, label_fmt='{:.3g}', box_alpha=0.6, text_color=None, occlusion_tol=0.01, scheme='okabe_ito', font_path=None)`、台帳から引くなら `ops3d.get("annotate3d_measure")`)

## 使い方

画像(image2d)を返す: 3-D の 2 点間距離(メッシュ単位)を、射影した線と値で示す。

値は ``|p1 - p0|``(3-D、閉形式)。画素上の長さは短縮しても値は変わらない。

Raises
------
ValueError
    2 点が一致、端点がカメラの後ろ / 画像の外。

手順: ``dist = |p1 - p0|``(object 座標のユークリッド距離、単位はメッシュ単位)を
計算し、``p0``, ``p1`` を射影(``annotate3d_project`` と同じ慣習)。両端の画素を
結ぶ線と両端の垂直な目盛(長さ ``tick`` px)、両端に半径 3 px の点を描き、線の
中点から画面上側へ ``tick/2 + 4`` px 離した位置に
``label_fmt.format(dist) + " " + unit`` の文字箱を置く。

引数:
- ``p0``, ``p1``: object 座標 ``(3,)``(有限、一致は拒否)。
- ``unit``: 文字列(空なら数値だけ)。``label_fmt``: ``str.format`` 書式(既定
  ``"{:.3g}"``)。単位換算はしない — メッシュが mm ならそのまま mm。
- ``width`` [px] ``>= 0.5``、``tick`` [px] ``>= 0``、``font_size`` / ``box_alpha`` /
  ``text_color`` / ``font_path``: 文字箱の見た目。
- ``depth``: 前方距離画像。両端とも隠れていれば線を破線に、隠れた端点の点を
  白抜き(ring)にする。``occlusion_tol``: ``[0, 1)``。

返り値: 描画済みの新しい画像(float64 ``[0, 1]``)。

エラーになる条件: ``|p1 - p0| < 1e-12`` / どちらかの端点が ``z <= 1e-9`` /
**どちらかの端点が画像の外**(``in_image`` を両端に要求) / 姿勢・``K``・
``depth`` の不正 / 文字箱が収まらない。

使いどころ: ``fit_sphere3`` の直径、``smallest_box3`` の辺、2 つの特徴点間の
距離を図の上に示す。値そのものは描画前に ``np.linalg.norm(p1 - p0)`` と同じ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate3d_figure](../../../../examples_3d/annotate3d_figure.py) — `py -3.11 examples_3d/annotate3d_figure.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`annotate3d`)

[annotate3d_project](annotate3d_project.md) · [annotate3d_arrow](annotate3d_arrow.md) · [annotate3d_label](annotate3d_label.md) · [annotate3d_scale_bar](annotate3d_scale_bar.md) · [annotate3d_axes](annotate3d_axes.md) · [annotate3d_bbox](annotate3d_bbox.md)

---
*Provenance: annotate3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
