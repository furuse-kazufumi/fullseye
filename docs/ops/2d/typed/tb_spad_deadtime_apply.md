---
op: tb_spad_deadtime_apply
dim: 2d
category: typed
in: counts
out: counts
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tb_spad_deadtime_apply — 2D `typed` op

- **データ種**: `counts` → `counts`
- **呼び出し**: `fullseye.apply(img, "tb_spad_deadtime_apply", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Distort a true photon rate by the detector's dead time (counts lost).

    After every detection a SPAD is blind for a recharge (dead) time ``tau``, so
    the *measured* rate ``m`` is always below the *true* incident rate ``n``.
    Two classical laws, and this op implements both:

      * **non-paralysable** (default) — an arriving photon during the dead time is
        simply lost: ``m = n / (1 + n*tau)``. Monotonic, saturating at ``1/tau``.
      * **paralysable** (``paralyzable=True``) — an arriving photon *restarts* the
        dead time: ``m = n * exp(-n*tau)``. This law **peaks** at ``n = 1/tau``
        (where ``m = 1/(e*tau)``) and then falls, so a bright scene can read
        *darker* than a dim one. That is why no inverse op exists for it (see
        :func:`spad_deadtime_correct`).

    *rate_hz* is a 1-D array of true rates in counts per second; *dead_time_ns*
    is the dead time in nanoseconds, defaulting to 50 — the middle of the
    10-100 ns range a passively quenched SPAD occupies, and a placeholder to be
    replaced by the datasheet value, never a measurement of your detector.
    Returns the measured rates as a float64 1-D array of the same length.

    Ground truth (pinned in the tests): at ``n = 1/tau`` the non-paralysable law
    gives exactly ``n/2``; the paralysable law's maximum is exactly
    ``1/(e*tau)`` at ``n = 1/tau``; both reduce to ``m = n`` as ``n*tau -> 0``.

    **Raises** ``ValueError``: negative, non-finite or non-1-D *rate_hz*, a
    non-positive *dead_time_ns*, and a non-bool *paralyzable*.

Typed bridge of the photon op ``spad_deadtime_apply`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. ``a`` drives ``dead_time_ns`` (default 50); ``b`` is unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`counts` を入力に取れる)

[identity](../misc/identity.md) · [tb_spad_deadtime_correct](tb_spad_deadtime_correct.md) · [tb_tcspc_coates_correct](tb_tcspc_coates_correct.md) · [tb_tcspc_irf_convolve](tb_tcspc_irf_convolve.md) · [tb_tcspc_background_subtract](tb_tcspc_background_subtract.md) · [tb_dtof_depth](tb_dtof_depth.md) · [tb_countrate_to_counts](tb_countrate_to_counts.md) · [tb_counts_to_countrate](tb_counts_to_countrate.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
