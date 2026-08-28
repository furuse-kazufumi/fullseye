---
op: sampson_distance
dim: 3d
category: two_view
in: image2d × image2d
out: measurement
examples: [two_view_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# sampson_distance — 3D `two_view` op

- **データ種**: `image2d × image2d` → `measurement`
- **呼び出し**: `import twoview; twoview.sampson_distance(F, pts1, pts2)` (または `ops3d.get("sampson_distance")`)

## 使い方

エピポーラ拘束の Sampson 距離(1 次幾何誤差、各対応)。→ (N,)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [two_view_pose](../../../../examples_3d/two_view_pose.py) — `py -3.11 examples_3d/two_view_pose.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`two_view`)

[fundamental_8point](fundamental_8point.md) · [essential_8point](essential_8point.md) · [recover_pose](recover_pose.md) · [triangulate](triangulate.md)

---
*Provenance: twoview.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
