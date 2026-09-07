---
op: d2_distribution
dim: 3d
category: shape_descriptor
in: points
out: descriptor
examples: [shape_desc_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# d2_distribution — 3D `shape_descriptor` op

- **データ種**: `points` → `descriptor`
- **呼び出し**: `import fullseye as fs; fs.ledger.d2_distribution(points, bins: 'int' = 64, samples: 'int' = 100000, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import descriptors3d; descriptors3d.d2_distribution(points, bins: 'int' = 64, samples: 'int' = 100000, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("d2_distribution")`)

## 使い方

ランダムな 2 点対のユークリッド距離分布(Osada 2002 の D2)。

N 点から `samples` 組の相異なる点対 (i, j) を乱択し、その距離を集計する。
距離は**平均距離で割って正規化**するため、回転・平行移動・**スケール**に不変。
固定レンジ [0, _D2_MAX] の正規化ヒストグラム (bins,) を返す(総和 1)。

Parameters
----------
points : array_like, shape (N, 3)
    点群。N >= 2 が必要。
bins : int
    ヒストグラムの bin 数。
samples : int
    乱択する点対の数。多いほど分散が下がる(サンプリング誤差 ~ 1/sqrt(samples))。
seed : int
    乱数シード。同 seed・同点群なら決定論的に同一。

Returns
-------
np.ndarray, shape (bins,)
    正規化距離ヒストグラム。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape_desc_pose](../../../../examples_3d/shape_desc_pose.py) — `py -3.11 examples_3d/shape_desc_pose.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](shape_distance.md)

## 同カテゴリ(`shape_descriptor`)

[a3_distribution](a3_distribution.md) · [extent_signature](extent_signature.md) · [describe](describe.md) · [shape_distance](shape_distance.md)

---
*Provenance: descriptors3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
