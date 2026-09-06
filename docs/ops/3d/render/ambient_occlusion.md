---
op: ambient_occlusion
dim: 3d
category: render
in: mesh
out: image2d
examples: [render_ao]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# ambient_occlusion — 3D `render` op

- **データ種**: `mesh` → `image2d`
- **呼び出し**: `import render_ao; render_ao.ambient_occlusion(V, F, pose=None, intrinsics=None, width: 'int' = 256, height: 'int' = 256, n_dirs: 'int' = 64, max_dist: 'float | None' = None, k: 'int' = 3, background: 'float' = 1.0, method: 'str' = 'auto') -> 'np.ndarray'` (または `ops3d.get("ambient_occlusion")`)

## 使い方

メッシュを AO マップ画像 ``(H, W)`` [0,1] にレンダリングして返す。

``render3d.render_mesh`` で depth / silhouette / **三角形 id と透視補正重心座標** を得て
(ラスタライズと隠面消去はそれに任せ、再発明しない)、物体空間 :func:`vertex_occlusion` の
頂点 AO を**その画素を覆っている三角形の 3 頂点から重心補間**して焼き込む。物体の外
(silhouette=0)は ``background``(既定 1.0=完全露出)。*pose* / *intrinsics* 省略時は
``render3d.auto_view`` が枠取りする。fail-closed 検証は下位関数に従う。

``k`` は **2026-09-02 以降使われない**(後方互換のために残してある)。それまでは
カメラ空間で最近傍 ``k`` 頂点を引いて逆距離重みで混ぜていたが、頂点が粗い面では
多角形のセルになり、記事の hero 画像の地面にまだら模様として出ていた。重心補間は
三角形の中で厳密な線形補間なので頂点密度に依らず連続で、隣接する別の物体の頂点を
拾ってしまうこともない。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [render_ao](../../../../examples_3d/render_ao.py) — `py -3.11 examples_3d/render_ao.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](matcap_shade.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md) · [supersample_mesh](supersample_mesh.md)

---
*Provenance: render_ao.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
