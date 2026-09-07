---
op: skeleton_branches3d
dim: 3d
category: medial
in: voxel
out: voxel
examples: [medial_topology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# skeleton_branches3d — 3D `medial` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.skeleton_branches3d(vol, min_length=0)` (実装を直接呼ぶなら `import medial; medial.skeleton_branches3d(vol, min_length=0)`、台帳から引くなら `ops3d.get("skeleton_branches3d")`)

## 使い方

3D 骨格を分岐点で切って枝(線分)に分割する。2D の `r2_split_skeleton_lines` の 3D 版。

分岐点 voxel を除いた残りが枝。min_length > 0 なら、26 連結成分の voxel 数が
それ未満の断片を除去する。

手順: ``_ensure_skeleton`` で bool 化(interior voxel があれば ``skeletonize_vol``
で細線化)→ 26 近傍次数 ``>= 3`` の voxel(分岐点)を取り除く → ``min_length > 0``
なら ``scipy.ndimage.label``(3x3x3 全 1 構造 = 26 連結)で成分に分け、voxel 数が
``min_length`` 未満の成分を落とす。

返り値: 入力と同形の bool 配列(枝 voxel = True)。**枝ごとのラベルは返さない**
— 枝を個別に扱うには返り値を ``vol_label(branches, 26)`` に通す(成分数 = 枝数)。
分岐点 voxel そのものは結果に含まれないので、枝の両端は分岐点の 1 voxel 手前で
終わる。

引数と検証: ``min_length`` は voxel 数(``int()`` で切り捨て。0 なら除去しない)。
入力が 3-D でない・空・NaN/Inf は ``ValueError``。細線化が必要で
scikit-image が無ければ ``ImportError``。前景が無ければ全 False。

注意: 26 近傍次数は分岐の対角隣接で 3 以上になりやすく、分岐点が数 voxel の
塊として除かれるため、枝が実際より短く出ることがある。閉ループだけの骨格は
分岐点が無く、全体が 1 本の枝として残る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [medial_topology](../../../../examples_3d/medial_topology.py) — `py -3.11 examples_3d/medial_topology.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`medial`)

[distance_ridge](distance_ridge.md) · [skeletonize_vol](skeletonize_vol.md) · [medial_axis_points](medial_axis_points.md) · [topology_signature](topology_signature.md) · [medial_match](medial_match.md) · [skeleton_junctions3d](skeleton_junctions3d.md) · [skeleton_endpoints3d](skeleton_endpoints3d.md) · [skeleton_prune3d](skeleton_prune3d.md)

---
*Provenance: medial.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
