---
op: alpha_shape_boundary
dim: 3d
category: reconstruct
in: points
out: indices
examples: [sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# alpha_shape_boundary — 3D `reconstruct` op

- **データ種**: `points` → `indices`
- **呼び出し**: `import fullseye as fs; fs.ledger.alpha_shape_boundary(points, alpha)` (実装を直接呼ぶなら `import recon3d; recon3d.alpha_shape_boundary(points, alpha)`、台帳から引くなら `ops3d.get("alpha_shape_boundary")`)

## 使い方

alpha shapes による**境界点インデックス**を返す(点群 → 境界点)。

Delaunay 四面体分割の外接球半径 < 1/alpha の四面体の表面三角形(境界面)を集め、その頂点
集合を境界点とする。中実(表面+内部)の点群から表面殻の点だけを抜き出す用途に向く。
alpha を大きくすると許す半径 1/alpha が小さくなり、より密着した(細部を拾う)境界になる。

Parameters
----------
points : array_like (N,3)
alpha : float
    正の実数。半径しきい値は 1/alpha。``estimate_alpha`` で目安を得られる。

Returns
-------
boundary_point_indices : numpy.ndarray (K,) int64
    points に対する境界点の index(昇順・重複なし)。境界が無ければ空配列。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`indices` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`reconstruct`)

[poisson_lite](poisson_lite.md) · [alpha_shape_mesh](alpha_shape_mesh.md) · [estimate_alpha](estimate_alpha.md)

---
*Provenance: recon3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
