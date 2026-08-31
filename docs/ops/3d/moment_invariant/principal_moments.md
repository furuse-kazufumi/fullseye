---
op: principal_moments
dim: 3d
category: moment_invariant
in: points
out: descriptor
examples: [shape_desc_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# principal_moments — 3D `moment_invariant` op

- **データ種**: `points` → `descriptor`
- **呼び出し**: `import moments3d; moments3d.principal_moments(points) -> 'np.ndarray'` (または `ops3d.get("principal_moments")`)

## 使い方

慣性テンソルの固有値(主慣性モーメント、降順ソート、回転不変)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape_desc_pose](../../../../examples_3d/shape_desc_pose.py) — `py -3.11 examples_3d/shape_desc_pose.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`moment_invariant`)

[moment_invariants](moment_invariants.md) · [central_moments](central_moments.md) · [inertia_tensor](inertia_tensor.md)

---
*Provenance: moments3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
