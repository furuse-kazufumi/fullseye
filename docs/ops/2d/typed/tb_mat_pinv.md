---
op: tb_mat_pinv
dim: 2d
category: typed
in: matrix
out: matrix
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# tb_mat_pinv — 2D `typed` op

- **データ種**: `matrix` → `matrix`
- **呼び出し**: `fullseye.apply(img, "tb_mat_pinv", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Moore-Penrose pseudo-inverse via SVD, with the cutoff **explicit**.

    Singular values below ``rcond * s_max`` are treated as zero — that cutoff
    *is* the regularisation, so it is a named, documented parameter here
    (default ``1e-12``) rather than a hidden library default: raising it
    discards noisy directions (stabler, more biased), lowering it keeps them
    (exact for well-conditioned *A*, explosive near rank deficiency).

    Works for any ``(m, n)``: ``pinv(A) @ b`` is the least-squares solution for
    ``m > n`` and the minimum-norm solution for ``m < n``.

    HALCON: no direct operator — HALCON reaches the same result through
    ``svd_matrix`` + reciprocal singular values.

Typed bridge of the math op ``mat_pinv`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. ``a`` drives ``rcond`` (default 1e-12); ``b`` is unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`matrix` を入力に取れる)

[identity](../misc/identity.md) · [tb_mat_cond](tb_mat_cond.md) · [tb_stat_covariance](tb_stat_covariance.md) · [tb_stat_correlation](tb_stat_correlation.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
