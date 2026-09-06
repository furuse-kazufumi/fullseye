---
op: mesh_displace_fbm
dim: 3d
category: terrain
in: mesh
out: mesh
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# mesh_displace_fbm — 3D `terrain` op

- **データ種**: `mesh` → `mesh`
- **呼び出し**: `import render3d; render3d.mesh_displace_fbm(V, F, amplitude: 'float', *, scale=None, octaves: 'int' = 4, lacunarity: 'float' = 2.0, gain: 'float' = 0.5, seed: 'int' = 0)` (または `ops3d.get("mesh_displace_fbm")`)

## 使い方

Roughen a mesh by displacing vertices along their normals with seeded fBm noise → ``(V, F)``.

``amplitude`` is the peak displacement **in the mesh's own units** (the Itokawa STL is in
km, so 0.003 = 3 m); every vertex moves by at most ``amplitude`` (|fBm| ≤ 1, asserted by
tests). ``scale`` is the base wavelength (default = bounding-box diagonal / 12);
``octaves``/``lacunarity``/``gain`` shape the spectrum (multifractal ridges come from the
default 4 octaves). Deterministic for a given ``seed``; ``amplitude=0`` returns the input
unchanged. Face normals of the displaced mesh carry the matching shading perturbation
(no separate bump map is faked). Fail-closed on degenerate meshes / non-finite arguments.

各頂点 ``x_i`` を面積重み付き頂点法線 ``n_i`` に沿って ``x_i + amplitude · fBm(x_i) · n_i``
へ動かす。``fBm`` は :func:`fbm_noise`(seed 固定の格子 value noise、``octaves`` 段を
``lacunarity`` 倍の周波数・``gain`` 倍の振幅で重ね、振幅和で割って ``[-1, 1]``)。
面配列 ``F`` は変えず、返り値は ``(V' (N,3) float64, F のコピー)``。

- ``amplitude``: メッシュ単位の最大変位(0 以上)。負・非有限は ``ValueError``、0 なら
  入力のコピーをそのまま返す(ノイズ計算をしない)。
- ``scale``: ノイズの基本波長(メッシュ単位)。``None`` = 境界箱対角 / 12。0 以下は
  ``ValueError``。
- ``octaves`` ∈ [1, 16]、``lacunarity`` > 0、``gain`` ∈ (0, 1] の範囲外は ``ValueError``。
- 法線は面の巻き順から作るので外向きに一貫したメッシュを仮定する。面積ゼロで法線が
  決まらない頂点は +Z へ動く(``_vertex_normals`` の代替値)。

波長ごとに振幅を指定したい・粗いメッシュで折り返しを避けたい場合は
``mesh_displace_spectrum``(帯域制限あり)を使う。粗さを幾何に入れず陰影だけに載せるなら
``bump_normals_fbm``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_regolith_hero](../../../../examples_3d/itokawa_regolith_hero.py) — `py -3.11 examples_3d/itokawa_regolith_hero.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`terrain`)

[terrain_region_mask](terrain_region_mask.md) · [mesh_scatter_boulders](mesh_scatter_boulders.md) · [mesh_edge_lengths](mesh_edge_lengths.md) · [mesh_subdivide](mesh_subdivide.md) · [displacement_band_weights](displacement_band_weights.md) · [mesh_displace_spectrum](mesh_displace_spectrum.md) · [bump_normals_fbm](bump_normals_fbm.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
