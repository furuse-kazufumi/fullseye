---
op: render_volume_projection
dim: 3d
category: render
in: voxel
out: image2d
gpu: true
examples: [ct_hand_radiograph]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# render_volume_projection — 3D `render` op

- **データ種**: `voxel` → `image2d`
- **呼び出し**: `import match3d; match3d.render_volume_projection(vol, azimuth=0.0, elevation=0.0, mode='xray', device='cpu')` (または `ops3d.get("render_volume_projection")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

voxel を任意視点で 2D 投影(mode=xray=減衰積算 / mip=最大値)。DRR(X線)・世界モデル観測。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_hand_radiograph](../../../../examples_3d/ct_hand_radiograph.py) — `py -3.11 examples_3d/ct_hand_radiograph.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](matcap_shade.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md) · [supersample_mesh](supersample_mesh.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
