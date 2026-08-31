# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""math_complex — 複素解析 op(mathops tier2)を「閉形式の真値と突き合わせながら」一巡する。

    py -3.11 examples/math_complex.py

【この例が解く問題】
「多項式の零点は単位円の中に何個あるか」「境界の値だけから内部の値を復元できるか」
「この写像は等角か」「この場(位相画像・伝達関数)は正則か」— 複素解析の教科書問題を、
閉曲線を**点列**として持つだけで numpy 演算に落として答える。輪郭上の f はユーザーが
サンプルする(op は Python の関数を呼び戻さない)ので、式でも実測データでも同じ形で扱える。

【グラウンドトゥルース(数値で嘘を弾く)】
1. 周回積分: ∮dz/z = 2πi(Cauchy)。弦の台形則は 2 次収束なので、分点 4 倍で誤差 1/16 に
   なることまで確認する(許容値を 1 つ置くだけでは間違った求積を隠せる)。
2. 偏角の原理: z³-1 の零点は |z|=2 の内側に 3 個・|z|=0.5 の内側に 0 個・z=1 の周りに 1 個。
   極は負に数える(1/z² → -2)。向きを逆にすると符号が反転する。
3. Cauchy の積分公式: 境界上の z² だけから f(0.3)=0.09 を復元。時計回りでも同じ値
   (巻き数で割るため)。
4. Laurent 係数: 1/(z-0.5) の c₋₁=1(留数)・c₋₂=0.5・c₋₃=0.25、exp(z) の cₖ=1/k!。
5. 等角写像: Joukowski は単位円を実軸の線分 [-2,2](w=2cos t)へ、半径 R の円を半軸
   R±1/R の楕円へ。Möbius(Cayley 変換)は実軸を単位円へ、i を 0 へ。
6. Cauchy-Riemann 残差: z² は 0(中心差分は 2 次まで厳密)、conj(z) はちょうど 2。

【honest な限界】
- 巻き数・偏角の原理は**サンプル多角形**の量。粗いと数え落とす(z⁵ を 4 点円で数えると 1)。
  π/2 を超えると RuntimeWarning が出る。確かめ方は昔から 1 つ、分点を倍にして安定するまで。
- 弦の台形則は 2 次(∮ は分点数に敏感)。一方 Laurent 係数は円上の三角多項式なので指数収束。
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mathops as M  # noqa: E402


