---
op: annotate3d_arrow
dim: 3d
category: annotate3d
in: image2d
out: image2d
examples: [annotate3d_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# annotate3d_arrow — 3D `annotate3d` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import annotate3d; annotate3d.annotate3d_arrow(img, p0, p1, pose, K, depth=None, color='emphasis', width=2, head_len=12.0, head_width=9.0, occlusion_tol=0.01, scheme='okabe_ito')` (または `ops3d.get("annotate3d_arrow")`)

## 使い方

画像(image2d)を返す: 3-D の ``p0`` から ``p1`` へ、射影した矢印を描く。

``depth`` を渡し**両端とも隠れている**なら破線で描く(矢じりは半透明)。

Raises
------
ValueError
    端点がカメラの後ろ / 一致 / 両端とも画像の外、姿勢・K の不正。

手順: ``img`` を float64 ``[0, 1]`` の複製にし(``(H, W)`` / ``(H, W, C)``、C は
1/3/4。非有限・空は ``ValueError``)、``p0``, ``p1`` を ``annotate3d_project`` と
同じ射影で画素にして、``annotate.arrow`` で ``p0`` の画素から ``p1`` の画素へ
矢印を描く。矢じりは ``p1`` 側。

引数:
- ``p0``, ``p1``: object 座標 ``(3,)``(有限)。``pose`` は 4x4 object→camera か
  ``(R, t)``、``K`` は 3x3(-Z を見る render3d 慣習)。
- ``depth``: ``(H, W)`` 前方距離画像(``render3d.render_mesh`` の ``depth``)。
  画像と同じ形でなければ ``ValueError``。
- ``color``: 役割名(``"emphasis"`` など、``scheme`` のパレットで解決)か RGB。
- ``width``: 線幅 [px]、1 以上の整数(``1.5`` は拒否)。
- ``head_len`` / ``head_width``: 矢じりの長さ・幅 [px]。隠れ描画では矢印長の
  80 % を超えないよう縮める。
- ``occlusion_tol``: ``[0, 1)``。

返り値: 描画済みの新しい画像(float64、入力と同じ形。入力は変更しない)。

エラーになる条件(実装どおり): どちらかの端点が ``z <= 1e-9``(カメラ面上/後ろ)/
2 点が同じ画素に射影される(視線上に並ぶ、長さ 1e-9 px 未満)/ 姿勢・``K`` の不正。
**画像の外に出た端点はエラーにしない**(``annotate.arrow`` が枠外まで線を引く
だけ。片方が枠内なら見た目は途中で切れる)。

使いどころ: ``render3d.render_mesh`` の画像に「この頂点がこれ」を示す。長さを
数値で示すなら ``annotate3d_measure``、文字を添えるなら ``annotate3d_label``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate3d_figure](../../../../examples_3d/annotate3d_figure.py) — `py -3.11 examples_3d/annotate3d_figure.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`annotate3d`)

[annotate3d_project](annotate3d_project.md) · [annotate3d_label](annotate3d_label.md) · [annotate3d_scale_bar](annotate3d_scale_bar.md) · [annotate3d_axes](annotate3d_axes.md) · [annotate3d_bbox](annotate3d_bbox.md) · [annotate3d_measure](annotate3d_measure.md)

---
*Provenance: annotate3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
