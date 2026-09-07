---
op: skeleton_prune3d
dim: 3d
category: medial
in: voxel
out: voxel
examples: [medial_topology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# skeleton_prune3d — 3D `medial` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.skeleton_prune3d(vol, length=1)` (実装を直接呼ぶなら `import medial; medial.skeleton_prune3d(vol, length=1)`、台帳から引くなら `ops3d.get("skeleton_prune3d")`)

## 使い方

3D 骨格のヒゲ(短い枝)を刈る。端点除去を length 回反復 = 枝長 <=length を除去。

2D の `pruning` の 3D 版。孤立 voxel は端点扱いで消える。

手順: ``_ensure_skeleton`` で bool 化(interior voxel があれば ``skeletonize_vol``
で細線化)し、次を ``length`` 回繰り返す — 26 近傍次数 ``<= 1`` の voxel(端点と
孤立点)をすべて同時に取り除く。骨格が空になるか端点が無くなれば(閉ループ
だけになれば)途中で止まる。

引数: ``length`` は ``int(length)`` にして負なら 0 に丸める(0 なら細線化した
骨格をそのまま返す)。1 回の反復で各枝の先端 1 voxel が消えるので、
長さ ``<= length`` voxel の枝(ヒゲ)は根元まで消える。

返り値: 入力と同形の bool 配列。

注意(挙動として知っておくこと):
- **長い枝も先端から ``length`` voxel 短くなる**(ヒゲだけを選んで消す処理では
  ない)。主枝の端点位置が要るなら、刈った後の端点は元より ``length`` 内側に
  ある。
- 2 分岐の間の短い枝は両端が分岐点(次数 >= 3)なので消えない。
- 孤立 voxel は 1 回目で消える。
- 反復のたびに次数を数え直すので、コストは ``length`` に比例する。

検証(``ValueError``): 3-D でない・空配列・NaN/Inf を含む入力。細線化が必要で
scikit-image が無ければ ``ImportError``。後段は ``skeleton_endpoints3d`` /
``skeleton_junctions3d`` / ``skeleton_branches3d`` / ``topology_signature``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [medial_topology](../../../../examples_3d/medial_topology.py) — `py -3.11 examples_3d/medial_topology.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`medial`)

[distance_ridge](distance_ridge.md) · [skeletonize_vol](skeletonize_vol.md) · [medial_axis_points](medial_axis_points.md) · [topology_signature](topology_signature.md) · [medial_match](medial_match.md) · [skeleton_junctions3d](skeleton_junctions3d.md) · [skeleton_endpoints3d](skeleton_endpoints3d.md) · [skeleton_branches3d](skeleton_branches3d.md)

---
*Provenance: medial.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
