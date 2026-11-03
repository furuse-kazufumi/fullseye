---
op: crop_rectangle2
dim: mv
category: resample
in: image2d
out: image2d
halcon: crop_rectangle2
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# crop_rectangle2 — MV `resample` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.crop_rectangle2(image, row, col, phi, length1, length2) -> 'np.ndarray'` (実装を直接呼ぶなら `import image_gen; image_gen.crop_rectangle2(image, row, col, phi, length1, length2) -> 'np.ndarray'`、台帳から引くなら `opsmv.get("crop_rectangle2")`)
- **HALCON 相当**: `crop_rectangle2`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

回転矩形の内側を線形補間で読み、軸に沿った画像として切り出す(crop_rectangle2)。

矩形は中心 ``(row, col)``、長軸の半分 ``length1``、短軸の半分 ``length2``、向き ``phi``
[rad]。向きはこの repo の矩形(``gen_rectangle2_contour_xld``)と同じで、``phi`` が正だと
長軸は右へ進むほど行が増える。出力は (2 length2 + 1, 2 length1 + 1)。
空の入力(``image`` が 0 要素)は ValueError。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[binocular_disparity_ms](../stereo/binocular_disparity_ms.md) · [binocular_distance_ms](../stereo/binocular_distance_ms.md) · [reconstruct_surface_stereo](../stereo/reconstruct_surface_stereo.md) · [map_image](map_image.md) · [rectify_to_world_plane](rectify_to_world_plane.md) · [change_radial_distortion_image](change_radial_distortion_image.md) · [atan2_image](../gray/atan2_image.md) · [area_center_gray](../gray/area_center_gray.md)

## 同カテゴリ(`resample`)

[map_image](map_image.md) · [rectify_to_world_plane](rectify_to_world_plane.md) · [change_radial_distortion_image](change_radial_distortion_image.md)

---
*Provenance: image_gen.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
