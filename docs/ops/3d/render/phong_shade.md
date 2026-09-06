---
op: phong_shade
dim: 3d
category: render
in: normalmap
out: image2d
examples: [render_beauty, render_shade]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# phong_shade — 3D `render` op

- **データ種**: `normalmap` → `image2d`
- **呼び出し**: `import render_shade; render_shade.phong_shade(normals, view=(0.0, 0.0, 1.0), light=(0.0, 0.0, 1.0), ambient: 'float' = 0.1, diffuse: 'float' = 0.8, specular: 'float' = 0.5, shininess: 'float' = 32.0, clip: 'bool' = True) -> 'np.ndarray'` (または `ops3d.get("phong_shade")`)

## 使い方

Phong 反射モデルで法線マップを陰影付け(環境光 + 拡散 + **鏡面**)。→ ``(H, W)``。

各前景画素で単位法線 ``N`` に対し、光源方向 ``L`` を ``N`` で鏡面反射した理想反射方向
``R = 2(N·L)N − L`` を求め、視線 ``V`` との一致で鏡面項を作る::

    I = ambient + diffuse * max(N·L, 0) + specular * max(R·V, 0)^shininess

鏡面項は光の当たる面(``N·L > 0``)にのみ乗る。``render_lambertian`` に鏡面ローブを
足したもので、ハイライトのピークは拡散最大(``N=L``)ではなく **半角方向**
``N = normalize(L+V)`` に立つ(このとき ``R=V`` で ``R·V=1``)。

背景(長さ 0 の法線 = ``render3d.render_mesh`` の空画素)は 0。``clip=True`` で出力を
``[0, 1]`` にクリップ(表示向き)、``clip=False`` で生の加算強度を返す(``argmax`` で
ハイライト位置を厳密に取りたいときはこちら — 飽和で頂点が同点にならない)。

引数:
  * ``normals``  : float ``(H, W, 3)`` 法線マップ(視空間、視点向き。長さ 0 = 背景)。
  * ``view``     : 面→視点の方向(既定 ``(0,0,1)`` = ``render3d`` の視点)。
  * ``light``    : 面→光源の方向。
  * ``ambient/diffuse/specular`` : 各項の係数(有限・非負)。
  * ``shininess``: 鏡面ローブの鋭さ(> 0。大きいほど鋭い/小さいほど広い)。
  * ``clip``     : ``[0,1]`` にクリップするか。

fail-closed: 形状不正・非有限・ゼロ長方向・非正の ``shininess``・負係数は ``ValueError``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [render_beauty](../../../../examples_3d/render_beauty.py) — `py -3.11 examples_3d/render_beauty.py`
- [render_shade](../../../../examples_3d/render_shade.py) — `py -3.11 examples_3d/render_shade.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](matcap_shade.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [matcap_shade](matcap_shade.md) · [supersample_mesh](supersample_mesh.md)

---
*Provenance: render_shade.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
