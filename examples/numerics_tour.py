# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""numerics_tour — 数値計算の古典を「失敗する側」と並べて見る(Runge・Verlet・低食い違い列・Gauss・erf)。

    py -3.11 examples/numerics_tour.py

【この例が示すこと】(どの節も、うまくいく方法とうまくいかない方法を同じ軸に並べる)
1. **Runge 現象** —— 1/(1+25x²) を多項式で補間する。点を等間隔に置くと、点を増やすほど端で暴れる
   (41 点で誤差 10⁵)。Chebyshev 点(端に寄せる)なら増やすほど収束する。
2. **シンプレクティック積分** —— 振り子(調和振動子)を長く回す。陽的 Euler は位相空間で外へ渦を巻いて
   エネルギーが指数的に増える。速度 Verlet は閉じた輪を保つ。RK4 は短時間なら Verlet より正確だが、
   エネルギー誤差が時間に比例して増え、いずれ Verlet に抜かれる。
3. **低食い違い列** —— 同じ点数でも、乱数には「隙間と塊」がある。Sobol 列は隙間なく埋まり、
   積分誤差の減り方が N^{−1/2}(乱数)より速い(ここでは ≈ N^{−1})。
4. **Gauss 求積** —— n 点で 2n−1 次の多項式まで厳密。2n 次で初めて誤差が出る。
5. **誤差関数** —— ガウスでぼけた段差の形は ½(1 + erf(x/(σ√2)))。画像の「ぼけた縁」の正体。
6. **QR 分解の 3 つの作り方** —— 同じ行列を古典 Gram–Schmidt・修正 Gram–Schmidt・Householder で直交化する。
   紙の上では同じ答えだが、行列が悪条件(条件数 κ が大きい)になると、古典は直交性を κ² の速さで失い κ = 1e9 で
   完全に崩れる。修正は κ の速さ、Householder は丸め誤差のまま。ライブラリが Householder を使う理由。

7. **2 次元の Runge 現象** —— 1/(1 + 25(x² + y²)) を格子の点で補間する。等間隔の格子では点を増やすほど
   四隅が爆発し(25×25 で誤差 8e5)、Chebyshev の格子(fs.chebyshev_coeffs_nd)では減り続ける。画像の照明むらのような
   滑らかな面を少数の係数で表すときの点の置き方。

【グラウンドトゥルース】すべて閉じた式か定理(Runge 関数・調和振動子の円軌道と (1+ω²dt²)^n・積分 = 1・
単項式の積分・erf の導関数)。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs      # noqa: E402
import fullseye as fs          # noqa: E402  公開経路(fs.<名前>)から呼ぶ


def _runge(t):
    return 1.0 / (1.0 + 25.0 * t * t)


def _scatter_image(P, size=220):
    """点集合 (N,2) ⊂ [0,1]² を白地の画像に打つ(隙間と塊を目で見るため、点は 1 画素ではなく 3×3)。"""
    img = np.ones((size, size))
    ij = np.clip((P * (size - 1)).round().astype(int), 0, size - 1)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            img[np.clip(size - 1 - ij[:, 1] + di, 0, size - 1), np.clip(ij[:, 0] + dj, 0, size - 1)] = 0.0
    return img


