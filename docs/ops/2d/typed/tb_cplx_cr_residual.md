---
op: tb_cplx_cr_residual
dim: 2d
category: typed
in: cimage
out: feature
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tb_cplx_cr_residual — 2D `typed` op

- **データ種**: `cimage` → `feature`
- **呼び出し**: `fullseye.apply(img, "tb_cplx_cr_residual", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Cauchy-Riemann residual of a sampled complex field — "is this field
    holomorphic?" as a number.

    With ``f = u + i v`` sampled on a uniform grid, holomorphy means
    ``u_x = v_y`` and ``u_y = -v_x`` (Cauchy-Riemann). This returns the
    **relative** residual ``max(|u_x - v_y|, |u_y + v_x|) / max|grad|``
    (central differences, ``numpy.gradient``): ``0`` = the samples satisfy CR to
    the discretisation limit, ``2`` = the field is the conjugate of a
    holomorphic one (``conj(z)`` gives exactly 2), values in between = partly
    analytic or noisy.

    **Grid convention (it decides the sign of the answer)**: ``f[i, j]`` is the
    field at ``z = x0 + j*spacing + i*spacing*1j`` — rows index the *increasing
    imaginary* axis, columns the real axis. Image arrays usually run rows
    *downward*; feeding one directly measures the conjugate field, whose
    residual is ``2``, not ``0``. Flip rows (``f[::-1]``) to use image data.

    Discretisation, honestly: central differences are exact for polynomials of
    degree <= 2, so ``f = z**2`` returns exactly 0; for higher order the
    residual floors at ``O(h^2 * |f'''|)`` (measured: ``f = z**3`` on a
    ``[-1,1]^2`` grid returns 1.7e-3 at ``h`` and 4.2e-4 at
    ``h/2`` — a factor 4.00, the expected second order). Read a
    small value as "consistent with holomorphic at this resolution", never as
    proof.

    A constant field returns ``0.0`` (it is holomorphic; the ``0/0`` of the
    normalisation is resolved by that limit, and stated here rather than left
    to numpy).

    **Raises** ``ValueError``: not a 2-D array, either dimension below 3 (no
    central difference exists), non-finite/masked input, over-cap size,
    non-finite or non-positive *spacing*.

    HALCON: no operator (``derivate_gauss`` supplies the real-valued
    derivatives one would build this from).

Typed bridge of the math op ``cplx_cr_residual`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. ``a`` drives ``spacing`` (default 1); ``b`` is unused.

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
