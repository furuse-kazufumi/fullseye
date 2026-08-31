---
op: hough_sphere_3d
dim: 3d
category: detect
in: voxel
out: primitive
gpu: true
examples: [detect_primitives_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# hough_sphere_3d — 3D `detect` op

- **データ種**: `voxel` → `primitive`
- **呼び出し**: `import match3d; match3d.hough_sphere_3d(vol, device='cpu', radii=None, mc=0.0, iso=0.5, subvoxel=True)` (または `ops3d.get("hough_sphere_3d")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

球検出(2D Hough 円の 3D リフト)。中心 = p + sgn·r·n を半径 r ごとに投票。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [detect_primitives_3d](../../../../examples_3d/detect_primitives_3d.py) — `py -3.11 examples_3d/detect_primitives_3d.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [intersect_line_plane](../geometry/intersect_line_plane.md)

## 同カテゴリ(`detect`)

[hough_plane_3d](hough_plane_3d.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
