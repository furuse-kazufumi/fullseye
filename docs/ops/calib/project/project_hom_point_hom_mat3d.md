---
op: project_hom_point_hom_mat3d
dim: calib
category: project
in: points
out: points
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# project_hom_point_hom_mat3d — CALIB `project` op

- **データ種**: `points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.project_hom_point_hom_mat3d(points_hom, hom_mat3d)` (実装を直接呼ぶなら `import calib; calib.project_hom_point_hom_mat3d(points_hom, hom_mat3d)`、台帳から引くなら `opscalib.get("project_hom_point_hom_mat3d")`)

## 使い方

同次 3D 点 (4,) を 3x4/4x4 射影行列で投影し画素 (row, col) を返す
(project_hom_point_hom_mat3d)。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`points` を入力に取れる)

[project_3d_point](project_3d_point.md) · [project_point_hom_mat3d](project_point_hom_mat3d.md) · [image_to_world_plane](../plane/image_to_world_plane.md) · [image_points_to_world_plane](../plane/image_points_to_world_plane.md) · [camera_calibration](../calibrate/camera_calibration.md) · [vector_to_rigid](../fit/vector_to_rigid.md) · [vector_to_similarity](../fit/vector_to_similarity.md) · [hom_vector_to_proj_hom_mat2d](../fit/hom_vector_to_proj_hom_mat2d.md)

## 同カテゴリ(`project`)

[project_3d_point](project_3d_point.md) · [project_point_hom_mat3d](project_point_hom_mat3d.md)

---
*Provenance: calib.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
