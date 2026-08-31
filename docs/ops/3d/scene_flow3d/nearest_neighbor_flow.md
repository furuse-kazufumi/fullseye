---
op: nearest_neighbor_flow
dim: 3d
category: scene_flow3d
in: points × points
out: flow
examples: [scene_flow_rigid]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# nearest_neighbor_flow — 3D `scene_flow3d` op

- **データ種**: `points × points` → `flow`
- **呼び出し**: `import scene_flow3d; scene_flow3d.nearest_neighbor_flow(pts0, pts1) -> 'np.ndarray'` (または `ops3d.get("nearest_neighbor_flow")`)

## 使い方

各点 pts0 から pts1 の最近傍への 3-D 変位ベクトル場 (N, 3) を返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [scene_flow_rigid](../../../../examples_3d/scene_flow_rigid.py) — `py -3.11 examples_3d/scene_flow_rigid.py`

## 型が繋がる次の op(`flow` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`scene_flow3d`)

[rigid_flow](rigid_flow.md) · [smooth_flow](smooth_flow.md)

---
*Provenance: scene_flow3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
