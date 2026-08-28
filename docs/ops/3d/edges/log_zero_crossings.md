---
op: log_zero_crossings
dim: 3d
category: edges
in: voxel
out: voxel
examples: [edges_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# log_zero_crossings — 3D `edges` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import edges3d; edges3d.log_zero_crossings(vol, sigma: 'float' = 1.5, rel_thresh: 'float' = 0.001) -> 'np.ndarray'` (または `ops3d.get("log_zero_crossings")`)

## 使い方

Laplacian-of-Gaussian のゼロ交差エッジ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [edges_3d](../../../../examples_3d/edges_3d.py) — `py -3.11 examples_3d/edges_3d.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`edges`)

[gradient3d](gradient3d.md) · [canny3d](canny3d.md) · [link_edges](link_edges.md) · [edge_points](edge_points.md)

---
*Provenance: edges3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
