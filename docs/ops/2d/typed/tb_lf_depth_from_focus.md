---
op: tb_lf_depth_from_focus
dim: 2d
category: typed
in: lightfield
out: image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# tb_lf_depth_from_focus — 2D `typed` op

- **データ種**: `lightfield` → `image`
- **呼び出し**: `fullseye.apply(img, "tb_lf_depth_from_focus", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Per-pixel slope from the **sharpness peak** across the refocus sweep.

    Refocus at every slope in *slopes*, measure local sharpness (*measure*:
    ``laplacian`` = summed modified Laplacian, the classical depth-from-focus
    operator; ``variance`` = local variance; ``gradient`` = local gradient
    energy) in a ``window x window`` neighbourhood, and take the slope at which
    each pixel is sharpest. With ``subpixel=True`` (default) the peak is refined
    by fitting a parabola through the winning sample and its two neighbours on a
    **uniformly** spaced sweep — on a non-uniform sweep the refinement is
    skipped rather than applied with the wrong spacing.

    Unbiased where :func:`lf_epi_slope` is not: measured 2026-09-01 on a
    5x5x64x64 synthetic field over a 121-point sweep from -3 to +3, the argmax
    landed **exactly** on the true slope in 18 of 18 combinations (true slopes
    0.0, +0.5, +1.0, +1.5, +2.0, -1.0 crossed with texture sigma 1.5 / 3.0 /
    5.0 px), and the sub-pixel refinement left every one of them unmoved. Its
    resolution, though, is whatever you put in *slopes* — it cannot see a plane
    you never refocused on.

    Returns ``(slope_map, sharpness)``: the ``(H, W)`` map of estimated slopes
    (in px per angular step) and the ``(H, W)`` peak focus-measure value, which
    is the honest confidence — a textureless pixel has no sharpness peak, gets
    an essentially arbitrary slope, and its ``sharpness`` is ~0. Threshold on it
    rather than trusting the map everywhere.

    **Raises** ``ValueError``: *lf* not a valid light field, *slopes* empty /
    over :data:`MAX_STACK_SLICES` / over :data:`MAX_STACK_ELEMENTS` / containing
    a non-finite or over-large value, an even or non-positive *window*, unknown
    *measure* / *interp* / *edge*.

Typed bridge of the lightfield op ``lf_depth_from_focus`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

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
