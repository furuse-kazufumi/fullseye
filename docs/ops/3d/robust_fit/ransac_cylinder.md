---
op: ransac_cylinder
dim: 3d
category: robust_fit
in: points × normals
out: primitive
examples: [ransac_prim]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# ransac_cylinder — 3D `robust_fit` op

- **データ種**: `points × normals` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.ransac_cylinder(points, normals, thresh, iters=800, seed=0)` (実装を直接呼ぶなら `import ransac_fit; ransac_fit.ransac_cylinder(points, normals, thresh, iters=800, seed=0)`、台帳から引くなら `ops3d.get("ransac_cylinder")`)

## 使い方

外れ値に頑健な RANSAC 円筒適合(点法線が必要)。

円筒表面の法線は軸に直交するので、2 点の法線の外積で軸方向を推定 → 軸に直交な平面へ
全点を投影 → その平面内で円をフィット → |投影距離 - r| < ``thresh`` の inlier を
最大化。最終 inlier ではより頑健に軸を再推定(法線群の SVD の最小特異方向 = 軸)し、
投影円を最小二乗リフィットする。法線が無ければ呼び出し側で estimate してから渡す。

Args:
    points: (N,3) 点群。
    normals: (N,3) 各点の(単位)法線。
    thresh: inlier とみなす |投影距離-r| のしきい値。
    iters: RANSAC 反復数。
    seed: 乱数シード(決定論)。

Returns:
    (params, inlier_mask, info)。params = {"axis": (3,) 単位軸, "point": (3,) 軸上の一点,
    "radius": float}。info には inlier 数 ``n_inliers`` / 比 ``inlier_ratio`` / ``iters``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ransac_prim](../../../../examples_3d/ransac_prim.py) — `py -3.11 examples_3d/ransac_prim.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [distance_segment_segment](../geometry/distance_segment_segment.md)

## 同カテゴリ(`robust_fit`)

[ransac_plane](ransac_plane.md) · [ransac_sphere](ransac_sphere.md) · [ransac_line](ransac_line.md) · [fit_cone](fit_cone.md) · [fit_torus](fit_torus.md) · [fit_ellipsoid](fit_ellipsoid.md)

---
*Provenance: ransac_fit.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
