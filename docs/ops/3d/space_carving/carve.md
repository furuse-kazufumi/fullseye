---
op: carve
dim: 3d
category: space_carving
in: images
out: voxel
examples: [space_carving]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# carve — 3D `space_carving` op

- **データ種**: `images` → `voxel`
- **呼び出し**: `import visualhull; visualhull.carve(silhouettes: 'Sequence[np.ndarray]', Ks: 'Sequence[np.ndarray]', Rs: 'Sequence[np.ndarray]', ts: 'Sequence[np.ndarray]', bounds: 'Bounds', res: 'int') -> 'np.ndarray'` (または `ops3d.get("carve")`)

## 使い方

bounds を res^3 voxel に離散化し、全シルエット内に射影される voxel を残す(空間彫刻)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [space_carving](../../../../examples_3d/space_carving.py) — `py -3.11 examples_3d/space_carving.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`space_carving`)

[visual_hull](visual_hull.md) · [synthesize_silhouette](synthesize_silhouette.md)

---
*Provenance: visualhull.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
