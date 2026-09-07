---
op: inflate
dim: 3d
category: occupancy
in: voxel
out: voxel
examples: [sensor_seg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# inflate — 3D `occupancy` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.inflate(occupancy, radius, voxel_size=1.0)` (実装を直接呼ぶなら `import occupancy; occupancy.inflate(occupancy, radius, voxel_size=1.0)`、台帳から引くなら `ops3d.get("inflate")`)

## 使い方

障害物を ``radius``(world 単位)膨張した占有格子 bool(= ESDF<=radius を占有)。

planner の安全マージン: 点ロボットが膨張格子上で衝突回避すれば、半径 radius の実
ロボットが障害物から離隔を保つ(configuration-space obstacle)。ESDF は外で正の
最近占有距離なので、``ESDF<=radius`` は「占有(負)∪ 障害物から radius 以内の自由」を
捕らえる。radius を増やすと単調に占有が増える(下流テストの GT)。

Raises ValueError for radius<0 or voxel_size<=0 (both validated up-front, before
the radius==0 / empty-occupancy short-circuit — otherwise an invalid voxel_size
slips through unchecked when esdf is never reached).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sensor_seg](../../../../examples_3d/sensor_seg.py) — `py -3.11 examples_3d/sensor_seg.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`occupancy`)

[occupancy_grid](occupancy_grid.md) · [esdf](esdf.md) · [query_distance](query_distance.md)

---
*Provenance: occupancy.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
