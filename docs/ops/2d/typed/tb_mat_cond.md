---
op: tb_mat_cond
dim: 2d
category: typed
in: matrix
out: feature
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tb_mat_cond — 2D `typed` op

- **データ種**: `matrix` → `feature`
- **呼び出し**: `fullseye.apply(img, "tb_mat_cond", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Spectral (2-norm) condition number ``s_max / s_min`` — the numerical
    canary of the whole linalg family.

    ``cond == 1`` for an orthogonal/orthonormal matrix (the best possible);
    ``inf`` (returned, not raised — the question "how conditioned is it?" has
    that honest answer) for an exactly singular one. A solve against *A* loses
    roughly ``log10(cond(A))`` significant digits (Golub & Van Loan §2.6):

      * ``cond ~ 1e3``  — comfortable, ~13 digits survive.
      * ``cond ~ 1e8``  — half the digits are gone; residuals may still look
        small while parameters are off.
      * ``cond > 1e12`` — **do not trust** :func:`mat_solve` here: at best ~3
        digits remain. Rescale/centre the problem, or switch to
        :func:`mat_lstsq` / :func:`mat_pinv` with an honest ``rcond``.

    Defined for any rectangular ``(m, n)`` matrix (via its singular values).
    HALCON: no direct operator (combine ``norm_matrix`` of *A* and of its
    inverse).

Typed bridge of the math op ``mat_cond`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
