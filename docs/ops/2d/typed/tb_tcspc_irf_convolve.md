---
op: tb_tcspc_irf_convolve
dim: 2d
category: typed
in: counts
out: counts
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# tb_tcspc_irf_convolve — 2D `typed` op

- **データ種**: `counts` → `counts`
- **呼び出し**: `fullseye.apply(img, "tb_tcspc_irf_convolve", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Blur an arrival-time histogram by the instrument response (timing jitter).

    The temporal analogue of a PSF convolution: a detector's timing uncertainty
    (SPAD jitter + TDC quantisation + laser pulse width) smears every arrival
    time by the instrument response function, here a Gaussian of full width at
    half maximum *irf_fwhm_ps*. The kernel is the **exact bin integral** of that
    Gaussian (erf differences), normalised to sum 1, truncated at
    ``+-truncate*sigma`` and forced to odd length so the convolution is centred.

    Ground truth: convolving a unit spike in the middle of a 256-bin window with
    ``irf_fwhm_ps = 500`` at ``bin_ps = 50`` leaves the centroid **exactly**
    where it was (measured shift 0.0 ps — the kernel is symmetric) and gives a
    profile whose measured FWHM is 501.22 ps. That 0.24% excess over 500 is the
    *measurement*, not the kernel: :func:`tcspc_stats` finds the half-maximum
    crossings by linear interpolation between bins, which slightly overestimates
    the width of a Gaussian.

    Total counts are preserved *except* at the window edges, where
    ``mode='same'`` discards the tail that falls outside — measured loss exactly
    0 for that centred spike, but a genuine loss for a pulse within a few sigma
    of either end.

    Returns a float64 1-D histogram of the same length as *hist*.

    **Raises** ``ValueError``: negative, non-finite or non-1-D *hist*, a
    non-positive *bin_ps* / *irf_fwhm_ps* / *truncate*, an IRF sigma below
    1e-3 bins (the kernel would be a delta and the op a no-op — say so instead
    of pretending to blur), and a kernel that would be longer than the
    :data:`MAX_BINS` cap.

Typed bridge of the photon op ``tcspc_irf_convolve`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. ``a`` drives ``bin_ps`` (default 100) and ``b`` drives ``irf_fwhm_ps`` (default 200).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`counts` を入力に取れる)

[identity](../misc/identity.md) · [tb_spad_deadtime_apply](tb_spad_deadtime_apply.md) · [tb_spad_deadtime_correct](tb_spad_deadtime_correct.md) · [tb_tcspc_coates_correct](tb_tcspc_coates_correct.md) · [tb_tcspc_background_subtract](tb_tcspc_background_subtract.md) · [tb_dtof_depth](tb_dtof_depth.md) · [tb_countrate_to_counts](tb_countrate_to_counts.md) · [tb_counts_to_countrate](tb_counts_to_countrate.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
