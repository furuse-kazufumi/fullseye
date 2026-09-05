---
op: render_regolith
dim: 3d
category: render
in: mesh
out: rgbimage
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# render_regolith — 3D `render` op

- **データ種**: `mesh` → `rgbimage`
- **呼び出し**: `import render_beauty; render_beauty.render_regolith(V, F, *, pose=None, intrinsics=None, size: 'int' = 512, ss: 'int' = 2, sun: 'Sequence[float]' = (0.3, 0.4, 1.0), w: 'float' = 0.42, g: 'float' = -0.35, B0: 'float' = 0.87, h: 'float' = 0.01, roughness_deg: 'float' = 26.0, sun_angular_diameter_deg: 'float' = 0.53, shadow_samples: 'int' = 4, ao_samples: 'int' = 32, tint: 'Sequence[float]' = (1.0, 0.97, 0.93), self_illumination: 'float' = 1.0, exposure='auto', albedo_variation: 'float' = 0.12, seed: 'int' = 0, smooth_normals: 'bool' = True, background: 'Sequence[float]' = (0.0, 0.0, 0.0), bump=None, vertex_normals=None, vertex_albedo=None, exposure_target: 'float' = 0.45) -> 'np.ndarray'` (または `ops3d.get("render_regolith")`)

## 使い方

小惑星のレゴリスを物理ベース(Hapke + 太陽視直径のレイキャスト影 + 環境光ゼロ)で描く → RGB ``(size,size,3)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_regolith_hero](../../../../examples_3d/itokawa_regolith_hero.py) — `py -3.11 examples_3d/itokawa_regolith_hero.py`

## 型が繋がる次の op(`rgbimage` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md)

---
*Provenance: render_beauty.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
