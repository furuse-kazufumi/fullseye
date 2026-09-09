---
op: voxel_to_mips
dim: 3d
category: transform
in: voxel
out: images
examples: [transforms_repr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# voxel_to_mips — 3D `transform` op

- **データ種**: `voxel` → `images`
- **呼び出し**: `import fullseye as fs; fs.ledger.voxel_to_mips(vol)` (実装を直接呼ぶなら `import match3d; match3d.voxel_to_mips(vol)`、台帳から引くなら `ops3d.get("voxel_to_mips")`)

## 使い方

3D → 直交 3 方向の最大値投影(MIP)。2D 手法(accel の 2D NCC 等)を適用する入口。

入力 ``(D,H,W)`` に対し ``[max(axis=0), max(axis=1), max(axis=2)]`` の list を返す。形は
それぞれ ``(H,W)``(軸 0=D を潰す)、``(D,W)``(軸 1=H を潰す)、``(D,H)``(軸 2=W を潰す)、
dtype float64。値は入力の最大値そのまま(正規化しない)。負の値も max なので通り、
密度 0 の背景は 0 のまま。
形の検証は無い(2-D は ``axis=2`` で失敗し、4-D 以上は動いてしまう)ので、呼び手で次元を確かめる。
``match_mip_2d`` はこの 3 枚に 2D NCC を掛けて 3D 位置を冗長推定する。任意視点の投影は
``render_volume_projection``(mode="mip")。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`

## 型が繋がる次の op(`images` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [photometric_stereo](../photometric/photometric_stereo.md) · [wrapped_phase](../structured_light/wrapped_phase.md) · [graycode_decode](../structured_light/graycode_decode.md) · [decode_fringe](../structured_light/decode_fringe.md) · [carve](../space_carving/carve.md) · [visual_hull](../space_carving/visual_hull.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mesh](voxel_to_mesh.md) · [tsdf_from_depth](tsdf_from_depth.md) · [signed_distance_field](signed_distance_field.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
