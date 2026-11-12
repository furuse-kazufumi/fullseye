---
op: rectify_to_world_plane
dim: mv
category: resample
in: image2d × table × matrix
out: image2d
halcon: image_to_world_plane
gpu: なし
examples: [machine_vision_tour, poc_real_chessboard_undistort]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# rectify_to_world_plane — MV `resample` op

- **データ種**: `image2d × table × matrix` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.rectify_to_world_plane(image, cam_par, pose, width, height, scale, origin=(0.0, 0.0), fill=0.0)` (実装を直接呼ぶなら `import mvimage; mvimage.rectify_to_world_plane(image, cam_par, pose, width, height, scale, origin=(0.0, 0.0), fill=0.0)`、台帳から引くなら `opsmv.get("rectify_to_world_plane")`)
- **HALCON 相当**: `image_to_world_plane`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

画像をワールド平面 z=0 の正面図へ平行化する(1 画素 = ``scale`` のワールド単位)。

世界の点 ``(x, y, 0)`` を ``pose``(ワールド → カメラの 4x4)で写し、ピンホール投影と
除算モデルの歪み(``cam_par`` に ``kappa`` があるとき)を通して入力の座標を求める。
出力の行は y、列は x に沿う。``origin`` は出力の (0, 0) に当たる世界の ``(x, y)``。
カメラの後ろへ落ちる画素は ``fill``。空の入力(``image`` が 0 要素)は ValueError。

Args:
    image: (H, W) の画像。
    cam_par: ``fx`` / ``fy`` / ``cx`` / ``cy``(と任意で ``kappa``)の dict。
    pose: 4x4 の同次変換(ワールド → カメラ)。
    width: 出力の列数。
    height: 出力の行数。
    scale: 1 画素あたりのワールド単位(> 0)。
    origin: 出力の左上の画素が指す世界の ``(x, y)``。
    fill: 入力の外とカメラの後ろの画素の値。

Returns:
    (height, width) の float 画像。

出典: R. Hartley and A. Zisserman, Multiple View Geometry, 2nd ed., ch. 2 (平面の射影変換)。

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

[binocular_disparity_ms](../stereo/binocular_disparity_ms.md) · [binocular_distance_ms](../stereo/binocular_distance_ms.md) · [reconstruct_surface_stereo](../stereo/reconstruct_surface_stereo.md) · [map_image](map_image.md) · [change_radial_distortion_image](change_radial_distortion_image.md) · [crop_rectangle2](crop_rectangle2.md) · [atan2_image](../gray/atan2_image.md) · [area_center_gray](../gray/area_center_gray.md)

## 同カテゴリ(`resample`)

[map_image](map_image.md) · [change_radial_distortion_image](change_radial_distortion_image.md) · [crop_rectangle2](crop_rectangle2.md)

---
*Provenance: mvimage.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
