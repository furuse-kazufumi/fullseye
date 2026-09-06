---
op: supersample_mesh
dim: 3d
category: render
in: mesh
out: image2d
examples: [render_ssaa]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# supersample_mesh — 3D `render` op

- **データ種**: `mesh` → `image2d`
- **呼び出し**: `import render_ssaa; render_ssaa.supersample_mesh(V, F, pose=None, intrinsics=None, size=256, ss: 'int' = 3, light=(0.0, 0.0, 1.0), ambient: 'float' = 0.1, shade: 'Optional[Callable[[dict], np.ndarray]]' = None, filter: 'str' = 'box') -> 'np.ndarray'` (または `ops3d.get("supersample_mesh")`)

## 使い方

メッシュを SSAA でアンチエイリアス描画 -> float 画像 ``(H, W)`` (or ``(H, W, C)``)。

``render_mesh`` を **目標サイズの ``ss`` 倍**で呼び、陰影を付けてから ``ss×ss`` 面積平均で
目標 ``size`` へ縮小する。``ss=1`` は縮小なし = ``render_mesh`` 生の(エイリアスありの)
ベースライン。

*pose* は 4x4 object->camera 行列(解像度非依存、そのまま使う)。*intrinsics* ``K`` は
**目標 ``size`` 用**の 3x3 ピンホール行列で、高解像レンダリングのため内部で ``fx, fy,
cx, cy`` を ``ss`` 倍にスケールする(出力は目標 ``size`` なので K の意味は目標基準)。
どちらも ``None`` なら ``render_mesh`` が ``auto_view`` で自動フレーミングする(``auto_view``
のフレーミングは解像度不変なので ``ss`` を変えても構図は同じ)。

*shade* は ``shade(view_dict) -> (H*ss, W*ss[, C])`` の callable で、高解像 ``render_mesh``
出力(``depth`` / ``silhouette`` / ``normals``)を陰影画像へ写す。``None`` のとき既定の
Lambertian(*light* をカメラ空間の光源, *ambient* を環境光として法線から陰影, 背景 0)。
*filter* は縮小重み(``"box"`` / ``"gauss"``, :func:`antialias` 参照)。

Fail-closed: ``ss`` は 1 以上の整数、``size`` は正、``size*ss`` の総画素は
``render3d.MAX_PIXELS`` 以下。メッシュ・カメラの妥当性は ``render_mesh`` が検査する。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [render_ssaa](../../../../examples_3d/render_ssaa.py) — `py -3.11 examples_3d/render_ssaa.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](matcap_shade.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md)

---
*Provenance: render_ssaa.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
