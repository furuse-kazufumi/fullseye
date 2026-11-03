---
op: change_radial_distortion_image
dim: mv
category: resample
in: image2d × table × table
out: image2d
halcon: change_radial_distortion_image
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# change_radial_distortion_image — MV `resample` op

- **データ種**: `image2d × table × table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.change_radial_distortion_image(image, cam_in, cam_out, fill=0.0)` (実装を直接呼ぶなら `import mvimage; mvimage.change_radial_distortion_image(image, cam_in, cam_out, fill=0.0)`、台帳から引くなら `opsmv.get("change_radial_distortion_image")`)
- **HALCON 相当**: `change_radial_distortion_image`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

除算モデルの歪みを持つカメラの画像を、別の歪み・内部パラメータの画像へ描き直す。

``cam_out`` の画素を歪み除去 → 正規化座標 → ``cam_in`` の焦点距離 → ``cam_in`` の歪みの順に
写して読む。``kappa`` の単位は 1/画素^2 で、主点からの画素座標に掛かる。``cam_out`` の
``kappa`` を 0 にすると歪み除去になる。空の入力(``image`` が 0 要素)は ValueError。

Args:
    image: (H, W) の画像。
    cam_in: 入力のカメラ(``fx`` / ``fy`` / ``cx`` / ``cy`` / ``kappa``)。
    cam_out: 出力のカメラ(同じ鍵)。
    fill: 入力の外の画素の値。

Returns:
    入力と同じ形の float 画像。

出典: R. Lenz and D. Fritsch, ISPRS J. Photogramm. Remote Sens. 45(2), 90-110 (1990)。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[binocular_disparity_ms](../stereo/binocular_disparity_ms.md) · [binocular_distance_ms](../stereo/binocular_distance_ms.md) · [reconstruct_surface_stereo](../stereo/reconstruct_surface_stereo.md) · [map_image](map_image.md) · [rectify_to_world_plane](rectify_to_world_plane.md) · [crop_rectangle2](crop_rectangle2.md) · [atan2_image](../gray/atan2_image.md) · [area_center_gray](../gray/area_center_gray.md)

## 同カテゴリ(`resample`)

[map_image](map_image.md) · [rectify_to_world_plane](rectify_to_world_plane.md) · [crop_rectangle2](crop_rectangle2.md)

---
*Provenance: mvimage.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
