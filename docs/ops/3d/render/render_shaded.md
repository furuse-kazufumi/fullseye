---
op: render_shaded
dim: 3d
category: render
in: normalmap
out: image2d
examples: [render_ao]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# render_shaded — 3D `render` op

- **データ種**: `normalmap` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.render_shaded(normals_img, light=(0, 0, 1), ambient=0.1)` (実装を直接呼ぶなら `import match3d; match3d.render_shaded(normals_img, light=(0, 0, 1), ambient=0.1)`、台帳から引くなら `ops3d.get("render_shaded")`)

## 使い方

法線マップ (H,W,3) + 光源方向 → Lambertian 陰影画像(外観サンプル生成、光学と接続)。

``I = ambient + (1 − ambient)·clip(n·L̂, 0, 1)`` を ``(H, W)`` float64、値域 **[0, 1]** で返す。
``light`` は内部で単位化する(零ベクトルは 0 除算で NaN)が、**法線は単位化しない**(単位法線を
渡す。``estimate_point_normals`` / ``normals_from_depth`` の出力は単位)。法線の成分順と
``light`` の成分順は揃える(既定 ``(0,0,1)`` は第 3 成分=カメラ向きを正面光とする規約)。
光源と反対を向く面は ``ambient`` の値になる。最後の軸を法線とみなすので ``(N,3)`` の点ごとの
法線でも動く。鏡面ハイライトは無い(``fresnel_reflectance`` / ``reflect`` で別途)。
用途: ``photometric_stereo`` の検算(法線 → 画像の順方向)、外観検査の合成サンプル。

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

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md) · [supersample_mesh](supersample_mesh.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
