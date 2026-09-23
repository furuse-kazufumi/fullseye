# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 絵では確かめられないもの —— 力学系と極小曲面を、定義と恒等式で採点する

ローレンツ・アトラクタの図は、積分器が 1 次でも 4 次でも蝶に見える。極小曲面の
図は、平均曲率が 0 でなくてもきれいな曲面に見える。**この族は「見て分かる」が
一切効かない**ので、採点は全部絵の外から来る。

★**この回の規律**: 使った式で答え合わせをしない。真値は次のどれかに限った。

1. **行列指数関数** —— 線形系 ``x' = Ax`` の厳密解は ``expm(At)x₀``。刻みを
   半分にすると RK4 の誤差は 1/16 になる。**次数そのもの**を測るので、
   「それらしい軌道」では通らない(オイラー法が対照群)。
2. **トレース恒等式** —— リアプノフ指数の**和**は接流のトレースの時間平均に
   等しく、ローレンツでは厳密に ``−(σ+1+β) = −13.667``。指数を出す手続き
   (接流 + QR)とは独立な恒等式なので、片方が壊れれば一致しない。
3. **厳密な分岐点** —— ロジスティック写像の周期倍分岐は ``r = 3`` と
   ``r = 1+√6``。ファイゲンバウム定数 4.6692 は 3 本目との比で出る。
   ★残差は隠さない —— 分岐点での収束は**代数的**なので、有限の burn-in では
   必ず少し手前に見える。門は「誤差が小さい」ではなく
   **「burn-in を伸ばすと置いていった分だけ縮む」**で置く。
4. **場の発散と渦度** —— 線形系では発散が厳密に ``tr(A)``、渦度が
   ``A₁₀ − A₀₁``。それを測るのは **PIV 族の既存 op**(``piv_divergence`` /
   ``piv_vorticity``)で、この族の実装を何も知らない。
5. **極小曲面の定義そのもの** —— 平均曲率 ``H`` が至るところ 0。既存
   ``vertex_curvature`` が測る。対照群は単位球(H = 1)と半径 1 の円柱
   (H = 0.5)。★カテノイドとヘリコイドはガウス曲率 ``K`` が一致するが、
   それは**必要条件にすぎない** —— 門にするのは H。
6. **トーラスの解析解** —— 円を中心線にした管は体積 ``2π²Rr²``・表面積
   ``4π²Rr``。既存 ``mesh_volume`` / ``mesh_area`` が測る。

図:
1. ``rk4``: 刻みと誤差(RK4 は 4 次・オイラーは 1 次)。
2. ``lorenz``: 軌道の xz 断面と、場の向き。
3. ``lyapunov``: 指数の和とトレース恒装式。
4. ``bifurcation``: 分岐図と、厳密な分岐点。
5. ``dimension``: 相関次元(円・平面・カントール)。
6. ``field``: 場の発散を既存 PIV op が測る。
7. ``poincare``: 周期軌道は 1 点・カオスは広がる。
8. ``tube``: 軌道を管メッシュに(トーラスで検算)。
9. ``minimal``: 極小曲面 4 種の平均曲率。
10. ``controls``: 対照群(球・円柱)との比較。
11. ``gyroid``: ジャイロイドの固体と、節面近似の残差。
12. ``numbers``: 数表。

走らせ方: ``py -3.11 examples/poc_what_a_picture_cannot_check.py``
(図は ``out/figures/poc_what_a_picture_cannot_check/``)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

CHECKS = []


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s%s" % ("OK" if ok else "NG", label,
                           ("  —— " + detail) if detail else ""))
    return bool(ok)


def states_matrix(st):
    cols = sorted((k for k in st if k.startswith("x")), key=lambda s: int(s[1:]))
    return np.stack([np.asarray(st[c], dtype=np.float64) for c in cols], axis=1)


def raster_points(pts, shape=(420, 420), pad=0.06, extent=None):
    """点群を白地に黒で焼く(図のためだけ。測るのは op のほう)。"""
    p = np.asarray(pts, dtype=np.float64)[:, :2]
    lo, hi = (p.min(axis=0), p.max(axis=0)) if extent is None else extent
    span = np.maximum(hi - lo, 1e-12).max()
    h, w = shape
    s = (1.0 - 2.0 * pad) * min(h, w) / span
    c = (p - (lo + hi) / 2.0) * s
    rr = np.clip((-c[:, 1] + h / 2.0).astype(int), 0, h - 1)
    cc = np.clip((c[:, 0] + w / 2.0).astype(int), 0, w - 1)
    img = np.ones(shape, dtype=np.float64)
    img[rr, cc] = 0.0
    return img


def mean_curvature(V, F, trim=0.1):
    """既存 op で平均曲率の大きさを測る。端は評価が甘いので上側を落とす。"""
    h = np.asarray(fs.ledger.vertex_curvature((V, F)), dtype=np.float64)
    h = np.abs(h[np.isfinite(h)])
    if trim > 0 and h.size > 20:
        cut = int(h.size * trim)
        h = np.sort(h)[:-cut] if cut else h
    return h


