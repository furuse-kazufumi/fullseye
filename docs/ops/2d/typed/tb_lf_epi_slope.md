---
op: tb_lf_epi_slope
dim: 2d
category: typed
in: lightfield
out: image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# tb_lf_epi_slope — 2D `typed` op

- **データ種**: `lightfield` → `image`
- **呼び出し**: `fullseye.apply(img, "tb_lf_epi_slope", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Per-pixel slope from the **EPI line orientation** (structure tensor, one pass).

    A scene point traces a straight line in the epipolar-plane image
    (:func:`lf_epi`), so along that line the intensity is constant:
    ``E_u + s * E_x = 0``. Accumulating that constraint over the whole angular
    grid and a ``window x window`` spatial neighbourhood gives the closed-form
    least-squares slope ``s = -(J_ux + J_vy) / (J_xx + J_yy)`` with
    ``J_ab = sum(E_a * E_b)`` — one pass over the light field, no sweep, both
    the horizontal and vertical EPI directions pooled.

    **This estimator is biased, and the bias is the reason to also run**
    :func:`lf_depth_from_focus`. It is ordinary (not total) least squares on
    finite differences, so it needs the EPI line to advance less than roughly
    one texture correlation length per view. Measured 2026-09-01 on
    5x5x64x64 synthetic fields, median over the interior: with texture
    ``sigma = 1.5`` px, true ``+1.00 -> +1.0004``, ``+0.50 -> +0.5285``,
    ``+1.50 -> +1.3018``, ``+2.00 -> +1.4614``; with ``sigma = 5.0`` px the same
    slopes give ``+1.0003``, ``+0.5029``, ``+1.4827``, ``+1.9482``. Integer
    slopes on a wrapped field come back within 4e-4 and ``s = 0`` is exact;
    ``|s| > 1`` is under-estimated, by 27% at ``s = 2`` on the roughest texture.
    Use it as a fast dense initialiser, not as the final word.

    Returns ``(slope_map, energy)``: the ``(H, W)`` slope map and the ``(H, W)``
    gradient energy ``J_xx + J_yy`` that was the denominator. Pixels whose
    energy is below *min_energy* have **no** measurable parallax (a flat patch
    of sky); their slope is set to 0 and their energy reported as-is, so you
    threshold on ``energy`` instead of being handed a plausible-looking number
    divided by ~0.

    **Raises** ``ValueError``: *lf* not a valid light field, an angular/spatial
    shape where *neither* EPI direction carries information (the horizontal EPI
    needs ``U >= 2`` **and** ``W >= 2``, the vertical needs ``V >= 2`` and
    ``H >= 2``), an even or non-positive *window*, a non-positive *min_energy*.

Typed bridge of the lightfield op ``lf_epi_slope`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

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
