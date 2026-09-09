---
op: ransac_sphere
dim: 3d
category: robust_fit
in: points
out: primitive
examples: [ransac_prim]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# ransac_sphere — 3D `robust_fit` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.ransac_sphere(points, thresh, iters=500, seed=0)` (実装を直接呼ぶなら `import ransac_fit; ransac_fit.ransac_sphere(points, thresh, iters=500, seed=0)`、台帳から引くなら `ops3d.get("ransac_sphere")`)

## 使い方

外れ値に頑健な RANSAC 球適合。

4 点をサンプル → 線形法(代数フィット)で球中心・半径 → |‖p-c‖ - r| < ``thresh`` の
inlier を最大化 → 最終 inlier で最小二乗リフィット。配管ボール/球面計測用。

Args:
    points: (N,3) 点群。
    thresh: inlier とみなす |距離-r| のしきい値。
    iters: RANSAC 反復数。
    seed: 乱数シード(決定論)。

Returns:
    (params, inlier_mask, info)。params = {"center": (3,), "radius": float}。

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

[ransac_plane](ransac_plane.md) · [ransac_line](ransac_line.md) · [ransac_cylinder](ransac_cylinder.md) · [fit_cone](fit_cone.md) · [fit_torus](fit_torus.md) · [fit_ellipsoid](fit_ellipsoid.md)

---
*Provenance: ransac_fit.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
