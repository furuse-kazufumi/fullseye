---
op: extent_signature
dim: 3d
category: shape_descriptor
in: points
out: descriptor
examples: [shape_desc_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# extent_signature — 3D `shape_descriptor` op

- **データ種**: `points` → `descriptor`
- **呼び出し**: `import descriptors3d; descriptors3d.extent_signature(points) -> 'np.ndarray'` (または `ops3d.get("extent_signature")`)

## 使い方

PCA 主軸(共分散の固有ベクトル)方向の広がりの比を返す。

共分散行列の固有値は回転に不変。ここでは固有値の平方根(= 各主軸方向の標準偏差、
長さの次元)を降順に並べ、総和 1 に正規化して (3,) ベクトルにする。これにより
絶対スケールが消え、**回転・平行移動・スケールに不変**な「形の細長さ」指標になる。

- 等方的な形状(球・立方体)→ 3 成分がほぼ等値 [~0.33, ~0.33, ~0.33]
- 細長い棒 → 1 成分が突出 [~0.9, ~0.05, ~0.05]

Parameters
----------
points : array_like, shape (N, 3)
    点群。N >= 3 が必要(共分散を意味のある形で作るため)。

Returns
-------
np.ndarray, shape (3,)
    降順・総和 1 に正規化した広がりベクトル。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape_desc_pose](../../../../examples_3d/shape_desc_pose.py) — `py -3.11 examples_3d/shape_desc_pose.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](shape_distance.md)

## 同カテゴリ(`shape_descriptor`)

[d2_distribution](d2_distribution.md) · [a3_distribution](a3_distribution.md) · [describe](describe.md) · [shape_distance](shape_distance.md)

---
*Provenance: descriptors3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
