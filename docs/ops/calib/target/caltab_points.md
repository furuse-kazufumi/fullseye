---
op: caltab_points
dim: calib
category: target
in: 
out: points
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# caltab_points — CALIB `target` op

- **データ種**: `なし` → `points`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.caltab_points(rows=7, cols=7, spacing=1.0)` (実装を直接呼ぶなら `import caltab; caltab.caltab_points(rows=7, cols=7, spacing=1.0)`、台帳から引くなら `opscalib.get("caltab_points")`)

## 使い方

校正板の理想マーク座標(ワールド, mm; 原点=最初のマーク)を (y, x) で返す(caltab_points)。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`points` を入力に取れる)

[project_3d_point](../project/project_3d_point.md) · [project_point_hom_mat3d](../project/project_point_hom_mat3d.md) · [project_hom_point_hom_mat3d](../project/project_hom_point_hom_mat3d.md) · [image_to_world_plane](../plane/image_to_world_plane.md) · [image_points_to_world_plane](../plane/image_points_to_world_plane.md) · [camera_calibration](../calibrate/camera_calibration.md) · [vector_to_rigid](../fit/vector_to_rigid.md) · [vector_to_similarity](../fit/vector_to_similarity.md)

## 同カテゴリ(`target`)

[create_caltab](create_caltab.md) · [gen_caltab](gen_caltab.md) · [sim_caltab](sim_caltab.md) · [disp_caltab](disp_caltab.md) · [find_caltab](find_caltab.md)

---
*Provenance: caltab.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
