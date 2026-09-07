---
op: distance_ridge
dim: 3d
category: medial
in: voxel
out: voxel
examples: [pcl_geodesic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# distance_ridge — 3D `medial` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.distance_ridge(vol, min_radius=0.0)` (実装を直接呼ぶなら `import medial; medial.distance_ridge(vol, min_radius=0.0)`、台帳から引くなら `ops3d.get("distance_ridge")`)
- **台帳経由の戻り値**: `fullseye.ledger.distance_ridge(...)` は**宣言 out 型 `voxel` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.distance_ridge.raw(...)`、または `medial.distance_ridge` を直接呼ぶ。
  - 本体の返り: `(ridge, dist)`

## 使い方

EDT のリッジ(距離場の局所極大)を medial として抽出。返り値 (ridge_mask, edt)。

各前景 voxel の EDT を計算し、**26 近傍の局所極大**(自分の EDT が周囲 26 voxel の最大以上)を
medial とみなす。この基準は物体の局所次元に応じて自然に次元を出し分ける:
    塊(球)  -> EDT が単峰 -> 点状の medial(中心 1 点)。
    管(円柱)-> 軸方向に平坦・半径方向に単峰 -> 線状の medial(軸線)。
    板(スラブ)-> 面内で平坦・厚み方向に単峰 -> 面状の medial(中心面)。
境界 voxel は内側の隣が必ず大きいため極大にならず、外殻は自然に除かれる。平坦な尾根
(軸/面)は同値の隣接を許容(>=)することで連続した線/面として残る。

Args:
    vol: バイナリ voxel(bool / 0-1 の 3D)。
    min_radius: この EDT 値以下の弱い尾根を捨てる閾値(既定 0 = 捨てない)。ノイズ抑制用。

Returns:
    ridge_mask (bool 3D): medial voxel。
    edt (float64 3D): 各 voxel の背景までのユークリッド距離(= 局所半径)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pcl_geodesic](../../../../examples_3d/pcl_geodesic.py) — `py -3.11 examples_3d/pcl_geodesic.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`medial`)

[skeletonize_vol](skeletonize_vol.md) · [medial_axis_points](medial_axis_points.md) · [topology_signature](topology_signature.md) · [medial_match](medial_match.md) · [skeleton_junctions3d](skeleton_junctions3d.md) · [skeleton_endpoints3d](skeleton_endpoints3d.md) · [skeleton_prune3d](skeleton_prune3d.md) · [skeleton_branches3d](skeleton_branches3d.md)

---
*Provenance: medial.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
