---
op: skeleton_junctions3d
dim: 3d
category: medial
in: voxel
out: voxel
examples: [medial_topology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# skeleton_junctions3d — 3D `medial` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import medial; medial.skeleton_junctions3d(vol)` (または `ops3d.get("skeleton_junctions3d")`)

## 使い方

3D 骨格の分岐点(joint、26 近傍に骨格 voxel が 3 個以上)を voxel マスクで返す。

骨格でない入力(interior を持つ塊)は skeletonize_vol で細線化してから測る。
2D の `junctions_skeleton` の 3D 版。血管・多孔質・ネットワーク状構造の
グラフ化(node 抽出)に使う。分岐次数の集計だけ欲しい場合は
topology_signature が dict で返す。

注意(honest): 26 近傍次数は分岐近傍の対角隣接で過大に出うる(離散骨格の
既知の性質)。分岐 *個数* を数えるときはこのマスクを連結成分でまとめること。

手順: ``_ensure_skeleton`` — 入力を bool 化し、6 近傍(面隣接)がすべて前景の
interior voxel が 1 つでもあれば「骨格ではない」とみなして ``skeletonize_vol``
(skimage Lee 法)を先に掛ける。その後、3x3x3 の全 1 カーネル(中心 0)の畳み込み
(``mode="constant"``、外側は 0)で各 voxel の 26 近傍にある骨格 voxel 数(次数)を
数え、``skel & (次数 >= 3)`` を返す。

返り値: 入力と同形の bool 配列。前景が無ければ全 False。骨格 voxel 以外は
必ず False。座標は ``np.argwhere`` で ``(z, y, x)`` 順に取れる。

検証(``ValueError``): 3-D でない・空配列・float で NaN/Inf を含む入力。
scikit-image が無い環境で細線化が必要になると ``ImportError``。

注意: 既に骨格の入力でも interior 判定は毎回走る(細い骨格なら細線化は
skip される)。個数を数えるなら ``vol_label(mask, 26)`` の成分数を使う。
枝に分けるのは ``skeleton_branches3d``、端点は ``skeleton_endpoints3d``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [medial_topology](../../../../examples_3d/medial_topology.py) — `py -3.11 examples_3d/medial_topology.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`medial`)

[distance_ridge](distance_ridge.md) · [skeletonize_vol](skeletonize_vol.md) · [medial_axis_points](medial_axis_points.md) · [topology_signature](topology_signature.md) · [medial_match](medial_match.md) · [skeleton_endpoints3d](skeleton_endpoints3d.md) · [skeleton_prune3d](skeleton_prune3d.md) · [skeleton_branches3d](skeleton_branches3d.md)

---
*Provenance: medial.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
