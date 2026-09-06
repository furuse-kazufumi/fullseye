---
op: match_points_ncc
dim: 3d
category: match_localize
in: points × points
out: position
gpu: true
examples: [matching_localize]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# match_points_ncc — 3D `match_localize` op

- **データ種**: `points × points` → `position`
- **呼び出し**: `import match3d; match3d.match_points_ncc(pts_scene, pts_model, size, bounds, device='cpu', smooth=0.8)` (または `ops3d.get("match_points_ncc")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

点群同士マッチング(構造=point cloud × 手法=NCC、変換=splat)。model を scene 内で定位。

手順: ``pts_scene`` と ``pts_model`` を **同じ** ``bounds=(lo,hi)`` と ``size`` で
``points_to_voxel``(σ=``smooth`` voxel の平滑つき)に通し、model 側は ``> 5%·max`` の bbox を
切り出してテンプレにし、``accel_match.ncc_locate_3d`` で NCC 定位する。
返り値 ``[NCC, z, y, x]`` float64(NCC ∈ [−1,1]、位置は voxel index、±2 近傍重心で
サブボクセル)。
- 位置は **切り出した bbox テンプレの中心**が scene voxel のどこに載るか。world 座標に戻すには
``lo + idx/(size−1)·(hi−lo)``(``points_to_voxel`` の格子)。
- ``bounds`` は必須(``_lo_hi`` で検証、不正は ValueError)。両雲を含む範囲にしないと範囲外の
点が端 voxel に clip される。
- model の voxel が全 0 なら ``[0,0,0,0]``。
- 並進のみ。回転・スケールは ``match_pca`` / ``match_logpolar_z`` で先に合わせる。
後段: ``icp_point2point_3d`` の ``init_t``、``refine_translation_lk``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [matching_localize](../../../../examples_3d/matching_localize.py) — `py -3.11 examples_3d/matching_localize.py`

## 型が繋がる次の op(`position` を入力に取れる)

[refine_peak_newton](../refine/refine_peak_newton.md) · [refine_translation_lk](../refine/refine_translation_lk.md) · [refine_lm](../refine/refine_lm.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`match_localize`)

[match_shape_3d](match_shape_3d.md) · [match_chamfer_3d](match_chamfer_3d.md) · [match_curvature_3d](match_curvature_3d.md) · [match_hough_3d](match_hough_3d.md) · [match_mip_2d](match_mip_2d.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
