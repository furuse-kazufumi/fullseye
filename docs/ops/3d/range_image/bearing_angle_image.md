---
op: bearing_angle_image
dim: 3d
category: range_image
in: depth
out: image2d
examples: [sensor_seg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# bearing_angle_image — 3D `range_image` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import range_image; range_image.bearing_angle_image(depth, direction='down')` (または `ops3d.get("bearing_angle_image")`)

## 使い方

bearing-angle 画像: 走査方向に沿った視線と局所面のなす角(range image の古典記述子)。→ HxW(度)。

隣接深度差から局所傾斜角 atan2(Δdepth, step) を計算。斜面の向きに敏感で照明不変。
direction ∈ {down,up,right,left}。

``direction`` が "down"/"up" なら行方向(axis=0)、"right"/"left" なら列方向(axis=1)の
``np.gradient``(中心差分、端は片側差分)で隣接深度差 Δd を取り、"up"/"left" では符号を
反転する。角度は ``degrees(atan2(Δd, 1))`` なので値域は (-90, 90) 度、平坦面で 0、走査
方向に遠ざかる面で正。格子間隔を 1 としているため、深度の単位が画素と違う(mm 等)場合
は幾何学的な入射角そのものではなく「深度単位あたりの傾き」の角になる。上記 4 語以外の
``direction`` は列方向・符号そのままとして扱われ、エラーにはならない。返り値は float32
の ``(H,W)``。深度の段差では ±90 度近くまで振れるので遮蔽の目安にもなるが、段差と斜面
を区別するには ``occlusion_edges`` を使う。入力検証は無い。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)
- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sensor_seg](../../../../examples_3d/sensor_seg.py) — `py -3.11 examples_3d/sensor_seg.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`range_image`)

[depth_to_organized_points](depth_to_organized_points.md) · [normals_from_depth](normals_from_depth.md) · [occlusion_edges](occlusion_edges.md)

---
*Provenance: range_image.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