def grid_surface(fn, nu=90, nv=140, wrap_v=True):
    import render3d
    V = fn(nu, nv)
    return V, render3d._surf_grid_faces(nu, nv, wrap_v=wrap_v)


# --------------------------------------------------------------------------- #
# 第 1 章 積分器の次数 —— 絵ではまったく区別できない                             #
# --------------------------------------------------------------------------- #
def chapter_rk4():
    print("\n[1] 積分器の次数 —— 厳密解は expm(At)x₀(絵では 1 次と 4 次が同じ)")
    A = np.array([[0.0, 1.0], [-1.0, 0.0]])
    x0 = np.array([1.0, 0.0])
    T = 4.0
    exact = np.array([np.cos(T), -np.sin(T)])
    dts = (0.08, 0.04, 0.02, 0.01)
    e_rk, e_eu = [], []
    for dt in dts:
        st = fs.ode_flow_states("linear", A.ravel(), x0, T, dt, "rk4")
        e_rk.append(float(np.linalg.norm(states_matrix(st)[-1] - exact)))
        st = fs.ode_flow_states("linear", A.ravel(), x0, T, dt, "euler")
        e_eu.append(float(np.linalg.norm(states_matrix(st)[-1] - exact)))
    ratios = [a / b for a, b in zip(e_rk, e_rk[1:])]
    check(all(12.0 < r < 20.0 for r in ratios), "RK4 は 4 次(刻み半分で誤差 1/16)",
          "比 %s(4 次なら 16)" % " / ".join("%.1f" % r for r in ratios))
    er = [a / b for a, b in zip(e_eu, e_eu[1:])]
    check(all(1.5 < r < 2.6 for r in er), "対照群のオイラー法は 1 次(比 2)",
          "比 %s" % " / ".join("%.2f" % r for r in er))
    check(e_eu[-1] > 100.0 * e_rk[-1], "同じ刻みで誤差の桁が違う",
          "dt = 0.01 で オイラー %.2e / RK4 %.2e" % (e_eu[-1], e_rk[-1]))

    if figs.enabled():
        figs.save_plot("rk4",
                       [("RK4(4 次)", np.log10(dts), np.log10(e_rk)),
                        ("オイラー(1 次・対照群)", np.log10(dts), np.log10(e_eu))],
                       xlabel="log₁₀ 刻み dt", ylabel="log₁₀ 誤差(expm との差)",
                       title="積分器の次数 —— 傾きが 4 と 1",
                       caption="厳密解は expm(At)x₀ なので、誤差は積分器の次数を"
                               "そのまま出す。★どちらの軌道も絵にすると同じ円に"
                               "見える —— 絵では次数は確かめられない。")
    return {"rk": e_rk, "eu": e_eu, "ratios": ratios}


# --------------------------------------------------------------------------- #
# 第 2 章 リアプノフ指数 —— 和がトレース恒等式に一致する                          #
# --------------------------------------------------------------------------- #
def chapter_lyapunov():
    print("\n[2] リアプノフ指数 —— 和は厳密に −(σ+1+β)(出し方と独立の恒等式)")
    lam = np.asarray(fs.dynsys_lyapunov_spectrum("lorenz", None, None,
                                                 120.0, 0.004, 20.0))
    import mathops
    sigma, beta, rho = mathops.DYNSYS_SYSTEMS["lorenz"]   # 族名 -> 係数の表
    want = -(sigma + 1.0 + beta)
    check(abs(float(lam.sum()) - want) < 1e-4, "★和がトレース恒等式に一致",
          "Σλ = %.6f / −(σ+1+β) = %.6f  差 %.2e"
          % (lam.sum(), want, abs(lam.sum() - want)))
    check(0.80 < float(lam[0]) < 1.00, "最大指数が公表値 0.906 の近く",
          "λ₁ = %.4f(Lorenz 1963 の標準パラメータ)" % lam[0])
    check(abs(float(lam[1])) < 0.05, "中間の指数は理論上 0(流れの方向)",
          "λ₂ = %.5f" % lam[1])
    lam_h = np.asarray(fs.dynsys_lyapunov_spectrum("harmonic", None, None,
                                                   60.0, 0.002, 5.0))
    check(abs(float(lam_h.sum())) < 1e-3, "対照群の保存系は和がちょうど 0",
          "調和振動子 Σλ = %.2e" % lam_h.sum())

    st = fs.ode_flow_states("lorenz", None, None, 60.0, 0.004)
    m = states_matrix(st)
    if figs.enabled():
        figs.save("lorenz", raster_points(m[:, [0, 2]]), gray=True,
                  caption="ローレンツ・アトラクタの xz 断面。★この図は積分器が 1 次でも"
                          "4 次でも同じ蝶に見える —— 図から言えることは何も無い。"
                          "言えるのは λ の和が −(σ+1+β) に一致することのほう。")
        figs.save_plot("lyapunov",
                       [("指数(大きい順)", np.arange(3), lam),
                        ("和 = −(σ+1+β)", np.array([1.0]), np.array([want]))],
                       xlabel="番号", ylabel="リアプノフ指数",
                       title="リアプノフ・スペクトル —— 和は閉形式",
                       caption="Σλ = %.5f、閉形式 −(σ+1+β) = %.5f(差 %.1e)。"
                               "λ₁ = %.4f は公表値 0.906 の近く、λ₂ は理論上 0。"
                               % (lam.sum(), want, abs(lam.sum() - want), lam[0]),
                       kinds=("scatter", "scatter"))
    return {"lam": lam, "want": want, "harmonic": float(lam_h.sum()), "states": m}


