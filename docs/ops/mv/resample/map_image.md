---
op: map_image
dim: mv
category: resample
in: image2d × table
out: image2d
halcon: map_image
gpu: なし
examples: [machine_vision_tour, poc_real_chessboard_undistort]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# map_image — MV `resample` op

- **データ種**: `image2d × table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.map_image(image, image_map, fill=0.0)` (実装を直接呼ぶなら `import mvimage; mvimage.map_image(image, image_map, fill=0.0)`、台帳から引くなら `opsmv.get("map_image")`)
- **HALCON 相当**: `map_image`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

逆写像表を画像へ適用して再標本化する(出力の画素ごとに入力の座標を読む)。

``image_map`` は ``row_map`` / ``col_map`` の dict(``gen_radial_distortion_map`` の返りを
そのまま渡せる)。線形補間で読み、画像の外は ``fill`` で埋める。``image_map`` に写像の鍵が
無い(``x_map`` / ``y_map`` は画素 → ワールドの順写像で、このままでは穴が開く)と ValueError。
空の入力(``image`` が 0 要素)は ValueError。

Args:
    image: (H, W) の画像。
    image_map: ``row_map`` と ``col_map`` を持つ dict。形が出力の形になる。
    fill: 入力の外を読んだ画素の値。

Returns:
    ``image_map`` と同じ形の float 画像。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`
- [poc_real_chessboard_undistort](../../../../examples/poc_real_chessboard_undistort.py) — `py -3.11 examples/poc_real_chessboard_undistort.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[binocular_disparity_ms](../stereo/binocular_disparity_ms.md) · [binocular_distance_ms](../stereo/binocular_distance_ms.md) · [reconstruct_surface_stereo](../stereo/reconstruct_surface_stereo.md) · [rectify_to_world_plane](rectify_to_world_plane.md) · [change_radial_distortion_image](change_radial_distortion_image.md) · [crop_rectangle2](crop_rectangle2.md) · [atan2_image](../gray/atan2_image.md) · [area_center_gray](../gray/area_center_gray.md)

## 同カテゴリ(`resample`)

[rectify_to_world_plane](rectify_to_world_plane.md) · [change_radial_distortion_image](change_radial_distortion_image.md) · [crop_rectangle2](crop_rectangle2.md)

---
*Provenance: mvimage.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
