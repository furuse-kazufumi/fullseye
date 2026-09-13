---
op: tb_fly_lgmd_eta
dim: 2d
category: typed
in: signal
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# tb_fly_lgmd_eta — 2D `typed` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `fullseye.apply(img, "tb_fly_lgmd_eta", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

LGMD/eta looming response from an expanding subtended angle.

    The multiplicative looming model::

        eta(t) = theta'(t - delay) * exp(-alpha * theta(t - delay))

    where *theta_signal* is the object's full subtended angle over time, in
    radians. The product of the angular expansion rate and an exponentially
    decaying gain gives a response that peaks a fixed time before collision.

    theta_signal: the full subtended angle per sample, radians.
    dt_s:  the sample interval, seconds.
    alpha: the gain-decay constant.
    delay_s: a fixed neural delay, seconds.

    Returns a 1-D float64 array ``eta(t)`` of the same length.

    Ground truth: for an object of half-size ``l`` approaching at speed ``|v|``,
    ``eta`` peaks at a time-to-contact of ``alpha*l/|v| - delay_s`` (Gabbiani et
    al. Eq. 5), where the subtended angle is exactly ``2*atan(1/alpha)`` (Eq. 6;
    24.0 degrees for ``alpha = 4.7``) — both pinned in the tests.

    **Raises** ``ValueError``: a non-1-D / empty / too-short (< 3) / non-finite
    *theta_signal*, a signal over :data:`MAX_SIGNAL_POINTS`, a non-positive *dt_s*
    / *alpha*, and a negative *delay_s*.

Typed bridge of the flyvision op ``fly_lgmd_eta`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. ``a`` drives ``alpha`` (default 4.7); ``b`` is unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[identity](../misc/identity.md) · [tb_create_funct_1d_array](tb_create_funct_1d_array.md) · [tb_smooth_funct_1d_gauss](tb_smooth_funct_1d_gauss.md) · [tb_smooth_funct_1d_mean](tb_smooth_funct_1d_mean.md) · [tb_derivate_funct_1d](tb_derivate_funct_1d.md) · [tb_integrate_funct_1d](tb_integrate_funct_1d.md) · [tb_zero_crossings_funct_1d](tb_zero_crossings_funct_1d.md) · [tb_abs_funct_1d](tb_abs_funct_1d.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md) · [tb_voxel_grid_downsample](tb_voxel_grid_downsample.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
