---
op: skeleton_endpoints3d
dim: 3d
category: medial
in: voxel
out: voxel
examples: [medial_topology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# skeleton_endpoints3d — 3D `medial` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import medial; medial.skeleton_endpoints3d(vol)` (または `ops3d.get("skeleton_endpoints3d")`)

## 使い方

3D 骨格の端点(26 近傍に骨格 voxel が 1 個以下)を voxel マスクで返す。

孤立 voxel(次数 0)も端点に数える。2D の `r2_endpoints_skeleton` の 3D 版。

手順: ``_ensure_skeleton`` で入力を bool 化し、6 近傍がすべて前景の interior voxel
があれば ``skeletonize_vol`` で細線化してから、3x3x3 全 1 カーネル(中心 0、
``mode="constant"`` で外側 0)の畳み込みで各 voxel の 26 近傍にある骨格 voxel 数
(次数)を数え、``skel & (次数 <= 1)`` を返す。volume の縁にある骨格 voxel は、
外側が 0 扱いなので枝がそこで途切れていれば端点になる。

返り値: 入力と同形の bool 配列(端点 = True)。前景が無ければ全 False。
``np.argwhere`` で ``(z, y, x)`` 座標に、``.sum()`` で端点数になる。

検証(``ValueError``): 3-D でない・空配列・float で NaN/Inf を含む入力。
細線化が必要で scikit-image が無い環境では ``ImportError``。

注意:
- 端点は各枝の末端で厳密だが、ヒゲ(細線化が作る短い枝)の先端も端点に数える。
  構造の端だけ欲しければ先に ``skeleton_prune3d`` で刈る。
- 閉ループだけの骨格(輪)は端点 0 個。
- 数だけ欲しいなら ``topology_signature`` が ``endpoints`` / ``isolated`` を
  分けて返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [medial_topology](../../../../examples_3d/medial_topology.py) — `py -3.11 examples_3d/medial_topology.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`medial`)

[distance_ridge](distance_ridge.md) · [skeletonize_vol](skeletonize_vol.md) · [medial_axis_points](medial_axis_points.md) · [topology_signature](topology_signature.md) · [medial_match](medial_match.md) · [skeleton_junctions3d](skeleton_junctions3d.md) · [skeleton_prune3d](skeleton_prune3d.md) · [skeleton_branches3d](skeleton_branches3d.md)

---
*Provenance: medial.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
