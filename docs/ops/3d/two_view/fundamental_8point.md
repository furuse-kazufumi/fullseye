---
op: fundamental_8point
dim: 3d
category: two_view
in: image2d × image2d
out: matrix
examples: [two_view_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# fundamental_8point — 3D `two_view` op

- **データ種**: `image2d × image2d` → `matrix`
- **呼び出し**: `import twoview; twoview.fundamental_8point(pts1, pts2)` (または `ops3d.get("fundamental_8point")`)

## 使い方

正規化 8 点法で基礎行列 F を推定(rank-2 強制)。→ F (3,3)。8 点以上必要。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [two_view_pose](../../../../examples_3d/two_view_pose.py) — `py -3.11 examples_3d/two_view_pose.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`two_view`)

[essential_8point](essential_8point.md) · [recover_pose](recover_pose.md) · [triangulate](triangulate.md) · [sampson_distance](sampson_distance.md)

---
*Provenance: twoview.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