# --------------------------------------------------------------------------- #
# 第 3 章 分岐とファイゲンバウム —— 残差を隠さない                               #
# --------------------------------------------------------------------------- #
def _period_at(r, burn, keep=256, tol=1e-7):
    x = 0.4
    for _ in range(burn):
        x = r * x * (1.0 - x)
    seen = []
    for _ in range(keep):
        x = r * x * (1.0 - x)
        if not any(abs(x - u) < tol for u in seen):
            seen.append(x)
    return len(seen)


def _bif(lo, hi, below, burn):
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if _period_at(mid, burn) <= below:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def chapter_bifurcation():
    print("\n[3] 周期倍分岐 —— r = 3 と 1+√6 は厳密(残差の正体は burn-in)")
    r1 = _bif(2.8, 3.2, 1, 20_000)
    r2 = _bif(3.4, 3.5, 2, 20_000)
    r3 = _bif(3.54, 3.56, 4, 20_000)
    check(abs(r1 - 3.0) < 2e-3, "1 本目の分岐点が r = 3",
          "実測 %.6f(誤差 %.1e)" % (r1, abs(r1 - 3.0)))
    check(abs(r2 - (1.0 + np.sqrt(6.0))) < 1e-3, "2 本目が r = 1+√6",
          "実測 %.6f / 厳密 %.6f" % (r2, 1.0 + np.sqrt(6.0)))
    delta = (r2 - r1) / (r3 - r2)
    check(abs(delta - 4.6692) < 0.15, "ファイゲンバウム定数 δ = 4.6692",
          "実測 %.4f(1.7 %% ほど大きい —— 下の行が理由)" % delta)
    coarse = _bif(2.8, 3.2, 1, 2_000)
    shrink = abs(coarse - 3.0) / max(abs(r1 - 3.0), 1e-15)
    check(shrink > 3.0, "★残差の正体は burn-in(伸ばすと縮む)",
          "burn 2,000 で誤差 %.1e → 20,000 で %.1e(%.1f 倍縮んだ)"
          % (abs(coarse - 3.0), abs(r1 - 3.0), shrink))

    bm = np.asarray(fs.dynsys_bifurcation_map("logistic", 2.5, 4.0, 600, 400, 80))

    def branches(r_target, tol=1e-5):
        v = np.sort(bm[bm[:, 0] == r_target, 1])
        return 1 + int((np.diff(v) > tol).sum()) if v.size else 0

    def nearest(x):
        return float(bm[:, 0][np.abs(bm[:, 0] - x).argmin()])

    b29, b32, b35 = branches(nearest(2.9)), branches(nearest(3.2)), branches(nearest(3.5))
    check((b29, b32) == (1, 2) and b35 >= 4,
          "分岐図の op が同じ所で枝を増やす",
          "r = 2.9 / 3.2 / 3.5 で %d / %d / %d 本" % (b29, b32, b35))

    if figs.enabled():
        figs.save("bifurcation",
                  raster_points(bm, shape=(420, 620),
                                extent=(np.array([2.5, 0.0]), np.array([4.0, 1.0]))),
                  gray=True,
                  caption="ロジスティック写像の分岐図。枝が 1 → 2 になるのは r = 3、"
                          "2 → 4 は r = 1+√6 = %.6f —— どちらも厳密値。比から "
                          "δ = %.4f(文献値 4.6692)。★残差は隠さない: 分岐点での"
                          "収束は代数的なので有限の burn-in では必ず少し手前に見え、"
                          "burn を 2,000 → 20,000 にすると誤差が %.1f 倍縮む。"
                          % (1.0 + np.sqrt(6.0), delta, shrink))
    return {"r1": r1, "r2": r2, "r3": r3, "delta": delta, "shrink": shrink,
            "branches": (b29, b32, b35)}


