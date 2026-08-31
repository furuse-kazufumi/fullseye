---
op: detect_reflection_symmetry
dim: 3d
category: symmetry
in: points
out: primitive
examples: [dl_mesh_symmetry, itokawa_symmetry_honest, reflection_symmetry, symmetry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# detect_reflection_symmetry — 3D `symmetry` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import symmetry3d; symmetry3d.detect_reflection_symmetry(points)` (または `ops3d.get("detect_reflection_symmetry")`)

## 使い方

PCA 主軸を法線とする候補平面(重心通過)から最良の反射対称面を選ぶ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dl_mesh_symmetry](../../../../examples_3d/dl_mesh_symmetry.py) — `py -3.11 examples_3d/dl_mesh_symmetry.py`
- [itokawa_symmetry_honest](../../../../examples_3d/itokawa_symmetry_honest.py) — `py -3.11 examples_3d/itokawa_symmetry_honest.py`
- [reflection_symmetry](../../../../examples_3d/reflection_symmetry.py) — `py -3.11 examples_3d/reflection_symmetry.py`
- [symmetry](../../../../examples_3d/symmetry.py) — `py -3.11 examples_3d/symmetry.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [intersect_line_plane](../geometry/intersect_line_plane.md)

## 同カテゴリ(`symmetry`)

[detect_rotational_symmetry](detect_rotational_symmetry.md) · [reflect_points](reflect_points.md) · [reflection_symmetry_score](reflection_symmetry_score.md)

---
*Provenance: symmetry3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
