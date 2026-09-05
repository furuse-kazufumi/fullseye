---
op: tb_temporal_bandpass
dim: 2d
category: typed
in: video
out: video
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tb_temporal_bandpass — 2D `typed` op

- **データ種**: `video` → `video`
- **呼び出し**: `fullseye.apply(img, "tb_temporal_bandpass", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Ideal temporal band-pass of every pixel's time series -> ``(T, H, W)``.

    Each pixel is transformed along time, every DFT bin whose frequency lies
    outside ``[f_lo, f_hi]`` (in Hz, magnitude, DC always excluded) is zeroed,
    and the result is transformed back. Frequency-selective where
    ``videops.moving_average`` and ``videops.spatiotemporal_gaussian`` are
    low-pass; this is the filter isolating "what is happening at 4 Hz".

    Exact for a component sitting on a bin: with ``T`` frames at ``fps``, a
    sinusoid at ``k*fps/T`` Hz passes with gain 1 and everything else in the band
    passes untouched. Measured on a bin-centred 4 Hz unit sinusoid in a 64-frame
    32 fps clip that also carries a DC offset of 0.5 and a 12 Hz component of
    amplitude 0.3, the recovered waveform matches the 4 Hz term alone to
    ``max|err| = 4.36e-15``.

    A brick-wall filter rings in time; that is the price of an exact pass-band
    and it is the same choice the 2012 Eulerian magnification paper makes. The
    output is zero-mean along time by construction.

Typed bridge of the motionmag op ``temporal_bandpass`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`video` を入力に取れる)

[identity](../misc/identity.md) · [tb_temporal_band_power](tb_temporal_band_power.md) · [tb_temporal_median_window](tb_temporal_median_window.md) · [tb_moving_average_window](tb_moving_average_window.md) · [tb_background_subtraction_window](tb_background_subtraction_window.md) · [tb_frame_difference_causal](tb_frame_difference_causal.md) · [tb_exponential_background](tb_exponential_background.md) · [tb_exponential_foreground](tb_exponential_foreground.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