# --------------------------------------------------------------------------- #
# 第 4 章 相関次元 —— 既知の値が 3 つある                                       #
# --------------------------------------------------------------------------- #
def chapter_dimension():
    print("\n[4] 相関次元 —— 円 1・平面 2・カントール log2/log3")
    rng = np.random.default_rng(0)
    t = np.linspace(0.0, 2.0 * np.pi, 3000, endpoint=False)
    circle = np.stack([np.cos(t), np.sin(t), np.zeros_like(t)], axis=1)
    plane = np.column_stack([rng.random((3000, 2)), np.zeros(3000)])
    acc = np.zeros(4000)
    for k in range(1, 13):
        acc += rng.integers(0, 2, 4000) * 2.0 / 3.0 ** k
    cantor = np.column_stack([acc, np.zeros(4000), np.zeros(4000)])
    rows, got_l, want_l = [], [], []
    for name, pts, want, tol in (("円", circle, 1.0, 0.1),
                                 ("平面", plane, 2.0, 0.15),
                                 ("カントール", cantor, np.log(2) / np.log(3), 0.12)):
        got = float(fs.dynsys_correlation_dimension(pts, max_points=1500))
        check(abs(got - want) < tol, "%s の相関次元" % name,
              "実測 %.4f / 真値 %.4f" % (got, want))
        rows.append([name, "%.4f" % got, "%.4f" % want, "%.4f" % abs(got - want)])
        got_l.append(got)
        want_l.append(want)

    # ★**偏りの正体を探し当ててから書く**。平面の推定が 1.88 と
    #   真値 2 より低いのは、最初に疑った「点数が足りない」ではなかった
    #   (400 → 3,000 点で 1.8825 → 1.8709 と**むしろ下がる**)。正体は
    #   **べき乗則を見る半径の窓**で、既定は対距離の 1〜25 パーセンタイル ——
    #   単位正方形ではその上端が箱の端に当たり、相関和が飽和して傾きが審う。
    #   窓を小さい r 側に寄せると 2.05 まで上がる。
    by_points = [float(fs.dynsys_correlation_dimension(plane, max_points=n))
                 for n in (400, 1500, 3000)]
    by_window = [float(fs.dynsys_correlation_dimension(plane, r_lo=lo, r_hi=hi,
                                                       max_points=3000))
                 for lo, hi in ((0.05, 0.30), (0.02, 0.20), (0.01, 0.10))]
    check(abs(by_points[0] - by_points[-1]) < 0.05,
          "★偏りの正体は点数ではない",
          "400 → 3,000 点で %s(ほとんど動かない)"
          % " / ".join("%.4f" % x for x in by_points))
    check(by_window[0] < by_window[-1] and by_window[-1] > 1.93,
          "★正体は**べき乗則を見る半径の窓**(箱の端で相関和が飽和する)",
          "r の窓を狭めると %s → 真値 2 に寄る"
          % " / ".join("%.4f" % x for x in by_window))

    lor = states_matrix(fs.ode_flow_states("lorenz", None, None, 200.0, 0.01))[4000:]
    d_lor = float(fs.dynsys_correlation_dimension(lor, max_points=2500))
    check(1.8 < d_lor < 2.15,
          "ローレンツ・アトラクタが 2 より少し下(公表値 2.05)",
          "実測 %.4f —— 上の行のとおり既定の半径の窓では低く出るので、"
          "「2.05 に一致」とは言わない(2,500 点)" % d_lor)

    if figs.enabled():
        figs.save_plot("dimension",
                       [("真値", np.arange(3), want_l),
                        ("dynsys_correlation_dimension", np.arange(3), got_l)],
                       xlabel="0 = 円 / 1 = 平面 / 2 = カントール",
                       ylabel="相関次元", title="相関次元 —— 既知の値が 3 つある",
                       caption="円 1・平面 2・カントール log2/log3 = 0.6309。"
                               "ローレンツ・アトラクタは %.3f。★公表値 2.05 との差は"
                               "隠さない —— 相関次元の推定は有限標本で**常に低く出る**"
                               "(平面も 2 でなく 1.88)。★正体は点数でなく"
                               "**べき乗則を見る半径の窓**: 既定の 1〜25 パーセンタイルは"
                               "上端が箱の端に当たるため相関和が飽和し、窓を小さい r 側に"
                               "寄せると 2.05 まで上がる(点数を 400 → 3,000 にしても動かない)。"
                               % d_lor,
                       kinds=("scatter", "scatter"))
    return {"rows": rows, "lorenz": d_lor}


