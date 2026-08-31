# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""math_metrology — 視覚計測を支える数学 op(mathops)を計測ワークフローで一巡する。

    py -3.11 examples/math_metrology.py

【この例が解く問題】
深度カメラで平面(定盤)を測った点群から、(1) 平面を最小二乗フィットし、
(2) 残差ノイズを統計で特徴づけ、(3) ノイズの共分散楕円を固有分解で主軸化し、
(4) レンズ歪み風の較正曲線を多項式フィット(条件数を監視)して、
(5) 補間で逆引き(測定値→真値)する — mathops 16 op 全てを実データ風に通す。

【グラウンドトゥルース(数値で嘘を弾く)】
1. 平面 z = ax + by + c の係数 (a, b, c) を lstsq / 正規方程式 solve / pinv の
   3 経路で復元し、全て一致 + 真値に収束(cond で正規方程式の条件も監視)。
2. 残差の describe: mean ≈ 0、std ≈ 注入ノイズ。histogram の度数和 = N。
   zscore の最大絶対値が正規ノイズとして妥当(< 5)。
3. 2 次元ノイズ雲の covariance → eigh: 固有値 ≈ 既知分散、主軸 ≈ 既知回転角。
   centered データの SVD 特異値² / (N-1) が固有値と一致(交差検証)。
   correlation は既知の正相関を検出。
4. 較正多項式 r_meas = r + 0.15 r³ を poly_fit(3 次)で復元(係数厳密)、
   poly_eval で往路検証、poly_roots で「r_meas = 1.0 になる真の r」を厳密解と照合。
5. interp_linear / interp_cubic による逆引き較正(単調表の x⇄y 入替)が
   真値に一致(cubic は linear より高精度)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mathops as M  # noqa: E402


