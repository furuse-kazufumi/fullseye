---
op: atan2_image
dim: mv
category: gray
in: image2d × image2d
out: image2d
halcon: atan2_image
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# atan2_image — MV `gray` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.atan2_image(image1, image2)` (実装を直接呼ぶなら `import filters_arith; filters_arith.atan2_image(image1, image2)`、台帳から引くなら `opsmv.get("atan2_image")`)
- **HALCON 相当**: `atan2_image`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

2 枚の画像の画素ごとの ``atan2(image1, image2)`` をラジアンで返す(atan2_image)。

勾配の成分から向きを求めるのに使う。値は ``-pi .. pi``。
空の入力(``image1`` が 0 要素)は ValueError。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[binocular_disparity_ms](../stereo/binocular_disparity_ms.md) · [binocular_distance_ms](../stereo/binocular_distance_ms.md) · [reconstruct_surface_stereo](../stereo/reconstruct_surface_stereo.md) · [map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [crop_rectangle2](../resample/crop_rectangle2.md) · [area_center_gray](area_center_gray.md)

## 同カテゴリ(`gray`)

[area_center_gray](area_center_gray.md) · [gray_histo](gray_histo.md) · [gray_projections](gray_projections.md) · [get_grayval_contour_xld](get_grayval_contour_xld.md)

---
*Provenance: filters_arith.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
