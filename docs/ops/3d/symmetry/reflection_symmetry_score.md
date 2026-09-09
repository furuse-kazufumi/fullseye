---
op: reflection_symmetry_score
dim: 3d
category: symmetry
in: points
out: measurement
examples: [dl_mesh_symmetry, reflection_symmetry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# reflection_symmetry_score — 3D `symmetry` op

- **データ種**: `points` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.reflection_symmetry_score(points, plane_point, plane_normal)` (実装を直接呼ぶなら `import symmetry3d; symmetry3d.reflection_symmetry_score(points, plane_point, plane_normal)`、台帳から引くなら `ops3d.get("reflection_symmetry_score")`)

## 使い方

反射対称スコア = chamfer(鏡映, 元) / 中央値最近傍間隔(小さいほど対称、スケール不変)。→ float。

``reflect_points`` で点群を平面で鏡映し、元の点群との対称 Chamfer 距離(``chamfer_distance``:
双方向の最近傍距離の平均の平均)を、元の点群の最近傍間隔の中央値で割る。「鏡像が元の点から
点間隔の何倍ずれているか」という無次元量なので、座標を定数倍しても値は変わらない。

- ``points``: (N,3) 点群。``plane_point`` / ``plane_normal``: 候補平面(法線は内部で正規化)。
- fail-closed: 点群が空・(N,3) でない(``chamfer_distance`` が ``ValueError``)、全点が一致して
  間隔が定義できない(``ValueError``)。重複点で中央値間隔が 0 になる場合だけ、重心からの RMS
  半径 × 1e-12 を床にする。

読み方の注意: 厳密に対称な形でも、鏡像の点が元のサンプル点にぴったり重なるわけではないので
スコアは 0 にならず、点間隔程度が床になる(実測値は ``detect_reflection_symmetry`` の表を参照)。
閾値で採否を決めるより、複数候補を掃引して最小値と 2 位との差(``margin``)を見る。PCA の
3 軸以外の候補面を試したいときは、この関数を平面パラメータで直接掃引する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dl_mesh_symmetry](../../../../examples_3d/dl_mesh_symmetry.py) — `py -3.11 examples_3d/dl_mesh_symmetry.py`
- [reflection_symmetry](../../../../examples_3d/reflection_symmetry.py) — `py -3.11 examples_3d/reflection_symmetry.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`symmetry`)

[detect_reflection_symmetry](detect_reflection_symmetry.md) · [detect_rotational_symmetry](detect_rotational_symmetry.md) · [reflect_points](reflect_points.md)

---
*Provenance: symmetry3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
