---
op: surface_normals
dim: 3d
category: photometric
in: image2d
out: normalmap
examples: [photometric_stereo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# surface_normals — 3D `photometric` op

- **データ種**: `image2d` → `normalmap`
- **呼び出し**: `import photometric; photometric.surface_normals(z)` (または `ops3d.get("surface_normals")`)

## 使い方

高さ場 z(HxW)→ 単位法線 (H,W,3)。n ∝ (-dz/dx, -dz/dy, 1)。深度→法線の順変換。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photometric_stereo](../../../../examples_3d/photometric_stereo.py) — `py -3.11 examples_3d/photometric_stereo.py`

## 型が繋がる次の op(`normalmap` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [render_shaded](../render/render_shaded.md) · [phong_shade](../render/phong_shade.md) · [matcap_shade](../render/matcap_shade.md) · [integrate_normals](integrate_normals.md) · [render_lambertian](render_lambertian.md)

## 同カテゴリ(`photometric`)

[photometric_stereo](photometric_stereo.md) · [integrate_normals](integrate_normals.md) · [render_lambertian](render_lambertian.md)

---
*Provenance: photometric.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
