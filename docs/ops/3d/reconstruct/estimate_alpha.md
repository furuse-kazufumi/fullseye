---
op: estimate_alpha
dim: 3d
category: reconstruct
in: points
out: measurement
examples: [alpha_shape_topology, sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# estimate_alpha — 3D `reconstruct` op

- **データ種**: `points` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.estimate_alpha(points)` (実装を直接呼ぶなら `import recon3d; recon3d.estimate_alpha(points)`、台帳から引くなら `ops3d.get("estimate_alpha")`)

## 使い方

点群のスケールから推奨 alpha を返す(最近傍距離の中央値ベース)。

各点の最近傍距離の中央値 ``m`` を求め、半径しきい値 1/alpha ≈ 2m(隣接間隔の約 2 倍まで
許す)となるよう ``alpha = 1/(2m)`` を返す。これで表面付近の素性の良い四面体は残しつつ、
大きく間延びした四面体(=凹み・外側)を切り落とせる。重複点は最近傍 0 になるため正の距離のみ使う。

Parameters
----------
points : array_like (N,3)

Returns
-------
alpha : float
    正の有限値。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [alpha_shape_topology](../../../../examples_3d/alpha_shape_topology.py) — `py -3.11 examples_3d/alpha_shape_topology.py`
- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`reconstruct`)

[poisson_lite](poisson_lite.md) · [alpha_shape_mesh](alpha_shape_mesh.md) · [alpha_shape_boundary](alpha_shape_boundary.md)

---
*Provenance: recon3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
