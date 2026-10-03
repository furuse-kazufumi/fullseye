# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""estimation_tour — 推定と統計の古典を「ありがちな素朴なやり方」と並べて見る。

    py -3.11 examples/estimation_tour.py

【この例が示すこと】
1. **割当(Hungarian)** —— 2 コマの間で点を結ぶ。各点が「いちばん近い相手」を貪欲に取ると、近い相手を
   先に取られた点が遠くへ飛ばされ、総距離が増えて追跡を取り違える。Hungarian 法は総距離を最小にする。
2. **Kalman 平滑化** —— 雑音の大きい位置の観測から軌跡を戻す。フィルタ(その時刻までのデータ)と平滑化
   (前後のデータ)を真の軌跡と重ねる。平滑化は「全データを一度に使う最小二乗」と厳密に同じ答え。
3. **Cramér–Rao 下界** —— どんな推定でも越えられない精度の壁。直線の当てはめの標準偏差は、データを増やすと
   下界の線(傾き −1/2)の上に乗る。
4. **p 値は帰無仮説の下で一様** —— 差の無い 2 群を何度も比べると、p 値は 0〜1 に平らに散らばり、5% は偶然で
   「有意」になる。
5. **姿勢の補間(SE(3))** —— 2 つの姿勢の間を、4×4 行列を直線で混ぜて補間すると、途中が回転行列でなくなる
   (物体が縮む)。exp/log で「速度」を直線で混ぜれば、途中もずっと剛体のまま。

【グラウンドトゥルース】総当たりの最適割当・一括最小二乗・下界の式 σ²(JᵀJ)⁻¹・一様分布・det R = 1。
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


def _greedy(C):
    """素朴な対応付け: 全組を距離の小さい順に見て、両方が空いていれば結ぶ。"""
    order = np.dstack(np.unravel_index(np.argsort(C, axis=None), C.shape))[0]
    used_r, used_c, pairs = set(), set(), []
    for r, c in order:
        if r not in used_r and c not in used_c:
            used_r.add(int(r))
            used_c.add(int(c))
            pairs.append((int(r), int(c)))
    return np.array(sorted(pairs))


