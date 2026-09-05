---
op: tb_lf_refocus
dim: 2d
category: typed
in: lightfield
out: image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# tb_lf_refocus — 2D `typed` op

- **データ種**: `lightfield` → `image`
- **呼び出し**: `fullseye.apply(img, "tb_lf_refocus", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Shift-and-add refocus: the synthetic-aperture image focused at *slope*.

    Every view ``(v, u)`` is shifted by ``(-s*(v - v_c), -s*(u - u_c))`` — the
    **minus** undoes the parallax of a point at slope ``s`` — and the shifted
    views are averaged. Points at that slope add coherently and stay sharp;
    everything else is smeared by an amount proportional to its slope
    difference times the angular baseline. ``slope=0`` is the plane the array
    was already focused on and returns the plain average of the views.

    Ground truth it reproduces exactly (pinned in ``tests/test_lightfield.py``):
    a single-layer field synthesised at slope ``s0`` and refocused at ``s0``
    with ``edge="wrap"`` and an integer ``s0`` returns the original texture to
    5.6e-16; sweeping the slope, the variance of the result peaks at ``s0``
    (measured exactly on the sweep grid in all 18 texture/slope combinations
    listed in the module docstring), and refocusing at ``-s0`` does *not* —
    which is the check that catches a flipped shift sign.

    Returns a ``(H, W)`` 2-D image.

    **Raises** ``ValueError``: *lf* not a valid light field, a non-finite or
    over-large *slope* (:data:`MAX_ABS_SLOPE`), unknown *interp* / *edge*.

Typed bridge of the lightfield op ``lf_refocus`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