def main():
    two_pi_i = 2.0j * np.pi

    # ---------------------------------------------------------------- #
    # 1) 周回積分 ∮dz/z = 2πi と、その 2 次収束                        #
    # ---------------------------------------------------------------- #
    err = {}
    for n in (256, 1024):
        z = M.cplx_contour_circle(0.0, 1.0, n)          # 反時計回り(正の向き)
        err[n] = abs(M.cplx_contour_integral(z, 1.0 / z) - two_pi_i) / (2 * np.pi)
    print(f"1) ∮dz/z: n=256 相対誤差 {err[256]:.2e} / n=1024 {err[1024]:.2e} "
          f"(比 {err[256] / err[1024]:.1f} ≈ 16 = 2 次収束)")
    assert err[256] < 2e-4 and 14.0 < err[256] / err[1024] < 18.0

    z = M.cplx_contour_circle(0.0, 2.0, 64)
    assert abs(M.cplx_contour_integral(z, z ** 2)) < 1e-9        # 正則 → 0
    assert abs(M.cplx_contour_integral(z, 1.0 / (z - 10.0))) < 1e-9  # 極が外 → 0

    # ---------------------------------------------------------------- #
    # 2) 偏角の原理: 微分も求根もせずに零点・極を数える                #
    # ---------------------------------------------------------------- #
    p = np.array([1.0, 0.0, 0.0, -1.0])                 # z³ - 1(零点は |z|=1 上の 3 点)
    big = M.cplx_contour_circle(0.0, 2.0, 512)
    small = M.cplx_contour_circle(0.0, 0.5, 512)
    around_one = M.cplx_contour_circle(1.0, 0.3, 512)
    n_big = M.cplx_argument_principle(big, M.cplx_poly_eval(p, big))
    n_small = M.cplx_argument_principle(small, M.cplx_poly_eval(p, small))
    n_one = M.cplx_argument_principle(around_one, M.cplx_poly_eval(p, around_one))
    unit = M.cplx_contour_circle(0.0, 1.0, 256)
    n_pole = M.cplx_argument_principle(unit, 1.0 / unit ** 2)
    print(f"2) z³-1 の零点数: |z|=2 内 {n_big} / |z|=0.5 内 {n_small} / z=1 の周り {n_one}"
          f"、1/z² の Z-P = {n_pole}(2 位の極)")
    assert (n_big, n_small, n_one, n_pole) == (3, 0, 1, -2)
    assert M.cplx_winding_number(big, 0.0) == 1
    assert M.cplx_winding_number(
        M.cplx_contour_circle(0.0, 2.0, 512, orientation="cw"), 0.0) == -1

    # 粗すぎる輪郭は数え落とす(警告が出る)— 正直な限界の実演
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        coarse = M.cplx_contour_circle(0.0, 1.0, 4)
        aliased = M.cplx_argument_principle(coarse, coarse ** 5)
    print(f"   粗い輪郭(4 点)で z⁵ を数えると {aliased}(真値 5)— 警告 "
          f"{len(caught)} 件、分点を増やせば "
          f"{M.cplx_argument_principle(M.cplx_contour_circle(0.0, 1.0, 64), M.cplx_contour_circle(0.0, 1.0, 64) ** 5)}")
    assert aliased == 1 and len(caught) == 1

    # ---------------------------------------------------------------- #
    # 3) Cauchy の積分公式: 境界の値だけから内部の値                    #
    # ---------------------------------------------------------------- #
    c = M.cplx_contour_circle(0.0, 1.0, 256)
    v_mid = M.cplx_cauchy_value(c, c ** 2, 0.3)
    cw = M.cplx_contour_circle(0.0, 1.0, 256, orientation="cw")
    v_cw = M.cplx_cauchy_value(cw, cw ** 2, 0.3)
    print(f"3) f(0.3) 復元: {v_mid.real:.6f}(真値 0.09、時計回りでも {v_cw.real:.6f})")
    assert abs(v_mid - 0.09) < 1e-4 and abs(v_cw - 0.09) < 1e-4
    try:
        M.cplx_cauchy_value(c, c ** 2, 5.0)             # 外の点は fail-closed
        raise AssertionError("外部点が通ってしまった")
    except ValueError as e:
        assert "outside the contour" in str(e)

    # ---------------------------------------------------------------- #
    # 4) Laurent 係数と留数                                            #
    # ---------------------------------------------------------------- #
    lau = M.cplx_laurent_coeffs(c, 1.0 / (c - 0.5), kmin=-3, kmax=1)
    k = list(lau["k"])
    res = lau["c"][k.index(-1)].real
    print(f"4) 1/(z-0.5) の Laurent: c₋₁={res:.12f}(留数 1)"
          f" c₋₂={lau['c'][k.index(-2)].real:.12f}(0.5)"
          f" c₋₃={lau['c'][k.index(-3)].real:.12f}(0.25)")
    assert abs(res - 1.0) < 1e-12
    tay = M.cplx_laurent_coeffs(c, np.exp(c), kmin=0, kmax=5)
    assert np.allclose(tay["c"].real, 1.0 / np.array([1, 1, 2, 6, 24, 120.0]), atol=1e-12)

    # ---------------------------------------------------------------- #
    # 5) 等角写像(Joukowski / Möbius)                                 #
    # ---------------------------------------------------------------- #
    w = M.cplx_joukowski(c, 1.0)
    assert np.abs(w.imag).max() < 1e-14
    assert np.allclose(w.real, 2.0 * np.cos(np.angle(c)), atol=1e-14)
    ell = M.cplx_joukowski(M.cplx_contour_circle(0.0, 2.0, 128), 1.0)
    a_ax, b_ax = 2.0 + 0.5, 2.0 - 0.5
    print(f"5) Joukowski: 単位円 → 実軸線分 [{w.real.min():.1f}, {w.real.max():.1f}]、"
          f"R=2 の円 → 半軸 {a_ax}/{b_ax} の楕円")
    assert np.abs(ell.real ** 2 / a_ax ** 2 + ell.imag ** 2 / b_ax ** 2 - 1.0).max() < 1e-12

    x = np.linspace(-50.0, 50.0, 501) + 0j
    cay = M.cplx_mobius(x, 1.0, -1j, 1.0, 1j)           # Cayley 変換 (z-i)/(z+i)
    print(f"   Möbius(Cayley): 実軸 → 単位円 max||w|-1| = {np.abs(np.abs(cay) - 1).max():.2e}"
          f"、i → {M.cplx_mobius(np.array([1j]), 1.0, -1j, 1.0, 1j)[0]}")
    assert np.abs(np.abs(cay) - 1.0).max() < 1e-12

    # ---------------------------------------------------------------- #
    # 6) Cauchy-Riemann 残差: 「この場は正則か」を 1 つの数で           #
    # ---------------------------------------------------------------- #
    g = np.linspace(-1.0, 1.0, 41)
    h = float(g[1] - g[0])
    X, Y = np.meshgrid(g, g)                            # 行 = 虚部が増える向き
    Z = X + 1j * Y
    r_holo = M.cplx_cr_residual(Z ** 2, spacing=h)
    r_conj = M.cplx_cr_residual(np.conj(Z), spacing=h)
    r_cubic = M.cplx_cr_residual(Z ** 3, spacing=h)
    print(f"6) CR 残差: z²={r_holo:.2e}(正則=0) conj(z)={r_conj:.3f}(=2) "
          f"z³={r_cubic:.2e}(離散化の床 O(h²))")
    assert r_holo < 1e-12 and abs(r_conj - 2.0) < 1e-12

    print("PASS: 複素解析 op 10 個が全て閉形式の真値と一致")


if __name__ == "__main__":
    main()
