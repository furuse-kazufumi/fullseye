---
op: reflection_symmetry_score
dim: 3d
category: symmetry
in: points
out: measurement
examples: [dl_mesh_symmetry, reflection_symmetry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# reflection_symmetry_score — 3D `symmetry` op

- **データ種**: `points` → `measurement`
- **呼び出し**: `import symmetry3d; symmetry3d.reflection_symmetry_score(points, plane_point, plane_normal)` (または `ops3d.get("reflection_symmetry_score")`)

## 使い方

反射対称スコア = chamfer(鏡映, 元) / 中央値最近傍間隔(小さいほど対称、スケール不変)。→ float。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dl_mesh_symmetry](../../../../examples_3d/dl_mesh_symmetry.py) — `py -3.11 examples_3d/dl_mesh_symmetry.py`
- [reflection_symmetry](../../../../examples_3d/reflection_symmetry.py) — `py -3.11 examples_3d/reflection_symmetry.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`symmetry`)

[detect_reflection_symmetry](detect_reflection_symmetry.md) · [detect_rotational_symmetry](detect_rotational_symmetry.md) · [reflect_points](reflect_points.md)

---
*Provenance: symmetry3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
