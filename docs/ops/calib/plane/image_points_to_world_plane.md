---
op: image_points_to_world_plane
dim: calib
category: plane
in: table
out: keypoints
halcon: image_points_to_world_plane
gpu: なし
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# image_points_to_world_plane — CALIB `plane` op

- **データ種**: `table` → `keypoints`
- **呼び出し**: `import fullseye as fs; fs.ledger.image_points_to_world_plane(cam_par, pose, image_points, scale=1.0)` (実装を直接呼ぶなら `import calib; calib.image_points_to_world_plane(cam_par, pose, image_points, scale=1.0)`、台帳から引くなら `opscalib.get("image_points_to_world_plane")`)
- **HALCON 相当**: `image_points_to_world_plane`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

カメラ内部/外部から画素を world 平面 z=0 へ逆投影(image_points_to_world_plane)。

返り値は (N,2) の world 座標 × ``scale``。視線が z=0 平面とカメラの**前**で交わらない画素
(地平線より上など、交点がカメラの後ろ)は平面上の点を見ていないので、その行は ``nan``。
視線が平面と平行な画素は ``ValueError``。

★2026-11-05(敵対的検証 geometry、未再現の疑いを確認): 以前は交点の係数 lam < 0(カメラの
後ろ)でも有限の world 点を返していた(深度 −6.7 の点が「見えている点」として返った)。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`keypoints` を入力に取れる)

[image_to_world_plane](image_to_world_plane.md) · [camera_calibration](../calibrate/camera_calibration.md) · [camera_calibration_lm](../calibrate/camera_calibration_lm.md) · [stereo_calibration_lm](../calibrate/stereo_calibration_lm.md) · [vector_to_rigid](../fit/vector_to_rigid.md) · [vector_to_similarity](../fit/vector_to_similarity.md) · [hom_vector_to_proj_hom_mat2d](../fit/hom_vector_to_proj_hom_mat2d.md)

## 同カテゴリ(`plane`)

[image_to_world_plane](image_to_world_plane.md) · [contour_to_world_plane_xld](contour_to_world_plane_xld.md) · [gen_image_to_world_plane_map](gen_image_to_world_plane_map.md) · [gen_radial_distortion_map](gen_radial_distortion_map.md)

---
*Provenance: calib.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