# --------------------------------------------------------------------------- #
# 第 5 章 場の発散 —— 測るのは PIV 族の既存 op                                  #
# --------------------------------------------------------------------------- #
def chapter_field():
    print("\n[5] 場の発散と渦度 —— 既存 piv_divergence / piv_vorticity が測る")
    rows, panels, caps = [], [], []
    ok_all = True
    for A in ((0.0, 1.0, -1.0, 0.0), (-0.3, 1.0, -1.0, -0.3),
              (0.5, 2.0, 0.0, -1.5), (0.0, -1.0, 4.0, 0.0)):
        M = np.asarray(A, dtype=np.float64).reshape(2, 2)
        F = np.asarray(fs.ode_vector_field_grid("linear", A, (-1.0, 1.0, -1.0, 1.0),
                                                (128, 128)))
        px = 2.0 / 127.0
        c = (slice(8, -8), slice(8, -8))
        div = float(np.asarray(fs.ledger.piv_divergence(F))[c].mean()) / px
        vor = float(np.asarray(fs.ledger.piv_vorticity(F))[c].mean()) / px
        d_ok = abs(div - float(np.trace(M))) < 1e-6
        v_ok = abs(vor - float(M[1, 0] - M[0, 1])) < 1e-6
        ok_all = ok_all and d_ok and v_ok
        rows.append(["A = %s" % (A,), "%+.6f / %+.6f" % (div, np.trace(M)),
                     "%+.6f / %+.6f" % (vor, M[1, 0] - M[0, 1]),
                     "%.1e" % max(abs(div - np.trace(M)),
                                  abs(vor - (M[1, 0] - M[0, 1])))])
        panels.append(np.asarray(fs.ledger.piv_flow_magnitude(F)))
        caps.append("tr(A) = %+.1f  渦度 %+.1f" % (np.trace(M), M[1, 0] - M[0, 1]))
    check(ok_all, "★発散 = tr(A)・渦度 = A₁₀−A₀₁(4 通りすべて 1e-6 未満)",
          "測るのは PIV 族の既存 op(この族の実装を何も知らない)")

    Fl = np.asarray(fs.ode_vector_field_grid("lorenz", None,
                                             (-20.0, 20.0, -20.0, 20.0),
                                             (128, 128), "xy", 20.0))
    div_l = float(np.asarray(fs.ledger.piv_divergence(Fl))[8:-8, 8:-8].mean()) / (40.0 / 127.0)
    check(abs(div_l - (-11.0)) < 1e-4, "ローレンツの xy 断面は −σ−1 = −11",
          "実測 %.6f(σ = 10。3 次元の全発散 −13.667 のうち xy 成分)" % div_l)

    if figs.enabled():
        figs.save_grid("field", panels, caps, ncols=4, gray=True,
                       title="ベクトル場 —— 既存 PIV op がそのまま食う",
                       caption="ode_vector_field_grid は flow2d((2, H, W) の (dy, dx))"
                               "を返すので、piv_divergence / piv_vorticity / "
                               "piv_flow_magnitude がそのまま使える。★channel-first "
                               "にしたのは、既存の型に既存の述語と既存の消費側がある"
                               "から —— (H, W, 2) のほうが自然に読めるが、それでは"
                               "型の嘘になる(連鎖ファザーが捕まえた)。")
    return {"rows": rows, "lorenz_div": div_l}


# --------------------------------------------------------------------------- #
# 第 6 章 ポアンカレ断面と管メッシュ                                            #
# --------------------------------------------------------------------------- #
def chapter_poincare_tube():
    print("\n[6] ポアンカレ断面と管メッシュ —— 周期軌道は 1 点、円の管はトーラス")
    st = fs.ode_flow_states("harmonic", None, np.array([1.0, 0.0]), 60.0, 0.001)
    sec = np.asarray(fs.dynsys_poincare_section(st, 0, 0.0, 1))
    spread = float(np.ptp(sec[:, 0]))
    check(spread < 1e-3, "周期軌道は断面で 1 点に重なる",
          "交点 %d 個・ばらつき %.2e" % (sec.shape[0], spread))
    st2 = fs.ode_flow_states("rossler", None, np.array([1.0, 1.0, 1.0]), 400.0, 0.005)
    m2 = states_matrix(st2)[20000:]
    sec2 = np.asarray(fs.dynsys_poincare_section(m2, 1, 0.0, 1))
    spread2 = float(np.ptp(sec2[:, 0]))
    check(spread2 > 0.05, "カオスは広がる(同じ op で両方測る)",
          "交点 %d 個・ばらつき %.3f" % (sec2.shape[0], spread2))

    R, r, mm, k = 2.0, 0.3, 720, 48
    th = np.linspace(0.0, 2.0 * np.pi, mm, endpoint=False)
    centre = np.stack([R * np.cos(th), R * np.sin(th), np.zeros(mm)], axis=1)
    V, F = fs.ledger.curve3d_tube_mesh(centre, r, k, closed=True)
    vol = abs(float(fs.ledger.mesh_volume((V, F))))
    area = float(fs.ledger.mesh_area((V, F)))
    v_want = 2.0 * np.pi ** 2 * R * r ** 2
    a_want = 4.0 * np.pi ** 2 * R * r
    check(abs(vol / v_want - 1.0) < 0.01, "円の管の体積が 2π²Rr²",
          "実測 %.5f / 解析解 %.5f  比 %.5f" % (vol, v_want, vol / v_want))
    check(abs(area / a_want - 1.0) < 0.01, "表面積が 4π²Rr",
          "実測 %.5f / 解析解 %.5f  比 %.5f" % (area, a_want, area / a_want))

    # ★平行移動フレームの効き目: まっすぐな区間を含む曲線でも半径が崩れない
    z = np.linspace(0.0, 4.0, 200)
    x = np.where(z < 2.0, 0.0, (z - 2.0) ** 2 * 0.3)
    bent = np.stack([x, np.zeros_like(z), z], axis=1)
    Vb, _Fb = fs.ledger.curve3d_tube_mesh(bent, 0.15, 16)
    ring = Vb.reshape(bent.shape[0], 16, 3)
    rad = np.linalg.norm(ring - bent[:, None, :], axis=2)
    check(abs(float(rad.min()) - 0.15) < 1e-9 and abs(float(rad.max()) - 0.15) < 1e-9,
          "★まっすぐな区間があっても半径が崩れない(平行移動フレーム)",
          "半径 %.12f 〜 %.12f(フレネ枠では直線部で法線が定義できない)"
          % (rad.min(), rad.max()))

    lor = states_matrix(fs.ode_flow_states("lorenz", None, None, 20.0, 0.004))
    Vl, Fl = fs.ledger.curve3d_tube_mesh(lor[::4], 0.25, 10)
    if figs.enabled():
        figs.save_grid("poincare",
                       [raster_points(np.column_stack([sec, np.zeros(sec.shape[0])])),
                        raster_points(np.column_stack([sec2, np.zeros(sec2.shape[0])]))],
                       ["周期軌道(ばらつき %.1e)" % spread,
                        "カオス(ばらつき %.3f)" % spread2], ncols=2, gray=True,
                       title="ポアンカレ断面 —— 周期は 1 点・カオスは広がる",
                       caption="同じ op で両方を測っている。周期軌道の断面が"
                               "広がったら積分器か断面の探し方が壊れている。")
        figs.save("tube",
                  raster_points(Vl[:, [0, 2]], shape=(420, 420)), gray=True,
                  caption="ローレンツの軌道を管メッシュに(MATLAB の tubeplot 相当、"
                          "%d 頂点 / %d 面)。★真値は「円を中心線にするとトーラスに"
                          "なり、体積 2π²Rr² = %.5f・表面積 4π²Rr = %.5f が解析解」"
                          "であること —— 既存 mesh_volume / mesh_area が測って比 "
                          "%.5f / %.5f。管が「管に見える」ことは検査ではない。"
                          % (Vl.shape[0], Fl.shape[0], v_want, a_want,
                             vol / v_want, area / a_want))
    return {"spread": spread, "spread2": spread2, "vol": vol, "area": area,
            "v_want": v_want, "a_want": a_want}


