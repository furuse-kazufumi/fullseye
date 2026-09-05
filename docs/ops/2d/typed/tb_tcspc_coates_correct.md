---
op: tb_tcspc_coates_correct
dim: 2d
category: typed
in: counts
out: counts
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# tb_tcspc_coates_correct — 2D `typed` op

- **データ種**: `counts` → `counts`
- **呼び出し**: `fullseye.apply(img, "tb_tcspc_coates_correct", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Undo TCSPC pile-up exactly (Coates's estimator) — the early-photon bias.

    Classical TCSPC records **at most one photon per excitation cycle**: the
    first one. Late bins are therefore starved, because the cycles in which an
    early photon arrived never reach them, and the measured histogram is biased
    toward short arrival times — a dToF depth read straight off a piled-up
    histogram is *too close*, and a fluorescence lifetime is *too short*.

    Coates's estimator inverts that exactly. With ``N_k`` the measured counts in
    bin ``k`` and ``C`` the number of excitation cycles, the number of cycles that
    survived to reach bin ``k`` is ``D_k = C - sum_{j<k} N_j``, the per-cycle
    detection probability in that bin is ``p_k = N_k / D_k`` and the pile-up-free
    per-cycle intensity is ``lambda_k = -ln(1 - p_k)``. This op returns
    ``C * lambda_k`` — the histogram the same scene would have produced if the
    detector could record every photon — so it is directly comparable to the
    measured one.

    This is an **exact** inverse, not a linearisation: build a histogram from a
    known ``lambda`` through the forward model ``N_k = C * exp(-sum_{j<k}
    lambda_j) * (1 - exp(-lambda_k))`` and Coates returns ``lambda`` to machine
    precision (measured max relative error 1.6e-15 in the tests, on a pile-up so
    severe that the last bin was suppressed to 14.8% of its true counts).

    *hist* is the 1-D measured histogram (counts per bin); *cycles* the number of
    excitation cycles (laser pulses) that produced it.

    **Raises** ``ValueError``: negative, non-finite or non-1-D *hist*, a
    non-positive or non-integer *cycles*, a histogram whose total exceeds
    *cycles* (impossible: at most one photon per cycle — a sure sign that
    *cycles* is wrong or the data are not first-photon TCSPC), and any bin that
    consumed every remaining cycle (``p_k = 1``, where ``-ln(0)`` is ``inf``).

Typed bridge of the photon op ``tcspc_coates_correct`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`counts` を入力に取れる)

[identity](../misc/identity.md) · [tb_spad_deadtime_apply](tb_spad_deadtime_apply.md) · [tb_spad_deadtime_correct](tb_spad_deadtime_correct.md) · [tb_tcspc_irf_convolve](tb_tcspc_irf_convolve.md) · [tb_tcspc_background_subtract](tb_tcspc_background_subtract.md) · [tb_dtof_depth](tb_dtof_depth.md) · [tb_countrate_to_counts](tb_countrate_to_counts.md) · [tb_counts_to_countrate](tb_counts_to_countrate.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
