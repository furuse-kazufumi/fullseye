---
op: contour_to_world_plane_xld
dim: calib
category: plane
in: contour
out: contour
examples: [poc_wound_area_tracking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# contour_to_world_plane_xld — CALIB `plane` op

- **データ種**: `contour` → `contour`
- **呼び出し**: `import fullseye as fs; fs.ledger.contour_to_world_plane_xld(contour, homography)` (実装を直接呼ぶなら `import calib; calib.contour_to_world_plane_xld(contour, homography)`、台帳から引くなら `opscalib.get("contour_to_world_plane_xld")`)

## 使い方

XLD 輪郭(dict {cs:[Nx2]})を world 平面へ写す(contour_to_world_plane_xld)。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_wound_area_tracking](../../../../examples/poc_wound_area_tracking.py) — `py -3.11 examples/poc_wound_area_tracking.py`

## 型が繋がる次の op(`contour` を入力に取れる)

—

## 同カテゴリ(`plane`)

[image_to_world_plane](image_to_world_plane.md) · [image_points_to_world_plane](image_points_to_world_plane.md) · [gen_image_to_world_plane_map](gen_image_to_world_plane_map.md) · [gen_radial_distortion_map](gen_radial_distortion_map.md)

---
*Provenance: calib.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
