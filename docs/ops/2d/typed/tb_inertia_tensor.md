---
op: tb_inertia_tensor
dim: 2d
category: typed
in: points
out: matrix
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tb_inertia_tensor — 2D `typed` op

- **データ種**: `points` → `matrix`
- **呼び出し**: `fullseye.apply(img, "tb_inertia_tensor", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

点群の慣性テンソル (3,3)(中心 2 次モーメントから、等質量・総質量 1)。

    I_xx = mean(y²+z²), I_yy = mean(x²+z²), I_zz = mean(x²+y²),
    I_xy = -mean(xy), I_xz = -mean(xz), I_yz = -mean(yz)。
    共分散 C を使うと I = tr(C)·E₃ − C(E₃ は単位行列)と等価。対称・半正定値。
    重心中心化のため並進不変。

    Returns
    -------
    np.ndarray, shape (3, 3)
        対称な慣性テンソル。

2-D 進化レジストリへ橋渡しした 3d の op ``inertia_tensor``。実装は同じで、呼び出し規約だけ ``op(v, a, b)`` に合わせてある。この op に調整点は無く、``a`` も ``b`` も使われない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`matrix` を入力に取れる)

[identity](../misc/identity.md) · [tb_mat_pinv](tb_mat_pinv.md) · [tb_mat_cond](tb_mat_cond.md) · [tb_stat_covariance](tb_stat_covariance.md) · [tb_stat_correlation](tb_stat_correlation.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