def main():
    rng = np.random.default_rng(42)

    # ---------------------------------------------------------------- #
    # 1) 平面フィット: z = 0.02 x + 0.5 y + 3.0 + N(0, 0.01)           #
    # ---------------------------------------------------------------- #
    a_t, b_t, c_t, noise = 0.02, 0.5, 3.0, 0.01
    xx, yy = np.meshgrid(np.linspace(-1, 1, 20), np.linspace(-1, 1, 20))
    x, y = xx.ravel(), yy.ravel()
    z = a_t * x + b_t * y + c_t + noise * rng.standard_normal(x.size)

    A = np.column_stack([x, y, np.ones_like(x)])           # (400, 3) 設計行列
    fit = M.mat_lstsq(A, z)                                # 経路1: SVD 最小二乗
    coef = fit["x"]

    N_mat, rhs = A.T @ A, A.T @ z                          # 正規方程式 (3x3)
    cond_N = M.mat_cond(N_mat)                             # 条件数を必ず見る
    coef2 = M.mat_solve(N_mat, rhs)                        # 経路2: 正方 solve
    coef3 = M.mat_pinv(A, rcond=1e-12) @ z                 # 経路3: 擬似逆行列

    print(f"平面フィット: (a,b,c)=({coef[0]:+.4f},{coef[1]:+.4f},{coef[2]:+.4f}) "
          f"真値=({a_t:+.4f},{b_t:+.4f},{c_t:+.4f})  cond(AᵀA)={cond_N:.1f}")
    assert np.allclose(coef, [a_t, b_t, c_t], atol=5e-3)   # ノイズ内で真値復元
    assert np.allclose(coef, coef2, atol=1e-9)             # 3 経路一致
    assert np.allclose(coef, coef3, atol=1e-9)
    assert fit["rank"] == 3 and np.isfinite(cond_N) and cond_N < 1e3

    # ---------------------------------------------------------------- #
    # 2) 残差統計: describe / histogram / zscore                        #
    # ---------------------------------------------------------------- #
    resid = z - A @ coef
    d = M.stat_describe(resid)
    counts, edges = M.stat_histogram(resid, bins=15)
    zsc = M.stat_zscore(resid)
    print(f"残差統計    : mean={d['mean']:+.2e} std={d['std']:.4f}(注入 {noise}) "
          f"p5={d['percentiles']['p5']:+.4f} p95={d['percentiles']['p95']:+.4f} "
          f"max|z|={np.abs(zsc).max():.2f}")
    assert abs(d["mean"]) < 5e-3                           # 不偏(平均 ≈ 0)
    assert abs(d["std"] - noise) < 0.4 * noise             # std ≈ 注入ノイズ
    assert int(counts.sum()) == d["n"] == resid.size       # 度数和 = N
    assert edges.size == 16
    assert np.abs(zsc).max() < 5.0                         # 正規ノイズとして妥当

    # ---------------------------------------------------------------- #
    # 3) ノイズ共分散楕円: covariance → eigh(主軸)+ SVD 交差検証     #
    # ---------------------------------------------------------------- #
    # 既知: 標準偏差 (3, 0.5) の楕円雲を θ=30° 回転 → 固有値 {0.25, 9}、
    # 主軸方向 (cosθ, sinθ)。
    th = np.deg2rad(30.0)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    cloud = (R @ np.diag([3.0, 0.5]) @ rng.standard_normal((2, 4000))).T  # (N,2)

    C = M.stat_covariance(cloud)
    w, V = M.mat_eigh(C)                                   # 昇順固有値, 列=固有ベクトル
    major = V[:, 1]                                        # 最大固有値の主軸
    ang = np.degrees(np.arctan2(abs(major[1]), abs(major[0])))
    print(f"共分散楕円  : 固有値=({w[0]:.3f},{w[1]:.3f}) 真値=(0.25,9.0) "
          f"主軸角={ang:.1f}°(真値 30°)")
    assert abs(w[1] - 9.0) < 0.5 and abs(w[0] - 0.25) < 0.05
    assert abs(ang - 30.0) < 2.0                           # 符号不定でも角度は一意

    centered = cloud - cloud.mean(axis=0)
    _, s, _ = M.mat_svd(centered)                          # SVD 交差検証:
    ev_from_svd = (s ** 2) / (cloud.shape[0] - 1)          # s²/(N-1) = 固有値(降順)
    assert np.allclose(sorted(ev_from_svd), w, rtol=1e-10)

    corr = M.stat_correlation(cloud)                       # 30° 回転 → 正相関
    print(f"相関行列    : r={corr[0, 1]:+.3f}(30° 回転楕円 → 正の相関)")
    assert corr[0, 0] == 1.0 and corr[0, 1] > 0.5

    # ---------------------------------------------------------------- #
    # 4) 較正曲線: r_meas = r + 0.15 r³ を 3 次 poly_fit(cond 監視)   #
    # ---------------------------------------------------------------- #
    r = np.linspace(0.0, 1.2, 25)
    r_meas = r + 0.15 * r ** 3                             # 樽型歪み風の較正真値
    pf = M.poly_fit(r, r_meas, 3)
    print(f"較正フィット: coeffs={np.round(pf['coeffs'], 6)} 真値=[0.15,0,1,0] "
          f"cond={pf['cond']:.1f} rms={pf['rms_residual']:.2e}")
    assert np.allclose(pf["coeffs"], [0.15, 0.0, 1.0, 0.0], atol=1e-9)
    assert pf["cond"] < M.POLY_COND_WARN                   # 健全な条件数を確認
    assert pf["rms_residual"] < 1e-12

    fwd = M.poly_eval(pf["coeffs"], 0.8)                   # 往路: r=0.8 → 測定値
    assert abs(fwd - (0.8 + 0.15 * 0.8 ** 3)) < 1e-12

    # 「測定値 1.0 を与える真の r」= 0.15 r³ + r - 1 = 0 の実根(poly_roots)
    shifted = pf["coeffs"].copy()
    shifted[-1] -= 1.0
    roots = M.poly_roots(shifted, real_only=True)
    r_true = roots[(roots >= 0.0) & (roots <= 1.2)]
    assert r_true.size == 1
    check = M.poly_eval(pf["coeffs"], float(r_true[0]))
    print(f"逆算(厳密) : r_meas=1.0 ← r={r_true[0]:.6f}(検算 p(r)={check:.6f})")
    assert abs(check - 1.0) < 1e-10
    # 複素対応の確認: x² + 1 の根は ±i(実根は無し)
    ci = M.poly_roots([1.0, 0.0, 1.0])
    assert np.allclose(sorted(ci.imag), [-1.0, 1.0], atol=1e-12)
    assert M.poly_roots([1.0, 0.0, 1.0], real_only=True).size == 0

    # ---------------------------------------------------------------- #
    # 5) 補間逆引き: 単調な較正表 (r_meas → r) を interp で引く         #
    # ---------------------------------------------------------------- #
    q = 1.0                                                # 測定値 1.0 の逆引き
    inv_lin = M.interp_linear(r_meas, r, q)                # 表の x⇄y 入替 = 逆関数
    inv_cub = M.interp_cubic(r_meas, r, q)
    e_lin, e_cub = abs(inv_lin - r_true[0]), abs(inv_cub - r_true[0])
    print(f"補間逆引き  : linear={inv_lin:.6f}(誤差 {e_lin:.2e}) "
          f"cubic={inv_cub:.6f}(誤差 {e_cub:.2e})")
    assert e_lin < 5e-4 and e_cub < 1e-6
    assert e_cub < e_lin                                   # 滑らか曲線では cubic 優位
    # 範囲外は fail-closed(既定)/ clamp は明示指定
    try:
        M.interp_linear(r_meas, r, 99.0)
        raise AssertionError("out-of-range must raise by default")
    except ValueError:
        pass
    assert M.interp_linear(r_meas, r, 99.0, out_of_range="clamp") == r[-1]

    print("PASS math_metrology: mathops 16 op(linalg 6 + stats 5 + interp/poly 5)"
          "を計測ワークフローで検証(平面フィット3経路一致/共分散楕円=SVD交差検証/"
          "較正多項式厳密復元/逆引き較正)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
