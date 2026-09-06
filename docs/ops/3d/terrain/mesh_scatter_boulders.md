---
op: mesh_scatter_boulders
dim: 3d
category: terrain
in: mesh
out: mesh
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# mesh_scatter_boulders — 3D `terrain` op

- **データ種**: `mesh` → `mesh`
- **呼び出し**: `import render3d; render3d.mesh_scatter_boulders(V, F, *, density: 'float', d_min: 'float', d_max=None, exponent: 'float' = 3.1, seed: 'int' = 0, region_weights=None, aspect=(1.0, 0.7, 0.5), embed: 'float' = 0.35, subdiv: 'int' = 1, shape: 'str' = 'ellipsoid', orientation: 'str' = 'normal', burial=(0.3, 0.6), max_count=None, hull_points=None, return_info: 'bool' = False)` (または `ops3d.get("mesh_scatter_boulders")`)

## 使い方

Scatter partly-buried boulders on a mesh (power-law sizes, seeded) → ``(V, F)``

(or ``(V, F, info)`` with ``return_info=True``).

``shape='ellipsoid'`` (default, unchanged behaviour): icosphere ellipsoids with semi-axes
``D/2 × aspect`` (1 : 0.7 : 0.5, shortest axis along the local surface normal), spun about
the normal and sunk by ``embed`` (0 = resting, 1 = centre on the surface).
``shape='hull'``: **angular blocks** — the convex hull of seeded random points on an
ellipsoid of the same aspect with 20 % radial jitter (flat facets, sharp edges, the
look of Itokawa's boulders), ``hull_points`` per block (default size-dependent:
``10 + 8·log2(D/d_min)``, 10..40). ``orientation='random'`` gives each block a uniform
random rotation instead of aligning its short axis with the normal. For hulls the sink
is the size-dependent ``burial`` fraction from :func:`sample_boulders` (30–60 % of the
block's height below the surface by default; ``embed`` is ignored). ``max_count`` caps
the expected number by raising ``d_min`` along the same law (see
:func:`sample_boulders`; ``info['d_min_effective']`` reports it).

Placement and sizes come from :func:`sample_boulders` (Poisson process,
N(>D) ∝ D^-exponent); boulders sit on the mesh *as passed* — pass the displaced /
subdivided terrain so they rest on the final surface. ``region_weights`` from
:func:`terrain_region_mask` keeps the seas smooth. The boulders are appended as real
geometry, so they self-shadow, cast shadows and occlude through the same rasteriser /
ray-cast path as the terrain. ``info`` = the sample dict plus ``faces_per_boulder``
and ``n_boulders``. Deterministic under ``seed``. Fail-closed.

手順: :func:`sample_boulders` で位置(面上の一様点)・面法線・直径 ``D`` を引き、岩ごとに
小さなメッシュを作って入力メッシュの後ろに連結する(頂点は末尾に追加、面 index は
オフセット済み)。入力の頂点・面はそのまま残るので、``info['faces_per_boulder']`` と
元の面数から岩の面だけを切り出せる。

- ``density``: 単位面積(メッシュ単位²)あたりの ``D ≥ d_min`` の岩の期待個数。
  実個数はポアソン分布で決まり 0 個もあり得る(そのときは入力のコピーを返す)。
- ``d_min`` < ``d_max``(``None`` = 10·d_min)、``exponent`` > 0、``aspect`` は正の 3 要素、
  ``embed`` ∈ [0, 1]、``subdiv`` ∈ [0, 3] (楕円体の icosphere 細分)、``hull_points`` は
  [6, 200]。いずれも範囲外は ``ValueError``。
- ``shape='ellipsoid'``: 半軸 ``D/2·aspect`` の楕円体を最短軸が法線に沿う向きで置き、
  中心を法線方向に ``semi_z·(1 − embed)`` 浮かせる。
- ``shape='hull'``: 楕円体上の乱数点の凸包。法線方向の高さ範囲のうち ``burial``
  (0.3〜0.6 既定、小さい岩ほど深い)の割合が面の下に沈む。``embed`` は無視。
- ``orientation='random'`` は一様ランダム回転(4 元数)。``'normal'`` は法線まわりに
  ランダム回転。回転の乱数は ``seed + 1`` の generator を使う。

岩は実ジオメトリなので ``ambient_occlusion`` / ``cast_shadow`` / ``shadow_raycast`` の
レイに普通に当たる。置く面は渡したメッシュそのものなので、``mesh_displace_spectrum`` や
``mesh_subdivide`` の **後** に呼ぶこと(先に呼ぶと岩が地面から浮く/埋まる)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_regolith_hero](../../../../examples_3d/itokawa_regolith_hero.py) — `py -3.11 examples_3d/itokawa_regolith_hero.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`terrain`)

[mesh_displace_fbm](mesh_displace_fbm.md) · [terrain_region_mask](terrain_region_mask.md) · [mesh_edge_lengths](mesh_edge_lengths.md) · [mesh_subdivide](mesh_subdivide.md) · [displacement_band_weights](displacement_band_weights.md) · [mesh_displace_spectrum](mesh_displace_spectrum.md) · [bump_normals_fbm](bump_normals_fbm.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
