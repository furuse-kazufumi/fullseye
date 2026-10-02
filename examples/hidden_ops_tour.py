# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""hidden_ops_tour — 公開経路の無かった道具 18 本を、答えの決まる入力で一巡する。

    py -3.11 examples/hidden_ops_tour.py

【この例が示すこと】
2026-10-02 の棚卸し(「名前の無い非公開関数」136 本)で、op として振る舞うのに ``fullseye`` のどこからも
呼べなかった 18 本を ``fs.<名前>`` から出した。各節は「真値 / 実測」を印字し、すべて assert で落とす。

【グラウンドトゥルース】
1. ncc_map_3d: 切り出したテンプレートの位置で NCC = 1。
2. gradient_normals + subpixel_refine_edges: 端が画素の中点(x.5)なら放物線補間は厳密。
3. gen_gauss_bandpass + apply_bandpass: 周期境界の純正弦波はマスクの値だけ縮む(線形・ずらし不変)。
4. normals_to_gradients + integrate_gradients: 周期的で帯域制限された面は Frankot–Chellappa で厳密に戻る。
5. triangulate_points / rel_pose_to_essential_matrix: 雑音なしで 3-D 点が戻る / エピポーラ拘束 0・特異値 (σ, σ, 0)。
6. pyr_down / image_pyramid: 大きさが半分ずつ、定数は定数のまま。
7. rotational_symmetry_score: 4 回対称の点群は次数 4 と 2 で 0、3 では正。
8. dilation2 / min_max_gray_n / get_bounding_box_object_model_3d / ensure_gray / ensure_color: 定義どおり。
(gaussians_to_mesh は open3d と torch が要るので、この例では存在だけ確かめる。門は tests/ 側。)
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fullseye as fs          # noqa: E402  公開経路(fs.<名前>)から呼ぶ


def run() -> dict:
    t0 = time.perf_counter()
    out = {}

    rng = np.random.default_rng(0)
    v = rng.random((20, 22, 24))
    m = np.asarray(fs.ncc_map_3d([v], v[5:10, 6:11, 7:12].copy())[0])
    peak = tuple(int(i) for i in np.unravel_index(int(np.argmax(m)), m.shape))
    print("1) ncc_map_3d: 峰 %s(テンプレートの中心 (7, 8, 9))、値 %.6f" % (peak, m[peak]))
    assert peak == (7, 8, 9) and abs(m[peak] - 1.0) < 1e-6
    out["ncc_peak"] = peak

    x = np.indices((32, 32))[1].astype(float)
    img = 1 / (1 + np.exp(-(x - 15.5) / 0.8))
    g, ny, nx = fs.gradient_normals(img)
    pts = np.array([[r, 15.0] for r in range(5, 27)])
    col = float(fs.subpixel_refine_edges(pts, g, ny, nx)[:, 1].mean())
    print("2) サブピクセルの端: 真値 15.5 / 実測 %.12f" % col)
    assert abs(col - 15.5) < 1e-9

    mask = fs.gen_gauss_bandpass((64, 64), 0.02, 0.2)
    wave = np.cos(2 * np.pi * 8 * np.indices((64, 64))[1] / 64)
    got = np.asarray(fs.apply_bandpass(wave, mask), float)
    gain = float(got[0, 0] / wave[0, 0])
    print("3) 帯域通過: 周波数 8/64 の利得 = マスクの値 %.6f / 実測 %.6f" % (mask[0, 8], gain))
    assert np.allclose(got, mask[0, 8] * wave, atol=1e-9)

    H, W = 48, 64
    yy, xx = np.indices((H, W)).astype(float)
    z = np.sin(2 * np.pi * xx / W) * np.cos(4 * np.pi * yy / H)
    zx = np.cos(2 * np.pi * xx / W) * (2 * np.pi / W) * np.cos(4 * np.pi * yy / H)
    zy = -np.sin(2 * np.pi * xx / W) * np.sin(4 * np.pi * yy / H) * (4 * np.pi / H)
    n = np.dstack([-zx, -zy, np.ones_like(z)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    zr = fs.integrate_gradients(*fs.normals_to_gradients(n))
    err = float(np.abs(zr - (z - z.mean())).max())
    print("4) 法線 → 勾配 → 高さ: 最大誤差 %.2e(振幅 1)" % err)
    assert err < 1e-10
    out["height_err"] = err

    K = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1.0]])
    a = 0.1
    R = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    t = np.array([-0.5, 0.02, 0.03])
    P1 = K @ np.hstack([np.eye(3), np.zeros((3, 1))])
    P2 = K @ np.hstack([R, t[:, None]])
    X = rng.uniform([-1, -1, 4], [1, 1, 8], (20, 3))
    Xh = np.hstack([X, np.ones((20, 1))])
    u1 = (P1 @ Xh.T).T
    u2 = (P2 @ Xh.T).T
    Xr = fs.triangulate_points(P1, P2, u1[:, :2] / u1[:, 2:], u2[:, :2] / u2[:, 2:])
    E = fs.rel_pose_to_essential_matrix(R, t)
    s = np.linalg.svd(E, compute_uv=False)
    print("5) 三角測量の誤差 %.1e / 本質行列の特異値 (%.4f, %.4f, %.1e)" % (np.abs(Xr - X).max(), *s))
    assert np.abs(Xr - X).max() < 1e-9 and abs(s[0] - s[1]) < 1e-12 and s[2] < 1e-12

    shapes = [p.shape for p in fs.image_pyramid(rng.random((65, 50)), 4)]
    print("6) ピラミッド: %s、定数の ptp = %.1e" % (shapes, np.ptp(fs.pyr_down(np.full((32, 32), 0.7)))))
    assert shapes == [(65, 50), (33, 25), (17, 13), (9, 7)]

    base = np.array([[1.0, 0.2, 0.0], [1.5, -0.1, 0.3], [0.7, 0.4, -0.2]])
    P = np.concatenate([base @ np.array([[math.cos(q), -math.sin(q), 0], [math.sin(q), math.cos(q), 0],
                                         [0, 0, 1]]).T for q in np.linspace(0, 2 * np.pi, 4, endpoint=False)])
    sc = {k: float(fs.rotational_symmetry_score(P, [0, 0, 0], [0, 0, 1], k)) for k in (2, 3, 4)}
    print("7) 4 回対称の点群: 次数 2 → %.1e、3 → %.3f、4 → %.1e" % (sc[2], sc[3], sc[4]))
    assert sc[2] < 1e-9 and sc[4] < 1e-9 and sc[3] > 0.5

    region = rng.random((30, 30)) > 0.93
    se = np.ones((3, 5), bool)
    assert np.array_equal(fs.dilation2(region, se, row=1, col=2), ndimage.binary_dilation(region, structure=se))
    stack = [rng.random((6, 7)) for _ in range(4)]
    mm = fs.min_max_gray_n(stack)
    assert np.array_equal(mm["min"], np.min(stack, axis=0))
    bb = fs.get_bounding_box_object_model_3d(X)
    assert np.allclose(bb["extent"], X.max(0) - X.min(0))
    assert fs.ensure_color(fs.ensure_gray(rng.random((5, 6, 3)))).shape == (5, 6, 3)
    assert callable(fs.gaussians_to_mesh)
    print("8) dilation2 = 中心の参照点で素の膨張 / min_max_gray_n / 外接箱 / 灰⇄色: すべて定義どおり")

    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  hidden_ops_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()
