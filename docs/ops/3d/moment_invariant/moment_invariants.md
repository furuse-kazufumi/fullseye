---
op: moment_invariants
dim: 3d
category: moment_invariant
in: points
out: descriptor
examples: [moment_invariants]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# moment_invariants — 3D `moment_invariant` op

- **データ種**: `points` → `descriptor`
- **呼び出し**: `import moments3d; moments3d.moment_invariants(points) -> 'np.ndarray'` (または `ops3d.get("moment_invariants")`)

## 使い方

並進+回転+スケール不変な形状特徴ベクトル(Sadjadi–Hall 流 + 高次半径分布)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [moment_invariants](../../../../examples_3d/moment_invariants.py) — `py -3.11 examples_3d/moment_invariants.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`moment_invariant`)

[principal_moments](principal_moments.md) · [central_moments](central_moments.md) · [inertia_tensor](inertia_tensor.md)

---
*Provenance: moments3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
