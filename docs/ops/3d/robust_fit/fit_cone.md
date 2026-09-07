---
op: fit_cone
dim: 3d
category: robust_fit
in: points
out: primitive
examples: [fit_primitives_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fit_cone — 3D `robust_fit` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_cone(points) -> 'dict'` (実装を直接呼ぶなら `import fit_primitives_ext; fit_primitives_ext.fit_cone(points) -> 'dict'`、台帳から引くなら `ops3d.get("fit_cone")`)

## 使い方

点群に無限円錐を当てはめ ``{apex, axis, half_angle, residual}`` を返す。

子午面での点-母線直交距離 ``a·sinα − ρ·cosα``(``a``=軸成分, ``ρ``=半径,
``α``=半角)を ``scipy.optimize.least_squares`` で最小化する。初期値は PCA 軸 +
半径 ρ の軸成分 t に対する線形回帰(``ρ = m·t + b`` の傾き m=tanα, 切片ゼロ点=頂点)。
軸の向きは「頂点から離れるほど ρ が増える(+方向に開く)」に正規化する。

Args:
    points: (N,3) 点群(最低 6 点)。

Returns:
    dict: ``{"apex": (3,), "axis": (3,) 単位軸(開く向き), "half_angle": float [rad],
    "residual": float 点-面距離の RMS}``。

Raises:
    ValueError: 形状不正/点数不足/半角 ~0(円柱へ縮退)など fail-closed。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fit_primitives_ext](../../../../examples_3d/fit_primitives_ext.py) — `py -3.11 examples_3d/fit_primitives_ext.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [distance_segment_segment](../geometry/distance_segment_segment.md)

## 同カテゴリ(`robust_fit`)

[ransac_plane](ransac_plane.md) · [ransac_sphere](ransac_sphere.md) · [ransac_line](ransac_line.md) · [ransac_cylinder](ransac_cylinder.md) · [fit_torus](fit_torus.md) · [fit_ellipsoid](fit_ellipsoid.md)

---
*Provenance: fit_primitives_ext.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
