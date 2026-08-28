---
op: orient_normals
dim: 3d
category: normals_orient
in: points × normals
out: normals
examples: [oriented_normals]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# orient_normals — 3D `normals_orient` op

- **データ種**: `points × normals` → `normals`
- **呼び出し**: `import normals_orient; normals_orient.orient_normals(points, normals, k: 'int' = 20, seed_dir=None) -> 'np.ndarray'` (または `ops3d.get("orient_normals")`)

## 使い方

Hoppe 法で法線を**大域一貫**に向き付け(MST 伝播)。→ (N,3)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [oriented_normals](../../../../examples_3d/oriented_normals.py) — `py -3.11 examples_3d/oriented_normals.py`

## 型が繋がる次の op(`normals` を入力に取れる)

[icp_point2plane](../refine/icp_point2plane.md) · [compute_fpfh](../feature_register/compute_fpfh.md) · [shot_descriptor](../feature_register/shot_descriptor.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [reflect](../optics/reflect.md) · [refract](../optics/refract.md) · [render_shaded](../render/render_shaded.md) · [phong_shade](../render/phong_shade.md)

## 同カテゴリ(`normals_orient`)

[estimate_oriented_normals](estimate_oriented_normals.md)

---
*Provenance: normals_orient.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