def run() -> dict:
    t0 = time.perf_counter()
    out = {}
    rng = np.random.default_rng(7)

    # ---- 1. 割当 -------------------------------------------------------------------- #
    # 4 点が少しずつ右へ動く。1 点だけ大きく動いて、隣の点の「元の場所」の近くに来る(取り違えの罠)。
    a = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]])
    b = a + np.array([[0.75, 0.25], [0.55, 0.25], [0.6, 0.25], [0.55, 0.25]])
    C = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    hun = fs.assign_hungarian(C)
    gre = _greedy(C)
    g_total = float(C[gre[:, 0], gre[:, 1]].sum())
    print("1) 割当: Hungarian の総距離 %.3f(対応 %s)/ 貪欲 %.3f(対応 %s)"
          % (hun["total"], hun["cols"].tolist(), g_total, gre[:, 1].tolist()))
    assert hun["cols"].tolist() == [0, 1, 2, 3] and g_total > hun["total"] + 1e-9
    out.update(hungarian_total=hun["total"], greedy_total=g_total)

    # ---- 2. Kalman ------------------------------------------------------------------- #
    T, dt = 80, 0.1
    F = np.array([[1.0, dt], [0.0, 1.0]])
    H = np.array([[1.0, 0.0]])
    q = 0.5
    Q = q * np.array([[dt ** 3 / 3, dt ** 2 / 2], [dt ** 2 / 2, dt]])
    R = np.array([[0.4 ** 2]])
    x = np.array([0.0, 1.0])
    truth, z = [], []
    for _ in range(T):
        truth.append(x[0])
        z.append(x[0] + 0.4 * rng.normal())
        x = F @ x + rng.multivariate_normal([0, 0], Q)
    truth, z = np.array(truth), np.array(z)
    z_obs = z.copy()
    z_obs[35:50] = np.nan                                          # 観測が途切れる区間
    ks = fs.kalman_smooth(z_obs[:, None], F, H, Q, R, [0.0, 1.0], np.eye(2))
    e_raw = float(np.sqrt(np.nanmean((z_obs - truth) ** 2)))
    e_f = float(np.sqrt(np.mean((ks["x_filt"][:, 0] - truth) ** 2)))
    e_s = float(np.sqrt(np.mean((ks["x_smooth"][:, 0] - truth) ** 2)))
    print("2) Kalman: 位置の誤差(RMS)観測 %.3f / フィルタ %.3f / 平滑化 %.3f(途切れ区間 15 コマを含む)" % (e_raw, e_f, e_s))
    assert e_s < e_f < e_raw
    out.update(rms_obs=e_raw, rms_filter=e_f, rms_smooth=e_s)

    # ---- 3. Cramér–Rao ---------------------------------------------------------------- #
    th, sig = np.array([1.0, 2.0]), 0.1
    ns = [8, 16, 32, 64, 128, 256]
    sd_mc, sd_cr = [], []
    for n in ns:
        xx = np.linspace(0, 1, n)
        est = np.array([np.polyfit(xx, th[0] + th[1] * xx + sig * rng.normal(size=n), 1)[0] for _ in range(1500)])
        sd_mc.append(float(np.std(est)))
        sd_cr.append(float(fs.crlb_gaussian(xx, th, sig, model="line")["std"][1]))
    ratio = np.array(sd_mc) / np.array(sd_cr)
    print("3) 傾きの標準偏差 / Cramér–Rao 下界 = %s(1 なら下界に到達)" % np.round(ratio, 3))
    assert np.all(np.abs(ratio - 1) < 0.07)

    # ---- 4. 帰無仮説の下の p 値 ----------------------------------------------------------- #
    ps = np.array([fs.stat_ttest_welch(rng.normal(size=15), rng.normal(size=25))["p"] for _ in range(2000)])
    frac = float(np.mean(ps < 0.05))
    print("4) 差の無い 2 群を 2000 回比べると、p < 0.05 は %.1f%%(偶然の「有意」)" % (100 * frac))
    assert 0.035 < frac < 0.065
    out["false_positive_rate"] = frac

    # ---- 5. 姿勢の補間 ------------------------------------------------------------------ #
    T0 = np.eye(4)
    T1 = fs.se3_exp([2.0, 0.5, 0.0, 0.0, 0.0, 2.6])               # z 軸まわり 149° 回して並進
    xi = fs.se3_log(T1)
    s = np.linspace(0, 1, 11)
    det_lin = [float(np.linalg.det(((1 - u) * T0 + u * T1)[:3, :3])) for u in s]
    det_lie = [float(np.linalg.det(fs.se3_exp(u * xi)[:3, :3])) for u in s]
    print("5) 姿勢の補間の途中で det R: 行列を直線で混ぜる 最小 %.3f / exp-log で混ぜる 最小 %.6f"
          % (min(det_lin), min(det_lie)))
    assert min(det_lin) < 0.3 and abs(min(det_lie) - 1) < 1e-12

    # ---- 図 -------------------------------------------------------------------------- #
    if figs.enabled():
        series = [("前のコマの点", a[:, 0], a[:, 1]), ("今のコマの点", b[:, 0], b[:, 1])]
        series += [("Hungarian の対応(総距離 %.2f)" % hun["total"], [a[r, 0], b[c, 0]], [a[r, 1], b[c, 1]])
                   for r, c in hun["pairs"]]
        series += [("貪欲の対応(総距離 %.2f)" % g_total, [a[r, 0], b[c, 0]], [a[r, 1] - 0.03, b[c, 1] - 0.03])
                   for r, c in gre]
        figs.save_plot("assign", series,
                       kinds=["scatter", "scatter"] + ["line"] * 8,
                       styles=[None, None] + [None] * 4 + ["dashed"] * 4,
                       colors=["neutral", "reference"] + ["right"] * 4 + ["wrong"] * 4, ylim=(-0.2, 0.45),
                       xlabel="x", ylabel="y",
                       title="2 コマの点を結ぶ —— 貪欲(破線)は総距離 %.2f、Hungarian(実線)は %.2f" % (g_total, hun["total"]),
                       caption="貪欲は「いま一番近い組」から順に結ぶので、近い相手を先に取られた点が遠くへ飛ばされる。"
                               "Hungarian は総距離が最小になる結び方を厳密に選ぶ(小さな問題では全順列の総当たりと一致)。")
        tt = np.arange(T) * dt
        figs.save_plot("kalman",
                       [("観測(雑音 0.4)", tt[np.isfinite(z_obs)], z_obs[np.isfinite(z_obs)]),
                        ("フィルタ(その時刻まで)", tt, ks["x_filt"][:, 0]),
                        ("平滑化(前後すべて)", tt, ks["x_smooth"][:, 0]),
                        ("真の位置", tt, truth)],
                       kinds=["scatter", "line", "line", "line"], styles=[None, None, None, "dashed"],
                       xlabel="時刻 t", ylabel="位置",
                       title="Kalman —— 観測が途切れても、前後から軌跡を戻す",
                       caption="t = 3.5〜5.0 は観測が無い。フィルタはそこを予測だけで進み、平滑化は後ろのデータで引き戻す。"
                               "誤差(RMS)は 観測 %.2f → フィルタ %.2f → 平滑化 %.2f。" % (e_raw, e_f, e_s))
        figs.save_plot("crlb",
                       [("最小二乗の傾きの標準偏差(1500 回)", np.log10(ns), np.log10(sd_mc)),
                        ("Cramér–Rao 下界", np.log10(ns), np.log10(sd_cr))],
                       kinds=["scatter", "line"], styles=[None, "dashed"],
                       xlabel="log10(データ点の数 n)", ylabel="log10(傾きの標準偏差)",
                       title="精度の壁 —— 点を 4 倍にしても精度は 2 倍(傾き −1/2)",
                       caption="雑音 σ=0.1 の直線の当てはめ。最小二乗は下界(破線)にぴったり乗る = これ以上の精度は"
                               "どんな方法でも出ない(効率的な推定量)。")
        hist, edges = np.histogram(ps, bins=20, range=(0, 1))
        figs.save_plot("pvalues",
                       [("p 値のヒストグラム(2000 回)", 0.5 * (edges[:-1] + edges[1:]), hist),
                        ("一様分布なら", [0, 1], [100, 100])],
                       kinds=["bar", "line"], styles=[None, "dashed"], ylim=(0, 160),
                       xlabel="p 値", ylabel="回数",
                       title="差が無いのに比べ続けると —— p 値は平らに散らばる",
                       caption="同じ分布から取った 2 群を 2000 回比べた。p < 0.05 は %.1f%% —— 「有意」の 5%% は偶然で出る。"
                               "たくさん比べて有意なものだけ報告すると、それは偶然を拾っている。" % (100 * frac))
        figs.save_plot("pose_interp",
                       [("行列を直線で混ぜる", s, det_lin), ("exp / log で混ぜる", s, det_lie),
                        ("剛体なら常に 1", [0, 1], [1, 1])],
                       styles=[None, None, "dashed"], ylim=(-0.05, 1.15),
                       xlabel="補間の割合 s", ylabel="det R(1 なら回転、1 未満は縮み)",
                       title="2 つの姿勢の間 —— 行列を混ぜると物体が縮む",
                       caption="149° 回した姿勢との間を補間する。4×4 行列を (1−s)T₀ + sT₁ で混ぜると、途中で回転行列で"
                               "なくなり体積が %.2f 倍まで縮む。se3_log で速度に直し、直線で混ぜてから se3_exp で戻すと、ずっと剛体。"
                               % min(det_lin))
    assert not figs.errors(), figs.errors()

    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  estimation_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()