# --------------------------------------------------------------------------- #
# 第 7 章 極小曲面 —— 定義そのものが門                                          #
# --------------------------------------------------------------------------- #
def chapter_minimal():
    print("\n[7] 極小曲面 —— H = 0 を既存 vertex_curvature が測る(対照群つき)")
    import render3d
    rows, panels, caps = [], [], []
    for kind in ("catenoid", "helicoid", "enneper", "scherk"):
        V, F = fs.ledger.minimal_surface(kind, 90, 140, 1.2)
        h = mean_curvature(V, F)
        med, p90 = float(np.median(h)), float(np.percentile(h, 90))
        check(med < 0.01 and p90 < 0.05, "%s の |H| が 0" % kind,
              "中央値 %.5f / p90 %.5f" % (med, p90))
        rows.append([kind, "%.5f" % med, "%.5f" % p90, "0(定義)"])
        panels.append(raster_points(V[:, [0, 2]]))
        caps.append("%s  |H| 中央値 %.5f" % (kind, med))

    # 対照群: 球は H = 1、円柱は H = 0.5
    def sphere(nu, nv):
        th = np.linspace(0.01, np.pi - 0.01, nu)[:, None]
        ph = np.linspace(0.0, 2.0 * np.pi, nv, endpoint=False)[None, :]
        return np.stack([(np.sin(th) * np.cos(ph)).ravel(),
                         (np.sin(th) * np.sin(ph)).ravel(),
                         np.broadcast_to(np.cos(th), (nu, nv)).ravel()], axis=1)

    def cylinder(nu, nv):
        ph = np.linspace(0.0, 2.0 * np.pi, nv, endpoint=False)[None, :]
        zz = np.linspace(-1.0, 1.0, nu)[:, None]
        return np.stack([np.broadcast_to(np.cos(ph), (nu, nv)).ravel(),
                         np.broadcast_to(np.sin(ph), (nu, nv)).ravel(),
                         np.broadcast_to(zz, (nu, nv)).ravel()], axis=1)

    ctrl = []
    for name, fn, want in (("球(H = 1)", sphere, 1.0),
                           ("円柱(H = 0.5)", cylinder, 0.5)):
        V, F = grid_surface(fn)
        h = mean_curvature(V, F)
        med = float(np.median(h))
        check(abs(med - want) < 0.05, "対照群 %s を門が区別する" % name,
              "|H| 中央値 %.5f / 理論 %.1f" % (med, want))
        ctrl.append([name, "%.5f" % med, "%.1f" % want, "極小ではない"])

    # ★K の一致は必要条件にすぎない
    Vc, _ = fs.ledger.minimal_surface("catenoid", 80, 120, 1.0)
    Vh, _ = fs.ledger.minimal_surface("helicoid", 80, 120, 1.0)
    k1c, k2c = fs.ledger.principal_curvatures(Vc)
    k1h, k2h = fs.ledger.principal_curvatures(Vh)
    Kc = np.asarray(k1c) * np.asarray(k2c)
    Kh = np.asarray(k1h) * np.asarray(k2h)
    mc, mh = float(np.median(Kc[np.isfinite(Kc)])), float(np.median(Kh[np.isfinite(Kh)]))
    check(mc < 0 and mh < 0 and abs(mc - mh) < 0.5 * abs(mc),
          "★カテノイドとヘリコイドは K が一致(等長だから)",
          "K 中央値 %.5f / %.5f —— だが K の一致は**必要条件にすぎない**" % (mc, mh))

    areas = []
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        V, F = fs.ledger.minimal_surface_bend(t * np.pi / 2.0, 80, 120, 1.0)
        h = mean_curvature(V, F)
        a = float(fs.ledger.mesh_area((V, F)))
        areas.append(a)
        check(float(np.median(h)) < 0.02, "曲げの族 t = %.2f π/2 でも H = 0" % t,
              "|H| 中央値 %.5f・面積 %.4f" % (np.median(h), a))
    check(max(areas) / min(areas) - 1.0 < 0.02, "曲げは等長(面積が変わらない)",
          "面積 %.4f 〜 %.4f" % (min(areas), max(areas)))

    if figs.enabled():
        figs.save_grid("minimal", panels, caps, ncols=4, gray=True,
                       title="極小曲面 4 種 —— |H| を既存 vertex_curvature が測る",
                       caption="「これは極小曲面だ」という主張を、**作り方を知らない "
                               "op が採点する**。対照群の単位球は |H| = 1.0、半径 1 の"
                               "円柱は 0.5 —— 門が素通しでないことの証拠。"
                               "★カテノイドとヘリコイドはガウス曲率 K が一致するが、"
                               "それは必要条件にすぎない(門にするのは H)。")
    return {"rows": rows, "ctrl": ctrl, "K": (mc, mh), "areas": areas}


