# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""estimate_lens_distortion — 本来まっすぐな線群から歪み係数を推定する(plumb-line 法)。

    py -3.11 examples/estimate_lens_distortion.py

【この例が示すこと】
歪み係数が「与えられている」前提の undistort_image に対し、こちらは係数を**測る**側。
本来まっすぐな線を歪ませた点列だけから estimate_distortion が k1,k2(必要なら p1,p2)を
回収し、その推定係数をそのまま undistort_image に渡すと弓なりが直ることを示す。
チェッカーボードの対応点は要らない —— 線がまっすぐだと分かっていればよい(Discorpy 流)。

EXTEND: 実写では、直線であるべき特徴(印刷線・建物のエッジ・定規)を線ごとに (x=col,y=row)
の点列として拾い(エッジ検出+追跡)、lines に渡す。主点=歪み中心は K で固定(この方法は
中心と p1,p2 を分離できない)。回収した dist は fs.undistort_image にそのまま渡せる。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402


def _straightness_rms(lines, K, dist):
    """各線を補正した後の『直線からの広がり(px, rms)』。まっすぐなほど小。"""
    s, n = 0.0, 0
    for p in lines:
        u = fs.undistort_points(p, K, dist)
        d = u - u.mean(0)
        _, sv, _ = np.linalg.svd(d, full_matrices=False)
        s += sv[1] ** 2
        n += len(p)
    return (s / n) ** 0.5


def _grid_lines(K, dist, size, n_lines=7, pts=40):
    """本来まっすぐな水平・垂直線を格子状に作り distort_points で歪ませた点列リスト。"""
    span = np.linspace(12, size - 12, pts)
    at = np.linspace(0.12 * size, 0.88 * size, n_lines)
    lines = []
    for yy in at:
        lines.append(fs.distort_points(np.column_stack([span, np.full_like(span, yy)]), K, dist))
    for xx in at:
        lines.append(fs.distort_points(np.column_stack([np.full_like(span, xx), span]), K, dist))
    return lines


def main() -> int:
    size = 200
    K = fs.intrinsic_matrix(0.95 * size, 0.95 * size, (size - 1) / 2, (size - 1) / 2)

    # 1) 放射(たる型)を回収 --------------------------------------------------- #
    true_dist = [-0.24, 0.06, 0.0, 0.0, 0.0]
    lines = _grid_lines(K, true_dist, size)
    est = fs.estimate_distortion(lines, K, radial=2, tangential=False)
    print("真の k1,k2   =", np.round(true_dist[:2], 4))
    print("推定 k1,k2   =", np.round(est[:2], 4))
    assert np.allclose(est[:2], true_dist[:2], atol=1e-5)

    # 補正で直線性が桁で回復する(dist=0 のまま vs 推定係数)。
    before = _straightness_rms(lines, K, np.zeros(5))
    after = _straightness_rms(lines, K, est)
    print("直線からの広がり(px): 補正前=%.4f  推定係数で補正後=%.6f" % (before, after))
    assert after < before / 100.0

    # 2) 接線も含めて回収 ------------------------------------------------------ #
    td2 = [-0.18, 0.04, 0.0018, -0.0012, 0.0]
    est2 = fs.estimate_distortion(_grid_lines(K, td2, size), K, radial=2, tangential=True)
    print("接線あり 真 =", np.round(td2, 5), " 推定 =", np.round(est2, 5))
    assert np.allclose(est2, td2, atol=1e-4)

    # 3) 推定係数を undistort_image にそのまま渡すと像が直る --------------------- #
    yy, xx = np.mgrid[0:size, 0:size]
    smooth = 0.5 + 0.5 * np.sin(xx / 22.0) * np.cos(yy / 26.0)
    distorted = fs.distort_image(smooth, K, true_dist)
    back = fs.undistort_image(distorted, K, est)              # ← 測った係数で補正
    c = (slice(40, size - 40), slice(40, size - 40))
    print("推定係数での像の往復 内部平均誤差=%.5f" % np.abs(back[c] - smooth[c]).mean())
    assert np.abs(back[c] - smooth[c]).mean() < 5e-3

    # 4) 雑音があっても素直に劣化(過信しない) -------------------------------- #
    rng = np.random.default_rng(0)
    noisy = [ln + rng.normal(0, 0.3, ln.shape) for ln in lines]
    est_n = fs.estimate_distortion(noisy, K, radial=2, tangential=False)
    err = abs(est_n[0] - true_dist[0]) / abs(true_dist[0])
    # 実数を正直に出す: 0.3px の点雑音で k1 は数〜十数 % ぶれる(点数・広がり・次数で変わる)。
    # 現場では線を増やす/画面いっぱいに張る/k2 を止める、で締める。過信しないための章。
    print("雑音 0.3px での k1 相対誤差 = %.2f %%" % (err * 100))
    assert err < 0.20

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
