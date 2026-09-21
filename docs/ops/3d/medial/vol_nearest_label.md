---
op: vol_nearest_label
dim: 3d
category: medial
in: voxel
out: voxel
examples: [nearest_seed_partition]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# vol_nearest_label — 3D `medial` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_nearest_label(vol_labels, spacing=None)` (実装を直接呼ぶなら `import volops; volops.vol_nearest_label(vol_labels, spacing=None)`、台帳から引くなら `ops3d.get("vol_nearest_label")`)

## 使い方

零 voxel に**最近の非零ラベル**を配ったラベル体積 ``(D, H, W)``(ラベルのボロノイ分割、``voxel``)。

入力は整数ラベル(``vol_label`` / ``vol_rle_components`` の出力、0 = 未割当)。各 0 voxel は物理距離(``spacing``)で
最も近い非零 voxel のラベルを受け取り、非零 voxel はそのまま。EM の分割片や骨格の枝ラベルから「その枝が支配する
体積」を切り出す(枝ごとの体積・肉厚)のに使う。非整数のラベルは拒否(丸めて別のラベルにしない)、非零が 1 つも
無ければ ValueError。返りは int64。

>>> L = np.zeros((1, 1, 7)); L[0, 0, 0] = 1; L[0, 0, 6] = 2
>>> vol_nearest_label(L)[0, 0].tolist()
[1, 1, 1, 1, 2, 2, 2]

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [nearest_seed_partition](../../../../examples_3d/nearest_seed_partition.py) — `py -3.11 examples_3d/nearest_seed_partition.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`medial`)

[distance_ridge](distance_ridge.md) · [skeletonize_vol](skeletonize_vol.md) · [medial_axis_points](medial_axis_points.md) · [topology_signature](topology_signature.md) · [medial_match](medial_match.md) · [skeleton_junctions3d](skeleton_junctions3d.md) · [skeleton_endpoints3d](skeleton_endpoints3d.md) · [skeleton_prune3d](skeleton_prune3d.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
