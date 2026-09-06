---
op: signed_distance_field
dim: 3d
category: transform
in: voxel
out: sdf
gpu: true
examples: [transforms_repr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# signed_distance_field — 3D `transform` op

- **データ種**: `voxel` → `sdf`
- **呼び出し**: `import match3d; match3d.signed_distance_field(vol, device='cpu', iso=0.5)` (または `ops3d.get("signed_distance_field")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

occupancy/密度 voxel → 符号付き距離場 SDF(内側<0・外側>0)。edt_jfa を両側に。

SDF はマッチングに優れた表現(滑らか・勾配=法線・0 等値面=表面)。inside/outside の
ユークリッド距離差で作る。GPU native。voxel↔SDF↔occupancy を相互変換できる。

定義: ``occ = vol > iso`` として ``d_out = edt_jfa(occ)``(各 voxel から最寄りの占有 voxel
までの距離、占有内では 0)、``d_in = edt_jfa(~occ)``(最寄りの非占有 voxel まで)、
``sdf = d_out − d_in``。外側は +距離、内側は −距離(voxel 単位、ユークリッド)。
voxel 中心同士の距離なので **0 になる voxel は無く**、境界の占有 voxel は −1、隣接する
非占有 voxel は +1(0 等値面は voxel の間)。
``iso`` は密度→占有の閾値(既定 0.5。個数密度なら「1 点以上」)。全占有・全空の volume は
seed の無い側の距離が 1e6 に飽和し、全占有では −1e6、全空では +1e6 になる(例外は出ない)。
返り値 ``(D,H,W)`` float32 numpy。
後段: ``sdf_to_occupancy`` で戻す、``voxel_to_mesh(sdf, iso=0.0)`` で面、``sobel3d`` で法線場。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](../sdf_csg/sdf_union.md) · [sdf_intersect](../sdf_csg/sdf_intersect.md) · [sdf_subtract](../sdf_csg/sdf_subtract.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [tsdf_from_depth](tsdf_from_depth.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
