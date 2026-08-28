---
op: edge_alias_energy
dim: 3d
category: render
in: image2d
out: measurement
examples: [render_beauty, render_ssaa]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# edge_alias_energy — 3D `render` op

- **データ種**: `image2d` → `measurement`
- **呼び出し**: `import render_ssaa; render_ssaa.edge_alias_energy(img) -> 'float'` (または `ops3d.get("edge_alias_energy")`)

## 使い方

エッジのエイリアス(ジャギー)エネルギー = ラプラシアンの RMS(小さいほど滑らか)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [render_beauty](../../../../examples_3d/render_beauty.py) — `py -3.11 examples_3d/render_beauty.py`
- [render_ssaa](../../../../examples_3d/render_ssaa.py) — `py -3.11 examples_3d/render_ssaa.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md)

---
*Provenance: render_ssaa.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
