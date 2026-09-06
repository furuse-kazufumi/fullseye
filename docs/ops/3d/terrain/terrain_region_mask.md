---
op: terrain_region_mask
dim: 3d
category: terrain
in: mesh
out: signal
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# terrain_region_mask — 3D `terrain` op

- **データ種**: `mesh` → `signal`
- **呼び出し**: `import render3d; render3d.terrain_region_mask(V, F, *, smooth_fraction: 'float' = 0.3, method: 'str' = 'neck', seed: 'int' = 0) -> 'np.ndarray'` (または `ops3d.get("terrain_region_mask")`)

## 使い方

Per-face terrain weights (M,) in [0,1]: 0 = smooth regolith "sea", 1 = rough highland.

``method='neck'`` (default, Itokawa-motivated): the sea is the band of faces around the
narrowest cross-section along the principal (long) axis — MUSES-C Regio sits in the neck
between head and body — widened until it covers ``smooth_fraction`` of the surface area.
``method='noise'``: low-frequency seeded fBm thresholded at the area-weighted
``smooth_fraction`` quantile (generic patches). ``method='slope'``: faces are ranked by
local slope (angle between face normal and the smoothed neighbourhood normal); the
flattest ``smooth_fraction`` of the area is sea. Deterministic; fail-closed on bad input.

返り値は面ごとの float64 ``(M,)`` で値は 0 か 1 の二値(中間値は出ない)。手順は
``method`` ごとにスコアを 1 つ作り、スコアの小さい面から面積を累積して全面積の
``smooth_fraction`` に達するまでを「海」(0)にする。

- ``'neck'``: 面重心の面積重み付き主軸(SVD 第 1 成分)に沿って、主軸座標の 20〜80 %
  区間を 24 ビンに切り、各ビンの半径 90 percentile が最小のビン中心を「くびれ」とし、
  くびれ面からの距離をスコアにする。8 面未満のビンは無視。``seed`` は使わない。
- ``'noise'``: 面重心での :func:`fbm_noise`(波長 = 境界箱対角 / 3、2 オクターブ、
  ``seed``)をスコアにする。
- ``'slope'``: 面法線と「3 頂点の頂点法線平均」のなす角(ラジアン)をスコアにする。
  ``seed`` は使わない。

``smooth_fraction`` は [0, 1] (範囲外・非有限は ``ValueError``)。0 なら全面 1、1 なら
全面 0 を即返す。``method`` が上記以外なら ``ValueError``。得た重みは
``mesh_scatter_boulders`` / ``sample_boulders`` の ``region_weights`` に渡して海に岩を
置かないようにする用途。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_regolith_hero](../../../../examples_3d/itokawa_regolith_hero.py) — `py -3.11 examples_3d/itokawa_regolith_hero.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`terrain`)

[mesh_displace_fbm](mesh_displace_fbm.md) · [mesh_scatter_boulders](mesh_scatter_boulders.md) · [mesh_edge_lengths](mesh_edge_lengths.md) · [mesh_subdivide](mesh_subdivide.md) · [displacement_band_weights](displacement_band_weights.md) · [mesh_displace_spectrum](mesh_displace_spectrum.md) · [bump_normals_fbm](bump_normals_fbm.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
