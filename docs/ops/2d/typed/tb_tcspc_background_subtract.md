---
op: tb_tcspc_background_subtract
dim: 2d
category: typed
in: counts
out: counts
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# tb_tcspc_background_subtract — 2D `typed` op

- **データ種**: `counts` → `counts`
- **呼び出し**: `fullseye.apply(img, "tb_tcspc_background_subtract", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Remove the ambient-light / dark-count floor from an arrival-time histogram.

    Outdoors, most of what a dToF sensor counts is sunlight: a roughly uniform
    pedestal under the return pulse. It biases the centroid toward the middle of
    the window (a floor of ``b`` per bin pulls the first moment toward
    ``window/2``) and it inflates the apparent signal, so it is removed before
    any depth or lifetime estimate.

    The level is estimated by *method* and then **subtracted** (the sign trap:
    the result is ``hist - level``, clipped at 0, never ``hist + level``):

      * ``"median"`` (default) — the median of every bin. Robust while the pulse
        occupies well under half the window, which is the normal dToF case.
      * ``"leading"`` — the mean of the first *leading_bins* bins, the classical
        choice when the pulse is known to arrive late (a far target).
      * ``"trailing"`` — the mean of the last *leading_bins* bins, for
        fluorescence decays where the tail is background.
      * ``"quantile"`` — the given *quantile* of all bins, for tuning by hand.

    *leading_bins* defaults to ``None`` = ``min(8, len(hist))``, so the default
    call works on a short histogram instead of raising over a constant nobody
    chose (a fixed default of 8 made ``method="leading"`` fail on any histogram
    with fewer than 8 bins).

    *scale* multiplies the estimated level before subtraction (``scale=1.2`` for
    a deliberately aggressive removal). Clipping at 0 means the result is a valid
    non-negative histogram that the rest of this module will accept.

    Ground truth: on a noiseless histogram with a known flat pedestal of 20
    counts/bin under a 5000-photon pulse covering 5.1% of the window, the median
    estimate recovers 20.000000 and the returned histogram equals the pedestal-
    free pulse **exactly** (measured area error 0.0, pinned in the tests).

    Returns a float64 1-D histogram of the same length as *hist*.

    **Raises** ``ValueError``: negative, non-finite or non-1-D *hist*, an unknown
    *method*, a *leading_bins* outside ``[1, len(hist)]``, a *quantile* outside
    ``[0, 1]``, and a negative *scale*.

Typed bridge of the photon op ``tcspc_background_subtract`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. ``a`` drives ``quantile`` (default 0.5) and ``b`` drives ``scale`` (default 1).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`counts` を入力に取れる)

[identity](../misc/identity.md) · [tb_spad_deadtime_apply](tb_spad_deadtime_apply.md) · [tb_spad_deadtime_correct](tb_spad_deadtime_correct.md) · [tb_tcspc_coates_correct](tb_tcspc_coates_correct.md) · [tb_tcspc_irf_convolve](tb_tcspc_irf_convolve.md) · [tb_dtof_depth](tb_dtof_depth.md) · [tb_countrate_to_counts](tb_countrate_to_counts.md) · [tb_counts_to_countrate](tb_counts_to_countrate.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
