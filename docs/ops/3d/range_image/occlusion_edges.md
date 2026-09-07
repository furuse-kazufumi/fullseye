---
op: occlusion_edges
dim: 3d
category: range_image
in: depth
out: image2d
examples: [range_image]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# occlusion_edges — 3D `range_image` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.occlusion_edges(depth, rel_thresh=0.05)` (実装を直接呼ぶなら `import range_image; range_image.occlusion_edges(depth, rel_thresh=0.05)`、台帳から引くなら `ops3d.get("occlusion_edges")`)

## 使い方

深度の不連続(前景/背景境界 = 遮蔽エッジ)を検出。→ bool HxW。

遮蔽エッジは深度の**不連続(step)**であって傾斜(slope)ではない。一様な傾斜面は
連続で遮蔽を含まないため flag してはならない。一階勾配(=深度/画素)は傾斜そのもので、
段差か斜面かを区別できない(かつ絶対深度の割合と比較するのは次元不整合)。

そこで軸ごとの**二階差分(離散ラプラシアン相当)** ``d[i+1]-2*d[i]+d[i-1]`` を使う。
一様傾斜(深度が近傍で線形)なら二階差分 ≈ 0、fronto-parallel な段差では両側で大きな値。
これを局所深度で正規化した相対的な深度ジャンプが rel_thresh を超える画素を境界とする。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)
- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [range_image](../../../../examples_3d/range_image.py) — `py -3.11 examples_3d/range_image.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`range_image`)

[depth_to_organized_points](depth_to_organized_points.md) · [normals_from_depth](normals_from_depth.md) · [bearing_angle_image](bearing_angle_image.md)

---
*Provenance: range_image.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
