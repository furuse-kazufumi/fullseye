---
op: annotate3d_label
dim: 3d
category: annotate3d
in: image2d × text
out: image2d
examples: [annotate3d_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# annotate3d_label — 3D `annotate3d` op

- **データ種**: `image2d × text` → `image2d`
- **呼び出し**: `import annotate3d; annotate3d.annotate3d_label(img, text, anchor, pose, K, depth=None, offset=(26.0, -22.0), color='emphasis', width=1.5, cap_size=3.0, font_size=12, pad=4, box_alpha=0.72, text_color=None, occlusion_tol=0.01, scheme='okabe_ito', font_path=None)` (または `ops3d.get("annotate3d_label")`)

## 使い方

画像(image2d)を返す: 3-D のアンカーに引き出し線つきの文字を付ける。

文字はアンカーの画素から ``offset`` [px] ずらした位置(``offset[0]`` の符号で
左右のアンカーを選ぶ)。``depth`` で隠れていると分かれば**破線 + 白抜きの印**。

Raises
------
ValueError
    アンカーがカメラの後ろ / 画像の外、文字が収まらない、姿勢・K の不正。

手順: ``anchor``(object 座標 ``(3,)``)を ``annotate3d_project`` と同じ射影で
画素 ``(x, y)`` にし、``(x, y)`` から ``(x + offset[0], y + offset[1])`` へ
引き出し線(``annotate._aa_polyline``、幅 ``width``)を引き、アンカー側に半径
``cap_size`` の点を打ち、線の先に ``annotate.text_box`` で文字を置く。
文字箱の付け根(anchor)は ``offset[0] > 0`` なら左中、``< 0`` なら右中、
``== 0`` なら ``offset[1] < 0`` で下中央・それ以外で上中央。

引数:
- ``offset``: 画素単位 ``(dx, dy)``(``dy`` は下向き正 = 行方向)。既定
  ``(26, -22)`` は右上へ。
- ``width``: 線幅 [px]、``>= 0.5`` の実数。``cap_size``: 点の半径 [px]、0 で
  打たない。``pad`` / ``font_size`` / ``box_alpha`` / ``text_color`` /
  ``font_path``: 文字箱の見た目(``font_size`` 未満 9 までは自動縮小)。
- ``depth``: 前方距離画像。隠れていれば線を破線、点を白抜き(ring)にする。
- ``color``: 役割名か RGB。``occlusion_tol``: ``[0, 1)``。

返り値: 描画済みの新しい画像(float64 ``[0, 1]``、入力は変更しない)。

エラーになる条件(実装どおり): アンカーが ``z <= 1e-9`` / アンカーの画素が
``[0, W-1] x [0, H-1]`` の外 / 姿勢・``K``・``depth`` の不正 / 文字箱が縮小しても
画像に収まらない(``text_box`` 側)。``offset`` の先が枠外でも線は引く。

使いどころ: 図中の部位名・番号付け。複数の点を一括でラベル付けするときは
``annotate3d_project`` で可視判定を先に取り、``visible`` の点だけ呼ぶ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate3d_figure](../../../../examples_3d/annotate3d_figure.py) — `py -3.11 examples_3d/annotate3d_figure.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`annotate3d`)

[annotate3d_project](annotate3d_project.md) · [annotate3d_arrow](annotate3d_arrow.md) · [annotate3d_scale_bar](annotate3d_scale_bar.md) · [annotate3d_axes](annotate3d_axes.md) · [annotate3d_bbox](annotate3d_bbox.md) · [annotate3d_measure](annotate3d_measure.md)

---
*Provenance: annotate3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
