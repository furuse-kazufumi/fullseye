---
op: points_to_voxel
dim: 3d
category: transform
in: points
out: voxel
gpu: true
examples: [sh_descriptor_retrieval, shape_desc_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# points_to_voxel — 3D `transform` op

- **データ種**: `points` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.points_to_voxel(points, size, bounds=None, device='cpu', smooth=0.0)` (実装を直接呼ぶなら `import match3d; match3d.points_to_voxel(points, size, bounds=None, device='cpu', smooth=0.0)`、台帳から引くなら `ops3d.get("points_to_voxel")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

点群 (N,3) → 密度 voxel (size³)。scatter_add で splat、任意で gaussian 平滑。

bounds=(lo,hi) を与えれば複数雲を同一格子に載せられる(=マッチング前提)。

手順: 各点を ``idx = floor((p − lo)/(hi − lo)·(size − 1))`` で整数格子に落とし、その voxel に
1 を加算する(値 = その voxel に落ちた点の個数)。``smooth > 0`` なら σ=``smooth``(voxel 単位)
の gaussian を 3 軸分離 conv で掛ける(半径 ``max(1, int(4σ + 0.5))``、端は replicate)。
出力の軸順は **点の列の順そのまま**(``points[:, 0]`` → 軸 0)で、(depth,row,col) への
並べ替えはしない。

- ``bounds``: ``(lo, hi)`` の 3 次元ベクトル 2 本。None なら点群自身の min/max(雲ごとに
格子が変わるので、2 つの雲を比べるときは必ず同じ bounds を渡す)。長さ 3 でない・非有限・
``hi <= lo`` の軸があると ValueError(tsdf 系の ``((xmin,xmax),...)`` 流儀は長さ 2 として拒否)。
- 範囲外の点は捨てずに **端の voxel へ clip される**(端に偽の密度が溜まる)。切り落としたい
なら事前に点群側で除く。
- ``size``: 一辺の voxel 数。``hi − lo`` が 0 の軸は 1e-9 に置換されるだけで警告しない。
- 空の点群で bounds=None は numpy の min が例外を出す。
- 返り値: ``(size, size, size)`` float64 numpy(device で計算しても CPU に戻す)。値は個数
(平滑後は個数の重み分布)で正規化はしない。

後段: ``match_points_ncc`` / ``signed_distance_field`` / ``voxel_to_mesh`` の入力に。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sh_descriptor_retrieval](../../../../examples_3d/sh_descriptor_retrieval.py) — `py -3.11 examples_3d/sh_descriptor_retrieval.py`
- [shape_desc_pose](../../../../examples_3d/shape_desc_pose.py) — `py -3.11 examples_3d/shape_desc_pose.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [signed_distance_field](signed_distance_field.md) · [to_points](to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`transform`)

[gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [tsdf_from_depth](tsdf_from_depth.md) · [signed_distance_field](signed_distance_field.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
