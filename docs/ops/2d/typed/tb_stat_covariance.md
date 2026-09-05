---
op: tb_stat_covariance
dim: 2d
category: typed
in: matrix
out: matrix
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tb_stat_covariance — 2D `typed` op

- **データ種**: `matrix` → `matrix`
- **呼び出し**: `fullseye.apply(img, "tb_stat_covariance", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Sample covariance matrix of ``(N, D)`` observations → ``(D, D)``.

    Rows are observations, columns are variables — the ``(N, D)`` orientation
    every Fullseye point/sample API uses (note ``np.cov`` defaults to the
    *transposed* convention). Uses the unbiased ``ddof=1`` estimator (divides
    by ``N - 1``), hence the ``N >= 2`` requirement. The diagonal holds the
    per-variable sample variances; the result is symmetric positive
    semi-definite by construction, so it can go straight into
    :func:`mat_eigh` for principal axes (the covariance-ellipse workflow).

    HALCON: no public tuple/matrix operator — covariance lives inside HALCON's
    calibration and matching internals only.

Typed bridge of the math op ``stat_covariance`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`matrix` を入力に取れる)

[identity](../misc/identity.md) · [tb_mat_pinv](tb_mat_pinv.md) · [tb_mat_cond](tb_mat_cond.md) · [tb_stat_correlation](tb_stat_correlation.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
