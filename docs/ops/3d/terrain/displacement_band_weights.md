---
op: displacement_band_weights
dim: 3d
category: terrain
in: mesh
out: matrix
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# displacement_band_weights — 3D `terrain` op

- **データ種**: `mesh` → `matrix`
- **呼び出し**: `import render3d; render3d.displacement_band_weights(V, F, wavelengths=(0.06, 0.03, 0.015, 0.0075, 0.00375), *, nyquist: 'float' = 2.0, fade: 'float' = 1.0, local_edge=None) -> 'np.ndarray'` (または `ops3d.get("displacement_band_weights")`)

## 使い方

Per-octave, per-vertex band gate ``(K, N)`` in [0,1]: 1 where the mesh can carry the

wavelength as geometry, 0 where it would alias.

A vertex with local edge length ``e`` (mean incident edge, :func:`mesh_edge_lengths`,
or ``local_edge`` (N,) if given) carries wavelength ``λ`` only when ``λ ≥ nyquist·e``;
the gate rises linearly from 0 at ``λ = nyquist·e`` to 1 at ``λ = (nyquist+fade)·e``
(``fade=0`` → hard cut). Used two ways by the Itokawa pipeline: (i) on the *rendered*
mesh to decide which octaves may be displaced (the rest go to bump normals); (ii) on
the *source* model to measure which wavelengths the real data already carries — the
complement ``1 − gate`` is the synthetic-relief weight (0 where the data are fine,
1 where they are coarse), so dense regions are not double-textured. Deterministic.

計算は ``ratio = λ_k / e_i`` に対し、``fade == 0`` なら ``gate = (ratio ≥ nyquist)`` の
二値、それ以外は ``gate = clip((ratio − nyquist) / fade, 0, 1)``。返り値は float64
``(K, N)``(K = 波長数、N = 頂点数)。

- ``wavelengths``: メッシュ単位の波長列(空・非正・非有限は ``ValueError``)。
  ``mesh_displace_spectrum`` と同じ列を渡す。
- ``nyquist``: 「幾何として担える」と見なす波長/辺長比の下限(既定 2 = 1 波長に
  2 辺)。0 以下は ``ValueError``。
- ``fade``: 遷移幅(辺長の倍数)。0 で硬い閾値。負は ``ValueError``。
- ``local_edge``: 頂点ごとの辺長 ``(N,)`` を自分で与える場合(``mesh_edge_lengths`` の
  ``per='vertex'`` 相当)。長さ不一致・非正・非有限は ``ValueError``。``None`` なら
  内部で :func:`mesh_edge_lengths` を呼ぶ。

``mesh_displace_spectrum`` は内部でこの関数を呼ぶので、通常は直接呼ぶ必要はない。直接
使うのは、元データが既に担っている波長を測って ``1 − gate`` を ``weights`` として渡す
(細かい所に合成起伏を二重に載せない)ときと、``bump_normals_fbm`` へ回す残りを
決めるとき。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_regolith_hero](../../../../examples_3d/itokawa_regolith_hero.py) — `py -3.11 examples_3d/itokawa_regolith_hero.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`terrain`)

[mesh_displace_fbm](mesh_displace_fbm.md) · [terrain_region_mask](terrain_region_mask.md) · [mesh_scatter_boulders](mesh_scatter_boulders.md) · [mesh_edge_lengths](mesh_edge_lengths.md) · [mesh_subdivide](mesh_subdivide.md) · [mesh_displace_spectrum](mesh_displace_spectrum.md) · [bump_normals_fbm](bump_normals_fbm.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