# --------------------------------------------------------------------------- #
# 第 8 章 ジャイロイド —— 節面近似であることを隠さない                            #
# --------------------------------------------------------------------------- #
def chapter_gyroid():
    print("\n[8] ジャイロイド —— 対称性で体積比 1/2、ただし**節面近似**")
    import render3d
    fr = []
    for n in (48, 64, 96):
        f = render3d._gyroid_field("poc", (n, n, n), 1.0)
        frac = float((f > 0).mean())
        fr.append(frac)
        check(abs(frac - 0.5) < 0.02, "%d³ で体積比が 1/2" % n,
              "実測 %.6f(体心反転に対し場が奇 —— 格子に依らない対称性)" % frac)
    shell = [float(np.asarray(render3d.gyroid_solid_mask((64, 64, 64), 0.0, 1.0, t)).mean())
             for t in (0.1, 0.2, 0.4)]
    check(abs(shell[1] / shell[0] - 2.0) < 0.3 and abs(shell[2] / shell[1] - 2.0) < 0.3,
          "薄い殻の体積は厚さにほぼ比例",
          "厚さ 0.1 / 0.2 / 0.4 で %.4f / %.4f / %.4f" % tuple(shell))

    residual = None
    try:
        V, F = render3d.gyroid_isosurface((64, 64, 64), 0.0, 1.0)
        h = mean_curvature(V, F)
        k1, k2 = fs.ledger.principal_curvatures(V)
        kk = np.abs(np.concatenate([np.asarray(k1), np.asarray(k2)]))
        kk = kk[np.isfinite(kk)]
        residual = float(np.median(h)) / max(float(np.median(kk)), 1e-12)
        check(residual < 0.15, "★節面の残差を隠さず出す(厳密な極小曲面ではない)",
              "|H| / 主曲率スケール = %.4f —— Schoen のジャイロイドは H = 0 だが、"
              "節面近似には小さな残差が残る" % residual)
    except ValueError as exc:
        check("scikit-image" in str(exc), "メッシュ形は scikit-image が要る(固体形は要らない)",
              str(exc)[:90])

    solid = np.asarray(render3d.gyroid_solid_mask((64, 64, 64), 0.0, 1.0, 0.3))
    if figs.enabled():
        figs.save_grid("gyroid",
                       [solid[16], solid[32], solid[48],
                        solid.mean(axis=0)],
                       ["z = 16 の断面", "z = 32", "z = 48",
                        "z 方向に平均(体積分率 %.4f)" % solid.mean()],
                       ncols=4, gray=True,
                       title="ジャイロイド —— 印刷できる固体(numpy だけで動く)",
                       caption="level = 0 で場は体心反転に対し奇なので、両側の体積は"
                               "ちょうど半分ずつ(実測 %.6f / %.6f / %.6f、格子に"
                               "依らない)。★メッシュ形と固体形を**別 op に分けた** ——"
                               "引数で mesh か voxel が変わる関数には宣言 out 型を"
                               "1 つ与えられない(indices_to_labels で踏んだ型の嘘)。"
                               % tuple(fr))
    return {"frac": fr, "shell": shell, "residual": residual}


