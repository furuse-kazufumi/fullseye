---
op: polar_unwrap
dim: 3d
category: curvilinear
in: image2d
out: image2d
gpu: true
examples: [curvilinear_proj]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# polar_unwrap — 3D `curvilinear` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import match3d; match3d.polar_unwrap(image, center=None, r_in=0.0, r_out=None, ntheta=360, nr=64, device='cpu')` (または `ops3d.get("polar_unwrap")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

画像の円環/円板を (θ×r) 矩形へアンラップ(工業: ラベル/リング/回転体の検査)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [curvilinear_proj](../../../../examples_3d/curvilinear_proj.py) — `py -3.11 examples_3d/curvilinear_proj.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [fit_zernike](fit_zernike.md) · [matcap_shade](../render/matcap_shade.md) · [antialias](../render/antialias.md) · [edge_alias_energy](../render/edge_alias_energy.md)

## 同カテゴリ(`curvilinear`)

[cylinder_unwrap](cylinder_unwrap.md) · [fit_zernike](fit_zernike.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
