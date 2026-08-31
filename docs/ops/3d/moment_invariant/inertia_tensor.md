---
op: inertia_tensor
dim: 3d
category: moment_invariant
in: points
out: matrix
examples: [moment_invariants]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# inertia_tensor — 3D `moment_invariant` op

- **データ種**: `points` → `matrix`
- **呼び出し**: `import moments3d; moments3d.inertia_tensor(points) -> 'np.ndarray'` (または `ops3d.get("inertia_tensor")`)

## 使い方

点群の慣性テンソル (3,3)(中心 2 次モーメントから、等質量・総質量 1)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [moment_invariants](../../../../examples_3d/moment_invariants.py) — `py -3.11 examples_3d/moment_invariants.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`moment_invariant`)

[moment_invariants](moment_invariants.md) · [principal_moments](principal_moments.md) · [central_moments](central_moments.md)

---
*Provenance: moments3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
