---
op: cast_shadow
dim: 3d
category: render
in: mesh × vector
out: image2d
examples: [render_beauty, render_shadow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# cast_shadow — 3D `render` op

- **データ種**: `mesh × vector` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.cast_shadow(V, F, light, *, pose=None, intrinsics=None, width: 'int' = 256, height: 'int' = 256, directional: 'bool' = True, penumbra: 'float' = 0.0, samples: 'int' = 16, shadow_res: 'int' = 512, bias=None, pcf: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import render_shadow; render_shadow.cast_shadow(V, F, light, *, pose=None, intrinsics=None, width: 'int' = 256, height: 'int' = 256, directional: 'bool' = True, penumbra: 'float' = 0.0, samples: 'int' = 16, shadow_res: 'int' = 512, bias=None, pcf: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("cast_shadow")`)

## 使い方

メッシュのキャスト影 / ソフトシャドウを計算し、可視性マップ (H,W) ∈ [0,1] を返す。

``1=完全に照らされる`` / ``0=完全な影``。受光面が無い背景画素は ``1.0``。

引数:
  * ``V, F``        頂点 (N,3) と三角形 (M,3)。空メッシュは影を落とせないので拒否。
  * ``light``       (3,) ベクトル。``directional=True`` なら平行光の方向(シーン→光源)、
                    ``False`` なら点光源のワールド位置。
  * ``pose``/``intrinsics`` カメラ。省略時は ``render3d.auto_view`` で補完。
  * ``penumbra``    面光源の**角半径(度)**。0 でハード影、増やすほど半影が広がる。
  * ``samples``     半影サンプル数(``penumbra>0`` のときのみ使用、Fibonacci ディスク)。
  * ``shadow_res``  shadow map の一辺解像度。
  * ``bias``        影判定の深度バイアス(ワールド単位)。``None`` なら texel サイズと
                    傾斜から自動設定(acne / peter-panning を抑制)。
  * ``pcf``         shadow map を引くときに混ぜる近傍の**半径 [texel]**。
                    ``0``(既定)は最近傍 1 点 = 従来どおり。``1`` なら 3x3 の
                    **判定を平均**する(深度を平均するのではない —— 深度の平均は
                    手前と奥をならして存在しない面を作る)。境目が texel に
                    量子化されて階段になるのを、shadow map を上げずに緩和する。

手法は shadow mapping(Williams 1978): 光源から ``render_mesh`` で深度を取り、カメラ側の
受光面点を光源空間へ射影して深度比較する。fail-closed: 退化メッシュ・不正光源・非正の
サイズ/解像度は ``ValueError``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [render_beauty](../../../../examples_3d/render_beauty.py) — `py -3.11 examples_3d/render_beauty.py`
- [render_shadow](../../../../examples_3d/render_shadow.py) — `py -3.11 examples_3d/render_shadow.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](matcap_shade.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md) · [supersample_mesh](supersample_mesh.md)

---
*Provenance: render_shadow.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