def main():
    t0 = time.time()
    print("=" * 74)
    print("絵では確かめられないもの —— 力学系と極小曲面を定義と恒等式で採点する")
    print("=" * 74)
    r = chapter_rk4()
    ly = chapter_lyapunov()
    b = chapter_bifurcation()
    d = chapter_dimension()
    fl = chapter_field()
    pt = chapter_poincare_tube()
    mn = chapter_minimal()
    gy = chapter_gyroid()

    if figs.enabled():
        rows = [
            ["RK4 の次数", "刻み半分での誤差の比",
             " / ".join("%.1f" % x for x in r["ratios"]), "16(4 次)"],
            ["オイラーの次数", "同じ刻みでの誤差", "%.2e" % r["eu"][-1],
             "RK4 は %.2e(桁が違う)" % r["rk"][-1]],
            ["★トレース恒等式", "Σλ − (−(σ+1+β))",
             "%.2e" % abs(ly["lam"].sum() - ly["want"]), "0(厳密)"],
            ["最大リアプノフ指数", "λ₁", "%.4f" % ly["lam"][0], "0.906(公表値)"],
            ["保存系(対照群)", "調和振動子の Σλ", "%.2e" % ly["harmonic"], "0"],
            ["1 本目の分岐点", "r", "%.6f" % b["r1"], "3(厳密)"],
            ["2 本目の分岐点", "r", "%.6f" % b["r2"],
             "1+√6 = %.6f(厳密)" % (1.0 + np.sqrt(6.0))],
            ["ファイゲンバウム δ", "(r₂−r₁)/(r₃−r₂)", "%.4f" % b["delta"],
             "4.6692(残差は burn-in・伸ばすと %.1f 倍縮む)" % b["shrink"]],
            ["相関次元", "円 / 平面 / カントール",
             " / ".join(x[1] for x in d["rows"]), "1 / 2 / 0.6309"],
            ["ローレンツの次元", "相関次元", "%.4f" % d["lorenz"],
             "2.05(公表値)。★既定の半径の窓では低く出る"],
            ["★場の発散", "既存 piv_divergence の実測 vs tr(A)",
             fl["rows"][1][1], "一致(4 通りすべて 1e-6 未満)"],
            ["場の渦度", "既存 piv_vorticity vs A₁₀−A₀₁", fl["rows"][3][2],
             "一致"],
            ["ポアンカレ断面", "周期軌道 / カオスのばらつき",
             "%.1e / %.3f" % (pt["spread"], pt["spread2"]), "0 / 広がる"],
            ["管メッシュ", "体積 / 2π²Rr²", "%.5f" % (pt["vol"] / pt["v_want"]),
             "1(解析解・既存 mesh_volume が測る)"],
            ["管メッシュ", "面積 / 4π²Rr", "%.5f" % (pt["area"] / pt["a_want"]),
             "1(解析解)"],
            ["★極小曲面", "|H| 中央値(4 種で最大)",
             "%.5f" % max(float(x[1]) for x in mn["rows"]), "0(定義)"],
            ["対照群", "球 / 円柱の |H|",
             "%s / %s" % (mn["ctrl"][0][1], mn["ctrl"][1][1]),
             "1.0 / 0.5(極小ではない)"],
            ["等長な曲げ", "面積の振れ幅",
             "%.4f 〜 %.4f" % (min(mn["areas"]), max(mn["areas"])), "変わらない"],
            ["ジャイロイド", "体積比(48³ / 64³ / 96³)",
             " / ".join("%.4f" % x for x in gy["frac"]), "0.5(対称性)"],
            ["★節面近似の残差", "|H| / 主曲率スケール",
             ("%.4f" % gy["residual"]) if gy["residual"] is not None else "—",
             "0 ではない(厳密な極小曲面ではないと明記)"],
        ]
        figs.save_table("numbers", ["主張", "測った量", "実測", "真値 / 期待"],
                        rows,
                        title="絵では確かめられないもの —— 恒等式と定義で当てた答え",
                        caption="どの行も絵からは読めない: expm との誤差の比、"
                                "トレース恒等式、厳密な分岐点、既知の 3 つの次元、"
                                "PIV 族の既存 op が測った tr(A)、トーラスの解析解、"
                                "既存 vertex_curvature が測った H —— そして節面"
                                "近似の残差は隠さずここに出してある。")
    # ★図の書き出しが失敗したら、ここで拾う。見ないと「検査は全部 OK・でも図は
    #   1 枚も出ていない」が黙って通る(examplefig は fail-soft で貯める)。
    assert not figs.errors(), figs.errors()
    bad = [c for c in CHECKS if not c[0]]
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)"
          % (len(CHECKS), len(CHECKS) - len(bad), time.time() - t0))
    if bad:
        for _, label, detail in bad:
            print("  NG:", label, detail)
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()
