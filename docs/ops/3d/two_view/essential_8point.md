---
op: essential_8point
dim: 3d
category: two_view
in: image2d × image2d
out: matrix
examples: [sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# essential_8point — 3D `two_view` op

- **データ種**: `image2d × image2d` → `matrix`
- **呼び出し**: `import twoview; twoview.essential_8point(pts1, pts2, K1, K2=None)` (または `ops3d.get("essential_8point")`)

## 使い方

対応点 + K から本質行列 E を直接。→ E (3,3)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`two_view`)

[fundamental_8point](fundamental_8point.md) · [recover_pose](recover_pose.md) · [triangulate](triangulate.md) · [sampson_distance](sampson_distance.md)

---
*Provenance: twoview.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
