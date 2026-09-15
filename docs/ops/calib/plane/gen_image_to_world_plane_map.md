---
op: gen_image_to_world_plane_map
dim: calib
category: plane
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# gen_image_to_world_plane_map — CALIB `plane` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.gen_image_to_world_plane_map(cam_par, pose, shape, scale=1.0)` (実装を直接呼ぶなら `import caltab; caltab.gen_image_to_world_plane_map(cam_par, pose, shape, scale=1.0)`、台帳から引くなら `opscalib.get("gen_image_to_world_plane_map")`)

## 使い方

画像→ワールド平面(z=0)の写像テーブルを生成(gen_image_to_world_plane_map)。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[sim_caltab](../target/sim_caltab.md) · [disp_caltab](../target/disp_caltab.md)

## 同カテゴリ(`plane`)

[image_to_world_plane](image_to_world_plane.md) · [image_points_to_world_plane](image_points_to_world_plane.md) · [contour_to_world_plane_xld](contour_to_world_plane_xld.md) · [gen_radial_distortion_map](gen_radial_distortion_map.md)

---
*Provenance: caltab.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
