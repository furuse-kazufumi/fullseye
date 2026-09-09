---
op: a3_distribution
dim: 3d
category: shape_descriptor
in: points
out: descriptor
examples: [shape_desc_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# a3_distribution — 3D `shape_descriptor` op

- **データ種**: `points` → `descriptor`
- **呼び出し**: `import fullseye as fs; fs.ledger.a3_distribution(points, bins: 'int' = 64, samples: 'int' = 100000, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import descriptors3d; descriptors3d.a3_distribution(points, bins: 'int' = 64, samples: 'int' = 100000, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("a3_distribution")`)

## 使い方

ランダムな 3 点 (A, B, C) が頂点 B で作る角の分布(Osada 2002 の A3)。

角度は回転・平行移動・スケールのすべてに不変(スケールしても角は変わらない)ため、
D2 と相補的な**無次元**の形状特徴になる。レンジ [0, π] 固定の正規化ヒストグラム
(bins,) を返す(総和 1)。空間的に重なった点(ゼロ長ベクトル)は角が未定義なので
除外する。

Parameters
----------
points : array_like, shape (N, 3)
    点群。N >= 3 が必要。
bins, samples, seed :
    d2_distribution と同義。

Returns
-------
np.ndarray, shape (bins,)
    正規化角度ヒストグラム(ラジアン、[0, π])。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape_desc_pose](../../../../examples_3d/shape_desc_pose.py) — `py -3.11 examples_3d/shape_desc_pose.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](shape_distance.md)

## 同カテゴリ(`shape_descriptor`)

[d2_distribution](d2_distribution.md) · [extent_signature](extent_signature.md) · [describe](describe.md) · [shape_distance](shape_distance.md)

---
*Provenance: descriptors3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
