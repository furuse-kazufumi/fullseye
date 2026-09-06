---
op: medial_match
dim: 3d
category: medial
in: voxel × voxel
out: measurement
examples: [medial_topology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# medial_match — 3D `medial` op

- **データ種**: `voxel × voxel` → `measurement`
- **呼び出し**: `import medial; medial.medial_match(vol_a, vol_b, w_topology=0.6, w_radius=0.4, n_bins=12)` (または `ops3d.get("medial_match")`)

## 使い方

2 つの voxel 形状の medial(位相 + 半径分布)による粗照合スコア。返り値 [0,1]。

骨格の位相記述子(端点/分岐/通常/孤立の割合)の距離と、medial 半径分布(内接半径の
ヒストグラム)の距離を重み付き合成し、類似度 = 1 - 距離 として返す。1 に近いほど似ている。
平行移動・回転(90 度)に対して概ね不変で、位相ベースの初期照合(粗いふるい)に使う。

Args:
    vol_a, vol_b: バイナリ voxel(bool / 0-1 の 3D)。
    w_topology: 位相距離の重み(既定 0.6)。
    w_radius: 半径分布距離の重み(既定 0.4)。
    n_bins: 半径ヒストグラムの bin 数。

Returns:
    float: 類似スコア [0,1] (大きいほど類似)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [medial_topology](../../../../examples_3d/medial_topology.py) — `py -3.11 examples_3d/medial_topology.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`medial`)

[distance_ridge](distance_ridge.md) · [skeletonize_vol](skeletonize_vol.md) · [medial_axis_points](medial_axis_points.md) · [topology_signature](topology_signature.md) · [skeleton_junctions3d](skeleton_junctions3d.md) · [skeleton_endpoints3d](skeleton_endpoints3d.md) · [skeleton_prune3d](skeleton_prune3d.md) · [skeleton_branches3d](skeleton_branches3d.md)

---
*Provenance: medial.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
