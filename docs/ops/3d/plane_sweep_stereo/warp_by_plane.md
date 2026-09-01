---
op: warp_by_plane
dim: 3d
category: plane_sweep_stereo
in: image2d
out: image2d
examples: [motion_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# warp_by_plane — 3D `plane_sweep_stereo` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import plane_sweep; plane_sweep.warp_by_plane(img: 'np.ndarray', H: 'np.ndarray', order: 'int' = 1, cval: 'float' = nan) -> 'np.ndarray'` (または `ops3d.get("warp_by_plane")`)

## 使い方

homography H で img を逆ワープ。→ out[y,x] = img(H·(x,y,1))(bilinear)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_scene](../../../../examples_3d/motion_scene.py) — `py -3.11 examples_3d/motion_scene.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`plane_sweep_stereo`)

[plane_sweep_depth](plane_sweep_depth.md)

---
*Provenance: plane_sweep.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
