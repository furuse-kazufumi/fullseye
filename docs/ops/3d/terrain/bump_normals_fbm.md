---
op: bump_normals_fbm
dim: 3d
category: terrain
in: normalmap × pointmap
out: normalmap
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# bump_normals_fbm — 3D `terrain` op

- **データ種**: `normalmap × pointmap` → `normalmap`
- **呼び出し**: `import render3d; render3d.bump_normals_fbm(normals, positions, wavelengths=(0.002, 0.001), amplitudes=(0.0002, 0.00012), *, seed: 'int' = 0, rotation=None, step=None, local_edge=None, nyquist: 'float' = 2.0, fade: 'float' = 1.0) -> 'np.ndarray'` (または `ops3d.get("bump_normals_fbm")`)

## 使い方

Perturb a normal map with the *gradient* of a seeded multi-octave height field

(sub-facet relief the geometry cannot afford to displace) → unit normals ``(H, W, 3)``.

``h(x) = Σ_k A_k n_k(x)`` is the same value-noise field :func:`mesh_displace_spectrum`
would displace with (same ``seed`` ⇒ same lattice), so passing the octaves that the
displacement's band gate rejected makes the shading continue the *same* amplitude
spectrum below the facet size (no fake sandpaper: an octave of amplitude ``A`` at
wavelength ``λ`` tilts the normal by about ``2πA/λ`` at most). The bumped normal is
``normalize(n − ∇_t h)`` (first-order shading normal of a height field over the
surface; ``∇_t`` = tangential gradient by central differences with ``step`` =
``min(λ)/64``). ``positions`` are world coordinates ``(H, W, 3)`` (NaN = background,
left untouched); if ``rotation`` (3×3, world → normal frame, e.g. ``pose[:3,:3]``)
is given the normals are taken in that frame.

``local_edge`` (optional ``(H, W)`` map of the mesh's local edge length under each
pixel) makes the bump the exact **complement** of the displacement's band gate: octave
``k`` is bumped with weight ``1 − gate_k`` where ``gate_k`` is
:func:`displacement_band_weights`'s rule with the same ``nyquist`` / ``fade`` — so an
octave the geometry carried at a pixel is not added twice, and one it could not carry
is fully supplied by the bump. Without it every octave is bumped at full amplitude.
Deterministic; fail-closed.

入出力はともに ``(H, W, 3)`` 画像。``positions`` に NaN を含む画素、または法線の長さが
``1e-12`` 以下の画素は背景として **元の値のまま** 残す(``render3d.render_mesh`` の空画素)。
有効画素が一つも無ければ入力のコピーを返す。

- ``wavelengths`` / ``amplitudes``: メッシュ(= ``positions``)の単位で同じ長さ(1〜32)の
  正の列。不一致・負は ``ValueError``。
- ``rotation``: 3×3(world → 法線の座標系)。与えると法線を ``N @ R`` で world に戻して
  勾配を取り、``@ R.T`` で元の系に戻す。``render_mesh`` の法線はカメラ空間なので
  ``pose[:3,:3]`` を渡す。非有限・形不正は ``ValueError``。
- ``step``: 中心差分の刻み(既定 ``min(wavelengths)/64``)。0 以下は ``ValueError``。
- ``local_edge``: ``(H, W)`` の辺長マップ。形が法線と違う、または有効画素の下に非正・
  非有限があると ``ValueError``。

高さ場を 3 軸の中心差分で微分するので評価は 1 画素あたり 6 回。法線の傾きは
``max |∇h| ≈ 2π A_k / λ_k`` 程度なので、振幅が波長に近づくほど法線が大きく寝る
(既定は A/λ = 0.1 前後)。結果は ``phong_shade`` / ``brdf_hapke`` 等の
法線マップ入力へそのまま渡せる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_regolith_hero](../../../../examples_3d/itokawa_regolith_hero.py) — `py -3.11 examples_3d/itokawa_regolith_hero.py`

## 型が繋がる次の op(`normalmap` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [render_shaded](../render/render_shaded.md) · [phong_shade](../render/phong_shade.md) · [matcap_shade](../render/matcap_shade.md) · [brdf_lommel_seeliger](../render/brdf_lommel_seeliger.md) · [brdf_hapke](../render/brdf_hapke.md) · [integrate_normals](../photometric/integrate_normals.md) · [render_lambertian](../photometric/render_lambertian.md)

## 同カテゴリ(`terrain`)

[mesh_displace_fbm](mesh_displace_fbm.md) · [terrain_region_mask](terrain_region_mask.md) · [mesh_scatter_boulders](mesh_scatter_boulders.md) · [mesh_edge_lengths](mesh_edge_lengths.md) · [mesh_subdivide](mesh_subdivide.md) · [displacement_band_weights](displacement_band_weights.md) · [mesh_displace_spectrum](mesh_displace_spectrum.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
