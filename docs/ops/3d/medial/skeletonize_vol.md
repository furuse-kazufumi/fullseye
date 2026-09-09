---
op: skeletonize_vol
dim: 3d
category: medial
in: voxel
out: voxel
examples: [medial_topology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# skeletonize_vol — 3D `medial` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.skeletonize_vol(vol)` (実装を直接呼ぶなら `import medial; medial.skeletonize_vol(vol)`、台帳から引くなら `ops3d.get("skeletonize_vol")`)

## 使い方

3D バイナリ voxel を細線化して 1 voxel 幅の骨格に。skimage の Lee(1994)法ラッパ。

method='lee' は 3D 対応の位相保存細線化。塊も含めて線状の骨格へ潰す(medial *surface* が
欲しい場合は distance_ridge を使う)。返り値は入力と同形の bool 配列。

Args:
    vol: バイナリ voxel(bool / 0-1 の 3D)。

Returns:
    skeleton (bool 3D): 骨格 voxel。

入力の扱い: ``_as_binary_volume`` が 3-D 配列を bool に正規化する(非ゼロ = 前景)。
3-D でない・空配列・float で NaN/Inf を含む場合は ``ValueError``。軸順は
``(z, y, x)``、距離・太さは voxel 単位で、等方サンプリングを仮定する(異方
voxel のままだと細線化の結果が軸ごとに偏る。先に ``vol_resize`` で等方化する)。

挙動:
- 前景が無ければ全 False の同形配列を返す(skimage は呼ばない)。
- ``skimage.morphology.skeletonize(mask, method="lee")`` は遅延 import。
  scikit-image が無い環境ではここで ``ImportError`` になる。
- Lee 法は位相を保つ(連結成分数・穴・空洞を変えない)が、太い塊は複数の枝に
  潰れ、表面の凹凸に応じたヒゲ(短い枝)が出る。ヒゲは ``skeleton_prune3d`` で
  刈る。

使いどころ: ``topology_signature``(端点・分岐の数)、``skeleton_junctions3d`` /
``skeleton_endpoints3d`` / ``skeleton_branches3d`` の入力。骨格 voxel の局所
半径が要るなら ``distance_ridge`` の ``edt`` を骨格位置で引く。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [medial_topology](../../../../examples_3d/medial_topology.py) — `py -3.11 examples_3d/medial_topology.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`medial`)

[distance_ridge](distance_ridge.md) · [medial_axis_points](medial_axis_points.md) · [topology_signature](topology_signature.md) · [medial_match](medial_match.md) · [skeleton_junctions3d](skeleton_junctions3d.md) · [skeleton_endpoints3d](skeleton_endpoints3d.md) · [skeleton_prune3d](skeleton_prune3d.md) · [skeleton_branches3d](skeleton_branches3d.md)

---
*Provenance: medial.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
