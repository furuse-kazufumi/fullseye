---
op: tsdf_from_depth
dim: 3d
category: transform
in: depth
out: sdf
examples: [transforms_repr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# tsdf_from_depth — 3D `transform` op

- **データ種**: `depth` → `sdf`
- **呼び出し**: `import fullseye as fs; fs.ledger.tsdf_from_depth(depth, fx, fy, cx, cy, size=64, bounds=None, trunc=3.0)` (実装を直接呼ぶなら `import match3d; match3d.tsdf_from_depth(depth, fx, fy, cx, cy, size=64, bounds=None, trunc=3.0)`、台帳から引くなら `ops3d.get("tsdf_from_depth")`)

## 使い方

深度マップ(2.5D)→ TSDF volume(RGB-D 再構成の標準表現)。depth→TSDF 変換。

各 voxel を画像へ投影し、視線上の観測深度との符号付き切詰め距離 [-1,1] を格納
(表面手前 +・奥 −・表面 0)。KinectFusion 系の基本表現。

格子: ``bounds=(lo, hi)`` は **(X, Y, Z) のカメラ座標**(``depth_to_points`` と同じ)で、
None なら深度を逆投影した点群の min−2 / max+2(深度の単位)。出力は ``(size,size,size)``
float32 で **軸順は (Z, Y, X)**、voxel 中心 ``= lo + (i + 0.5)/size·(hi − lo)``。
bounds の並び (x,y,z) と配列の軸 (z,y,x) が逆なことに注意。

値: 各 voxel 中心を ``u = X·fx/Z + cx``、``v = Y·fy/Z + cy`` で画素へ丸め、その画素の観測深度
``d`` から ``clip((d − Z)/trunc, −1, 1)``(``trunc`` は深度と同じ単位)。画像外に落ちる
voxel・観測深度が 0 以下・Z が 0 以下の voxel は **+1(未観測=自由)** にする(端画素へ
clip して観測済みに見せかけない)。深度 0 が無効値の規約。

- 深度が全て 0 で bounds=None だと点群が空になり numpy の min で例外。
- 1 視点の TSDF なので視線の裏側は −1 で埋まる(閉じた物体にはならない)。
後段: ``voxel_to_mesh(tsdf, iso=0.0)`` で面を取る。占有にするなら ``sdf_to_occupancy``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](../sdf_csg/sdf_union.md) · [sdf_intersect](../sdf_csg/sdf_intersect.md) · [sdf_subtract](../sdf_csg/sdf_subtract.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [signed_distance_field](signed_distance_field.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
