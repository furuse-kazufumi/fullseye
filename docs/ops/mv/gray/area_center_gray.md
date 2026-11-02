---
op: area_center_gray
dim: mv
category: gray
in: image2d
out: table
halcon: area_center_gray
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# area_center_gray — MV `gray` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.area_center_gray(image, region=None)` (実装を直接呼ぶなら `import image_gray; image_gray.area_center_gray(image, region=None)`、台帳から引くなら `opsmv.get("area_center_gray")`)
- **HALCON 相当**: `area_center_gray`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

灰色値を重みとした質量と重心 ``(row, col)`` を返す(area_center_gray)。

``region`` を渡すとその画素だけを数える。質量が 0 なら ``area`` が 0.0 で重心は原点を返す
(理由: 重みが無いと重心が定義できない)。空の入力(``image`` が 0 要素)は ValueError。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [find_ncc_models](../detect/find_ncc_models.md) · [run_bg_esti](../tracking/run_bg_esti.md) · [give_bg_esti](../tracking/give_bg_esti.md) · [update_bg_esti](../tracking/update_bg_esti.md) · [classify_class_gmm](../classify/classify_class_gmm.md)

## 同カテゴリ(`gray`)

[atan2_image](atan2_image.md) · [gray_histo](gray_histo.md) · [gray_projections](gray_projections.md) · [get_grayval_contour_xld](get_grayval_contour_xld.md)

---
*Provenance: image_gray.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