def run() -> dict:
    t0 = time.perf_counter()
    out = {}

    # ---- 1. Runge ----------------------------------------------------------------- #
    xe = np.linspace(-1, 1, 2001)
    ns = (5, 9, 13, 17, 21, 29, 41)
    eq_err, ch_err = [], []
    for n in ns:
        eq, ch = np.linspace(-1, 1, n), fs.chebyshev_nodes(n)
        eq_err.append(float(np.abs(fs.interp_barycentric(eq, _runge(eq), xe) - _runge(xe)).max()))
        ch_err.append(float(np.abs(fs.interp_barycentric(ch, _runge(ch), xe) - _runge(xe)).max()))
    print("1) Runge: 点 %d→%d で 等間隔の最大誤差 %.1e→%.1e / Chebyshev %.1e→%.1e"
          % (ns[0], ns[-1], eq_err[0], eq_err[-1], ch_err[0], ch_err[-1]))
    assert eq_err[-1] > 1e3 and ch_err[-1] < 1e-3 and ch_err == sorted(ch_err, reverse=True)
    out.update(runge_equispaced=eq_err[-1], runge_chebyshev=ch_err[-1])

    # ---- 2. Euler / Verlet / RK4 ----------------------------------------------------- #
    dt = 0.1
    short = {m: fs.integrate_hamiltonian([1.0], [0.0], dt, 300, method=m) for m in ("euler", "verlet", "rk4")}
    # 長時間は dt=0.2(dt=0.1 だと RK4 が Verlet を追い抜くのが約 18 万歩目で、図に入らない)。
    longrun = {m: fs.integrate_hamiltonian([1.0], [0.0], 0.2, 40_000, method=m) for m in ("verlet", "rk4")}
    # 「それまでの最大誤差」(包絡)で比べる。誤差そのものは振動して 0 をまたぎ、対数が下に跳ねて読めない。
    drift = {m: np.maximum.accumulate(np.abs(r["energy"] - r["energy"][0]) / r["energy"][0]) for m, r in longrun.items()}
    cross = int(np.argmax(drift["rk4"] > drift["verlet"]))
    print("2) 振動子(dt=%.1f): 300 歩で Euler のエネルギー %.1f 倍 / Verlet の誤差 %.1e / RK4 %.1e。"
          "dt=0.2 で長く回すと RK4 の誤差が Verlet を超えるのは t ≈ %.0f"
          % (dt, short["euler"]["energy"][-1] / 0.5, short["verlet"]["energy_drift"], short["rk4"]["energy_drift"],
             cross * 0.2))
    assert short["euler"]["energy"][-1] / 0.5 > 10 and short["verlet"]["energy_drift"] < 3e-3 and cross > 0
    out.update(rk4_overtaken_at_t=cross * 0.2)

    # ---- 3. 低食い違い列 ----------------------------------------------------------------- #
    f = lambda P: np.prod(np.exp(P), axis=1) / (math.e - 1) ** 2           # noqa: E731  積分 = 1(非対称)
    NS = [64, 256, 1024, 4096, 16384]
    rnd = [math.sqrt(np.mean([(f(fs.low_discrepancy(n, 2, "random", seed=s)).mean() - 1) ** 2 for s in range(20)]))
           for n in NS]
    sob = [abs(f(fs.low_discrepancy(n, 2, "sobol")).mean() - 1) for n in NS]
    s_r = float(np.polyfit(np.log(NS), np.log(rnd), 1)[0])
    s_s = float(np.polyfit(np.log(NS), np.log(sob), 1)[0])
    print("3) 積分誤差の傾き: 乱数 %.2f(理論 −0.5)/ Sobol %.2f" % (s_r, s_s))
    assert -0.62 < s_r < -0.38 and s_s < -0.8
    out.update(slope_random=s_r, slope_sobol=s_s)

    # ---- 4. Gauss 求積 ------------------------------------------------------------------ #
    rows = []
    for n in (2, 3, 4, 5):
        q = fs.gauss_quadrature(n)
        errs = [abs(np.sum(q["weights"] * q["nodes"] ** k) - (0.0 if k % 2 else 2.0 / (k + 1))) for k in range(2 * n + 1)]
        assert max(errs[:2 * n]) < 1e-13 and errs[2 * n] > 1e-9
        rows.append([str(n), str(2 * n - 1), "%.0e" % max(errs[:2 * n]), "%.2e" % errs[2 * n]])
    print("4) Gauss: n 点で 2n−1 次まで誤差 ≤ 1e−13、2n 次で初めて誤差(n=5 で %s)" % rows[-1][3])

    # ---- 5. erf = ぼけた段差 ---------------------------------------------------------------- #
    sigma = 1.5
    x = np.arange(-20, 21, dtype=float)
    step = (x >= 0).astype(float)
    k = np.exp(-np.arange(-15, 16) ** 2 / (2 * sigma ** 2))
    blurred = np.convolve(np.pad(step, 15, mode="edge"), k / k.sum(), mode="valid")
    model = 0.5 * (1 + fs.erf((x + 0.5) / (sigma * math.sqrt(2))))         # 画素の境界は x = −0.5
    eerr = float(np.abs(blurred - model).max())
    print("5) ぼけた段差 と ½(1+erf): 最大差 %.1e(離散のガウスと連続の erf の差)" % eerr)
    assert eerr < 1e-2                                  # 離散の核の標本化ぶん(実測 4.6e-3)
    out["erf_edge_err"] = eerr

    # ---- 6. QR の 3 つの作り方 ---------------------------------------------------------- #
    rng_q = np.random.default_rng(1)
    Uq, _ = np.linalg.qr(rng_q.standard_normal((40, 12)))
    Vq, _ = np.linalg.qr(rng_q.standard_normal((12, 12)))
    kap = np.arange(0, 13)
    qloss = {m: [] for m in ("cgs", "mgs", "householder")}
    for k in kap:
        Aq = Uq @ np.diag(np.logspace(0, -float(k), 12)) @ Vq.T
        for m in qloss:
            qloss[m].append(fs.mat_qr(Aq, m)["orthogonality_loss"])
    print("6) 直交性の損失 max|QᵀQ − I|(κ = 1e4 / 1e9): 古典 GS %.0e / %.0e、修正 GS %.0e / %.0e、Householder %.0e / %.0e"
          % (qloss["cgs"][4], qloss["cgs"][9], qloss["mgs"][4], qloss["mgs"][9],
             qloss["householder"][4], qloss["householder"][9]))
    assert qloss["cgs"][9] > 0.5 and qloss["mgs"][9] < 1e-6 and max(qloss["householder"]) < 1e-14
    out.update(qr_loss_cgs_k9=qloss["cgs"][9], qr_loss_mgs_k9=qloss["mgs"][9])

    # ---- 7. 2 次元の Runge 現象 ------------------------------------------------------------ #
    def _runge2(X, Y):
        return 1.0 / (1.0 + 25.0 * (X ** 2 + Y ** 2))
    gq = np.linspace(-1, 1, 161)
    true2 = _runge2(*np.meshgrid(gq, gq, indexing="ij"))
    r2_n = [9, 13, 17, 25]
    r2_eq, r2_ch, show = [], [], {}
    for nn in r2_n:
        ee = np.linspace(-1, 1, nn)
        Vg = _runge2(*np.meshgrid(ee, ee, indexing="ij"))
        tmp = np.array([fs.interp_barycentric(ee, Vg[:, j], gq) for j in range(nn)]).T
        Eq = np.array([fs.interp_barycentric(ee, tmp[i], gq) for i in range(gq.size)])
        cn = fs.chebyshev_nodes(nn)
        Ch = fs.chebyshev_eval_nd(fs.chebyshev_coeffs_nd(_runge2(*np.meshgrid(cn, cn, indexing="ij"))), (gq, gq))
        r2_eq.append(float(np.abs(Eq - true2).max()))
        r2_ch.append(float(np.abs(Ch - true2).max()))
        if nn == 13:
            show = {"eq": Eq, "ch": Ch, "ee": ee, "cn": cn}
    print("7) 2 次元の Runge(最大誤差、点 %s): 等間隔 %s / Chebyshev %s"
          % ("・".join("%d²" % v for v in r2_n), " ".join("%.0e" % v for v in r2_eq), " ".join("%.0e" % v for v in r2_ch)))
    assert r2_eq[-1] > 1e4 and r2_ch[-1] < 1e-2 and all(a > b for a, b in zip(r2_ch, r2_ch[1:])) and len(r2_ch) == 4
    out.update(runge2d_equi_25=r2_eq[-1], runge2d_cheb_25=r2_ch[-1])

    # ---- 図 --------------------------------------------------------------------------- #
    if figs.enabled():
        n_show = 11                                   # 暴れ方が枠に収まる点数(13 点で −3.6 まで振れる)
        eq, ch = np.linspace(-1, 1, n_show), fs.chebyshev_nodes(n_show)
        figs.save_plot("runge_curves",
                       [("等間隔 %d 点で補間" % n_show, xe, fs.interp_barycentric(eq, _runge(eq), xe)),
                        ("Chebyshev %d 点で補間" % n_show, xe, fs.interp_barycentric(ch, _runge(ch), xe)),
                        ("真の関数 1/(1+25x²)", xe, _runge(xe))],
                       styles=[None, None, "dashed"], ylim=(-0.4, 2.1),
                       xlabel="x", ylabel="y", title="Runge 現象 —— 同じ点数でも、点の置き方で結果が変わる",
                       caption="点を等間隔に置くと、真ん中は合うのに端で大きく暴れる。Chebyshev 点(端に寄せた置き方)"
                               "では全体で真の関数(破線)に重なる。")
        figs.save_plot("runge_errors",
                       [("等間隔", list(ns), np.log10(eq_err)), ("Chebyshev", list(ns), np.log10(ch_err))],
                       xlabel="補間に使う点の数", ylabel="log10(最大誤差)",
                       title="点を増やすと —— 等間隔は悪化、Chebyshev は改善",
                       caption="「データを増やせば良くなる」は点の置き方しだい。41 点で等間隔は %.0e、Chebyshev は %.0e。"
                               % (eq_err[-1], ch_err[-1]))
        th = np.linspace(0, 2 * math.pi, 200)
        figs.save_plot("phase_space",
                       [("陽的 Euler", short["euler"]["q"][:, 0], short["euler"]["p"][:, 0]),
                        ("速度 Verlet", short["verlet"]["q"][:, 0], short["verlet"]["p"][:, 0]),
                        ("真の軌道(半径 1 の円)", np.cos(th), np.sin(th))],
                       styles=[None, None, "dashed"], size=(520, 480),
                       xlabel="位置 q", ylabel="運動量 p",
                       title="位相空間 —— Euler は外へ渦を巻き、Verlet は輪を保つ",
                       caption="同じ刻み dt=0.1 で 300 歩。Euler はエネルギーが毎歩 (1+dt²) 倍に増え、外へ逃げる。"
                               "Verlet は少し歪んだ楕円の上を回り続ける(エネルギー誤差は有界)。")
        tt = longrun["verlet"]["t"]
        sel = np.unique(np.geomspace(1, tt.size - 1, 400).astype(int))
        figs.save_plot("energy_drift",
                       [("RK4", np.log10(tt[sel]), np.log10(drift["rk4"][sel] + 1e-18)),
                        ("速度 Verlet", np.log10(tt[sel]), np.log10(drift["verlet"][sel] + 1e-18))],
                       xlabel="log10(時間 t)", ylabel="log10(それまでの最大の相対誤差)",
                       title="長く回すと —— RK4 の誤差は増え続け、Verlet は頭打ち",
                       caption="短い時間なら RK4 のほうが 1 桁以上正確。でも RK4 の誤差は時間に比例して増え、"
                               "t ≈ %.0f で Verlet を超える(dt=0.2)。Verlet の誤差は振動するだけで増えない。" % (cross * 0.2))
        figs.save_grid("points",
                       [_scatter_image(fs.low_discrepancy(512, 2, "random", seed=1)),
                        _scatter_image(fs.low_discrepancy(512, 2, "sobol"))],
                       ["一様乱数 512 点", "Sobol 列 512 点"], ncols=2, gray=True,
                       title="同じ 512 点 —— 乱数には隙間と塊がある",
                       caption="乱数(左)は偶然の隙間と塊ができる。Sobol 列(右)は隙間を順番に埋めるように点を置く。")
        figs.save_plot("qmc_rate",
                       [("乱数(20 回の二乗平均)", np.log10(NS), np.log10(rnd)),
                        ("Sobol 列", np.log10(NS), np.log10(sob)),
                        ("傾き −1/2 の参照", np.log10(NS), np.log10(rnd[0]) - 0.5 * np.log10(np.asarray(NS) / NS[0])),
                        ("傾き −1 の参照", np.log10(NS), np.log10(sob[0]) - np.log10(np.asarray(NS) / NS[0]))],
                       styles=[None, None, "dashed", "dashed"],
                       xlabel="log10(点の数 N)", ylabel="log10(積分誤差)",
                       title="点を 4 倍にすると —— 乱数は誤差 1/2、Sobol は 1/4 前後",
                       caption="∫∫ e^{x+y} dx dy を点の平均で求める。傾き: 乱数 %.2f、Sobol %.2f。" % (s_r, s_s))
        figs.save_plot("erf_edge",
                       [("ガウスでぼかした段差(画素)", x, blurred),
                        ("½(1 + erf(x / σ√2))", x, model)],
                       kinds=["scatter", "line"], styles=[None, "dashed"],
                       xlabel="画素の位置 x", ylabel="明るさ",
                       title="ぼけた縁の形は誤差関数 —— σ = %.1f" % sigma,
                       caption="白黒の段差をガウスでぼかすと、断面は erf の形になる。縁の幅から σ(ぼけの大きさ)が測れる。")
        figs.save_table("gauss", ["点の数 n", "厳密な次数 2n−1", "その次数までの最大誤差", "2n 次の誤差"], rows,
                        title="Gauss–Legendre 求積 —— n 点で 2n−1 次まで厳密")
        eps = np.finfo(float).eps
        floor = 1e-17
        figs.save_plot("qr_orthogonality",
                       [("ε·κ²(傾き 2)", kap[kap <= 8], np.log10(eps * 10.0 ** (2 * kap[kap <= 8]))),
                        ("ε·κ(傾き 1)", kap, np.log10(eps * 10.0 ** kap)),
                        ("古典 Gram–Schmidt", kap, np.log10(np.array(qloss["cgs"]) + floor)),
                        ("修正 Gram–Schmidt", kap, np.log10(np.array(qloss["mgs"]) + floor)),
                        ("Householder(fs.mat_qr の既定)", kap, np.log10(np.array(qloss["householder"]) + floor))],
                       styles=["dashed", "dotted", None, None, None],
                       colors=["neutral", "neutral", "wrong", "right", "emphasis"],
                       ylim=(-17, 1), xlabel="log10(条件数 κ)", ylabel="log10 max|Q^T Q − I|(直交性の損失)",
                       title="同じ QR でも作り方で直交性の崩れ方が違う",
                       caption="40×12 の行列の特異値を 1 から 10^−k まで並べ、k を 0〜12 に振る。古典 Gram–Schmidt は ε·κ²(破線)に"
                               "沿って崩れ、κ = 1e9 で直交性が完全に無くなる(損失 %.2f)。修正 Gram–Schmidt は ε·κ(点線)に沿う。"
                               "Householder は κ によらず %.0e。3 つとも A = QR 自体は丸め誤差で成り立つ —— 崩れるのは Q だけ。"
                               % (qloss["cgs"][9], max(qloss["householder"])))

        def _dots(img, xs):
            out_ = np.asarray(img, float).copy()
            idx = np.rint((xs + 1) / 2 * (gq.size - 1)).astype(int)
            for i in idx:
                for j in idx:
                    out_[max(i - 1, 0):i + 2, max(j - 1, 0):j + 2] = out_.max() if out_.max() > 0 else 1.0
            return out_
        figs.save_grid("runge_2d",
                       [true2, show["eq"], show["ch"], _dots(np.zeros_like(true2), show["cn"]),
                        np.abs(show["eq"] - true2), np.abs(show["ch"] - true2)],
                       ["真の面 1/(1+25(x²+y²))", "等間隔 13×13 の補間", "Chebyshev 13×13 の補間(fs.chebyshev_coeffs_nd)",
                        "Chebyshev の点の置き方(端ほど密)", "等間隔の誤差", "Chebyshev の誤差(同じ目盛り)"],
                       ncols=3, vrange=[(0, 1)] * 3 + [(0, 1), (0, 0.5), (0, 0.5)],
                       title="2 次元の Runge 現象 —— 点を等間隔に置くと四隅が爆発する",
                       caption="同じ 169 個の値から面を作る。等間隔の格子では四隅で振動が爆発し(最大誤差 %.0f、上段中は 0〜1 で切っている)、"
                               "Chebyshev の格子(端に向かって密)では最大 %.2f。点を 25×25 に増やすと等間隔は %.0e まで悪化し、"
                               "Chebyshev は %.3f まで下がる。"
                               % (r2_eq[1], r2_ch[1], r2_eq[-1], r2_ch[-1]))
        figs.save_plot("runge_2d_convergence",
                       [("等間隔の格子", np.array(r2_n), np.log10(r2_eq)), ("Chebyshev の格子", np.array(r2_n), np.log10(r2_ch))],
                       colors=["wrong", "emphasis"], xlabel="各軸の点の数", ylabel="log10(最大誤差)",
                       title="点を増やしたときの誤差 —— 等間隔は増え、Chebyshev は減る",
                       caption="Chebyshev の減り方は関数の極(x² + y² = −1/25)が実軸に近いほど遅い(Bernstein の楕円)。"
                               "それでも点を増やせば必ず減る。等間隔は増やすほど悪くなる。")
    assert not figs.errors(), figs.errors()

    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  numerics_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()
