---
op: gradient3d
dim: 3d
category: edges
in: voxel
out: gradient
examples: [edges_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# gradient3d — 3D `edges` op

- **データ種**: `voxel` → `gradient`
- **呼び出し**: `import edges3d; edges3d.gradient3d(vol, sigma: 'float' = 1.0)` (または `ops3d.get("gradient3d")`)

## 使い方

ガウス平滑後の中心差分勾配を計算する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [edges_3d](../../../../examples_3d/edges_3d.py) — `py -3.11 examples_3d/edges_3d.py`

## 型が繋がる次の op(`gradient` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`edges`)

[canny3d](canny3d.md) · [log_zero_crossings](log_zero_crossings.md) · [link_edges](link_edges.md) · [edge_points](edge_points.md)

---
*Provenance: edges3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
