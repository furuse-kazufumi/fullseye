---
op: bump_normals_fbm
dim: 3d
category: terrain
in: normalmap × pointmap
out: normalmap
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# bump_normals_fbm — 3D `terrain` op

- **データ種**: `normalmap × pointmap` → `normalmap`
- **呼び出し**: `import render3d; render3d.bump_normals_fbm(normals, positions, wavelengths=(0.002, 0.001), amplitudes=(0.0002, 0.00012), *, seed: 'int' = 0, rotation=None, step=None, local_edge=None, nyquist: 'float' = 2.0, fade: 'float' = 1.0) -> 'np.ndarray'` (または `ops3d.get("bump_normals_fbm")`)

## 使い方

Perturb a normal map with the *gradient* of a seeded multi-octave height field

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`normalmap` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [render_shaded](../render/render_shaded.md) · [phong_shade](../render/phong_shade.md) · [matcap_shade](../render/matcap_shade.md) · [brdf_lommel_seeliger](../render/brdf_lommel_seeliger.md) · [brdf_hapke](../render/brdf_hapke.md) · [integrate_normals](../photometric/integrate_normals.md) · [render_lambertian](../photometric/render_lambertian.md)

## 同カテゴリ(`terrain`)

[mesh_displace_fbm](mesh_displace_fbm.md) · [terrain_region_mask](terrain_region_mask.md) · [mesh_scatter_boulders](mesh_scatter_boulders.md) · [mesh_edge_lengths](mesh_edge_lengths.md) · [mesh_subdivide](mesh_subdivide.md) · [displacement_band_weights](displacement_band_weights.md) · [mesh_displace_spectrum](mesh_displace_spectrum.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
