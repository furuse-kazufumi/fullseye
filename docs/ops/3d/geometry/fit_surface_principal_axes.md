---
op: fit_surface_principal_axes
dim: 3d
category: geometry
in: points
out: table
gpu: なし
examples: [primitive_fitting_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# fit_surface_principal_axes — 3D `geometry` op

- **データ種**: `points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_surface_principal_axes(points, degree: 'int' = 2, *, isotropy_ratio: 'float' = 0.95) -> 'dict'` (実装を直接呼ぶなら `import measure3d; measure3d.fit_surface_principal_axes(points, degree: 'int' = 2, *, isotropy_ratio: 'float' = 0.95) -> 'dict'`、台帳から引くなら `ops3d.get("fit_surface_principal_axes")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

斜めの反った面を PCA 主軸へ回してから多項式 ``z'=f(x',y')`` を当てはめる。

The two largest principal axes span the local x/y plane and the smallest is
local z. Returns ``center``, row-vector ``axes``, monomial ``powers``,
``coefficients``, local and original-frame ``fitted_points``, unit
``normal`` at the centroid, and gradient-normalised geometric ``rms``.
``degree`` is the total polynomial degree. A cloud whose two largest
variances differ by less than ``isotropy_ratio`` is rejected because its
in-plane principal directions are not identifiable. For degree one the
returned normal agrees with :func:`fit_plane3` up to sign.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [primitive_fitting_3d](../../../../examples_3d/primitive_fitting_3d.py) — `py -3.11 examples_3d/primitive_fitting_3d.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`geometry`)

[line_from_2points](line_from_2points.md) · [plane_from_3points](plane_from_3points.md) · [angle_3points](angle_3points.md) · [angle_between_lines](angle_between_lines.md) · [angle_between_planes](angle_between_planes.md) · [angle_line_plane](angle_line_plane.md) · [distance_point_plane](distance_point_plane.md) · [distance_point_line](distance_point_line.md)

---
*Provenance: measure3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
