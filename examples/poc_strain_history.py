# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_strain_history — クリープ試験の**ひずみ履歴**(DIC の時系列)。

    py -3.11 examples/poc_strain_history.py

【この PoC が答える問い】
`poc_dic_strain.py` は**1 対のフレーム**で「変位はどこまで測れるか」を測った。
こちらは**時間発展**が主題:「1 時間かけてゆっくり伸びる試験片を 25 コマ
撮った。ひずみ履歴 ε(t) と**ひずみ速度** dε/dt をどう出すか」。

やり方は 2 つしかない。

  * **累積**(ゼロ点) —— 隣り合うコマの変位を毎回測って足し上げる。
    1 回あたりの変形が小さいので相関がよく効く。
  * **直接** —— いつも基準フレーム(t=0)と比べる。誤差が積もらない。

教科書どおりなら「累積は誤差が √T で積もり、直接は変形が大きくなると
相関が落ちる。どちらが良いかは時刻で入れ替わる」。**その交点を実測で出す**
のがこの PoC の中心。

【★★ 番号つき所見(すべて実測。予想が外れたものはそう書く)】
(数字は最終実行の実測値。測ってから書いている。)

【グラウンドトゥルース】
真ひずみ(対数ひずみ)で ``E(t) = A ((t + t0)^n - t0^n)``、``n = 0.4``
(1 次クリープ)。変形は中心まわりの一様な伸び ``x -> xc + (x - xc) e^E``。
**対数ひずみを使うのが要点** —— 増分の和がちょうど全体の真ひずみになるので、
「累積」と「直接」が**同じ量を推定している**ことが代数的に保証される
(工学ひずみだと和が一致せず、比べているのが手法なのか定義なのか
分からなくなる)。

各コマは `pivops.piv_synth_pair` で **粒子を動かしてから描き直す**
(1 枚目を補間で歪めない)。同じ ``seed`` なら粒子は同じなので、
25 コマは 1 本の連続した履歴になる。

【使った既存 op(新しい op は作らない)】
`piv_synth_pair` / `piv_cross_correlate` / `piv_multipass` /
`piv_sample_at_windows` / `piv_error_stats` / `poly_fit` /
`fullseye.moving_average`(中央)/ `ledger.moving_average_window`(因果)。

【90 秒制限】256x256 px・25 コマ・雑音の実現 6 通り(実測は末尾)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import pivops                                                    # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N = 256                 # 画素
T = 25                  # コマ数(t = 0 .. 24、1 コマ = 1 単位時間)
TOFF = 2.0              # クリープ則の時間オフセット(t=0 で速度が発散しない)
NEXP = 0.4              # クリープ指数 n < 1(1 次クリープ)
E_MAX = 0.06            # t = T-1 での真ひずみ(6 % = 60000 µε)
DENSITY = 0.02          # スペックル粒子の密度(piv_synth_pair の既定)
DIAM = 2.5              # 粒子径 [px]
SEED = 4157             # 粒子配置(全コマ共通)
NOISE = 0.02            # 加法ガウス雑音の σ
WINDOW = 32             # PIV の窓
OVERLAP = 0.5

#: ``E(T-1) = E_MAX`` になるクリープ係数。
A_COEF = E_MAX / ((T - 1 + TOFF) ** NEXP - TOFF ** NEXP)

TIMES = np.arange(T, dtype=float)


def true_strain(t):
    """真ひずみ ``E(t) = A ((t+t0)^n - t0^n)``。``E(0) = 0``。"""
    t = np.asarray(t, float)
    return A_COEF * ((t + TOFF) ** NEXP - TOFF ** NEXP)


def true_rate(t):
    """ひずみ速度の**閉形式** ``dE/dt = A n (t+t0)^(n-1)``。"""
    t = np.asarray(t, float)
    return A_COEF * NEXP * (t + TOFF) ** (NEXP - 1.0)


# --- 合成 -------------------------------------------------------------------- #
_CENTER = (N - 1) / 2.0


def _frame(lam: float):
    """伸び ``lam`` を掛けた像と、画素ごとの真の変位 ``(2, N, N)``。

    ``piv_synth_pair`` は**粒子を動かしてから 2 枚目を描く**。同じ ``seed``
    なら 1 枚目は毎回同一なので、返る 2 枚目を並べると 1 本の履歴になる。
    """
    def disp(rows, cols):
        return np.zeros_like(cols), (cols - _CENTER) * (lam - 1.0)

    a, b, truth = pivops.piv_synth_pair((N, N), disp, density=DENSITY,
                                        diameter_px=DIAM, seed=SEED)
    return np.asarray(a), np.asarray(b), np.asarray(truth)


def make_history():
    """``(frames (T, N, N), truth_flow_last)``。雑音は**まだ足さない**。"""
    frames, first, last_truth = [], None, None
    for k in range(T):
        lam = float(np.exp(true_strain(TIMES[k])))
        a, b, truth = _frame(lam)
        if first is None:
            first = a
        frames.append(b if k > 0 else a)
        last_truth = truth
    return np.stack(frames, axis=0), np.asarray(first), last_truth


def add_noise(frames, sigma: float, seed: int):
    """コマごとに**独立な**雑音。実現を変えて偏りと散らばりを分けるために要る。"""
    if sigma <= 0:
        return frames
    rng = np.random.default_rng(seed)
    return frames + rng.normal(0.0, sigma, frames.shape)


# --- 測る -------------------------------------------------------------------- #
def stretch_between(img_a, img_b, window: int = WINDOW, multipass=None):
    """2 枚から**真ひずみの差**を出す。``ln(1 + du/dx)``。

    一様な伸びなので、変位場 ``u(x) = (x - xc)(lam - 1)`` の**傾き**が
    ``lam - 1``。傾きは `fs.ledger.poly_fit`(1 次)で出す —— 条件数と残差も
    一緒に返るので、当てはめの健康状態が同じ場所に残る。

    ★`poly_fit` は ``x`` が**厳密に単調増加**でないと例外を出す(補間ノード
    向けの契約)。散布した格子をそのまま渡せないので、**列ごとに行方向の
    平均**を取ってから渡す(9 節の穴 (f))。一様な伸びなら行方向は定数なので
    情報は落ちない。
    """
    if multipass:
        flow, info = pivops.piv_multipass(img_a, img_b, windows=multipass,
                                          overlap=OVERLAP)
    else:
        flow, info = pivops.piv_cross_correlate(img_a, img_b, window=window,
                                                overlap=OVERLAP)
    f = np.asarray(flow)
    x = np.asarray(info["cols"], float)
    y = f[1].mean(axis=0)
    fit = fs.ledger.poly_fit(x, y, degree=1)
    slope = float(fit["coeffs"][0])
    return float(np.log1p(slope)), float(fit["rms_residual"])


def history_direct(frames, **kw):
    """基準コマ(t=0)と毎回比べる。``E(0) = 0``。"""
    out = [0.0]
    for k in range(1, frames.shape[0]):
        out.append(stretch_between(frames[0], frames[k], **kw)[0])
    return np.asarray(out)


def history_cumulative(frames, **kw):
    """★ゼロ点 —— 隣り合うコマの増分を足し上げる。"""
    inc = [0.0]
    for k in range(1, frames.shape[0]):
        inc.append(stretch_between(frames[k - 1], frames[k], **kw)[0])
    return np.cumsum(np.asarray(inc))


# =========================================================================== #
def section1_check():
    print("=" * 78)
    print("1) 合成の検算 —— 25 コマが 1 本の履歴になっているか")
    print("=" * 78)
    frames, first, truth = make_history()
    print("  像 %s、粒子密度 %.3f、粒子径 %.1f px、雑音 σ %.3f"
          % (frames.shape, DENSITY, DIAM, NOISE))
    print("  クリープ則: E(t) = %.5f ((t + %.0f)^%.1f - %.0f^%.1f)"
          % (A_COEF, TOFF, NEXP, TOFF, NEXP))
    print("  E(0) = %.6f / E(%d) = %.6f(= %.0f µε)"
          % (true_strain(0.0), T - 1, true_strain(T - 1), 1e6 * E_MAX))
    print("  端(x = ±%.0f px)の総変位 = %.2f px。窓 %d の 1/4 則の上限は %.1f px。"
          % (_CENTER, _CENTER * (np.exp(E_MAX) - 1.0), WINDOW, 0.25 * WINDOW))
    print()
    # 1 枚目が全コマで同一か(同じ粒子を使い回せているかの検算)
    a2, _, _ = _frame(1.0)
    print("  1 枚目の再現性(同じ seed で 2 回描く): 最大差 %.2e"
          % float(np.abs(first - a2).max()))
    print("  フレーム 0 と生成した a の最大差: %.2e"
          % float(np.abs(frames[0] - first).max()))
    print()
    # 既存 op で流れ場そのものの誤差を出す(偏りと散らばりを分ける)
    flow, info = pivops.piv_cross_correlate(frames[0], frames[T - 1],
                                            window=WINDOW, overlap=OVERLAP)
    tr_grid = fs.ledger.piv_sample_at_windows(truth, info)
    st = fs.ledger.piv_error_stats(flow, tr_grid)
    print("  最終コマの変位場を `piv_error_stats` で採点(既存 op):")
    print("    偏り dx %.4f px / 散らばり dx %.4f px / RMS %.4f px / p95 %.4f px"
          % (st["bias_dx"], st["std_dx"], st["rms"], st["p95_abs"]))
    e_dir, res = stretch_between(frames[0], frames[T - 1])
    print("  そこから読んだ真ひずみ %.6f(真値 %.6f、誤差 %+.0f µε)"
          % (e_dir, E_MAX, 1e6 * (e_dir - E_MAX)))
    print("  当てはめの残差 RMS %.4f px" % res)
    print("  → **雑音なしでもここが床**。以降の数字はこれと比べる。")
    return frames


def section2_zero_point(frames):
    print()
    print("=" * 78)
    print("2) ★ゼロ点 —— 「ひずみ 0」と「増分の足し上げ」")
    print("=" * 78)
    noisy = add_noise(frames, NOISE, 1)
    cum = history_cumulative(noisy)
    dirq = history_direct(noisy)
    tru = true_strain(TIMES)
    z_rms = float(np.sqrt(np.mean(tru ** 2)))
    print("  ゼロ点その 0(「伸びていません」): RMS 誤差 %.0f µε" % (1e6 * z_rms))
    for name, h in (("累積(ゼロ点)", cum), ("直接", dirq)):
        r = float(np.sqrt(np.mean((h - tru) ** 2)))
        print("  %-14s RMS 誤差 %8.0f µε(ゼロ点比 %.0f 倍改善)"
              % (name, 1e6 * r, z_rms / max(r, 1e-12)))
    print()
    print("  %4s %12s %12s %10s %12s %10s"
          % ("t", "真値 µε", "累積 µε", "誤差", "直接 µε", "誤差"))
    print("  " + "-" * 66)
    for k in (1, 4, 8, 12, 16, 20, 24):
        print("  %4d %12.0f %12.0f %10.0f %12.0f %10.0f"
              % (k, 1e6 * tru[k], 1e6 * cum[k], 1e6 * (cum[k] - tru[k]),
                 1e6 * dirq[k], 1e6 * (dirq[k] - tru[k])))
    return noisy, cum, dirq, tru


def section3_crossover(frames):
    print()
    print("=" * 78)
    print("3) ★★累積 vs 直接 —— 偏りと散らばりを分けて、交点を探す")
    print("=" * 78)
    n_real = 10
    print("  雑音の実現を %d 通り作り、**コマごとに**偏り(平均誤差)と" % n_real)
    print("  散らばり(実現間の標準偏差)を分けて数える。1 つの RMS に")
    print("  畳むと、系統的なずれと揺らぎのどちらが効いているか消える。")
    cums, dirs = [], []
    for s in range(n_real):
        noisy = add_noise(frames, NOISE, 100 + s)
        cums.append(history_cumulative(noisy))
        dirs.append(history_direct(noisy))
    cums = np.asarray(cums)
    dirs = np.asarray(dirs)
    tru = true_strain(TIMES)
    out = {}
    for name, h in (("cum", cums), ("dir", dirs)):
        err = h - tru[None, :]
        out[name] = {"bias": err.mean(axis=0), "scatter": err.std(axis=0),
                     "rms": np.sqrt((err ** 2).mean(axis=0))}
    print()
    print("  %4s | %9s %9s %9s | %9s %9s %9s"
          % ("t", "累積偏り", "散らばり", "RMS", "直接偏り", "散らばり", "RMS"))
    print("  " + "-" * 70)
    for k in (1, 2, 4, 6, 8, 12, 16, 20, 24):
        print("  %4d | %9.1f %9.1f %9.1f | %9.1f %9.1f %9.1f"
              % (k, 1e6 * out["cum"]["bias"][k], 1e6 * out["cum"]["scatter"][k],
                 1e6 * out["cum"]["rms"][k], 1e6 * out["dir"]["bias"][k],
                 1e6 * out["dir"]["scatter"][k], 1e6 * out["dir"]["rms"][k]))
    print("  (単位はすべて µε = 1e-6)")
    print()
    # 散らばりが sqrt(T) で伸びるか —— 累積の教科書的な予想
    sc = out["cum"]["scatter"]
    kk = np.arange(2, T)
    p = np.polyfit(np.log(kk.astype(float)), np.log(sc[2:]), 1)[0]
    print("  累積の散らばりの伸び方: log-log の傾き %.2f(ランダムウォークなら"
          " 0.50)。" % p)
    print("  t=4 で %.1f µε → t=24 で %.1f µε(比 %.2f、sqrt(6) = 2.45)。"
          % (1e6 * sc[4], 1e6 * sc[24], sc[24] / max(sc[4], 1e-15)))
    print("  ★実現 %d 通りでは散らばりの推定自体が ±%.0f %% 揺れるので、"
          % (n_real, 100 / np.sqrt(2 * (n_real - 1))))
    print("  この傾きは**桁の話としてしか**読めない。断定はしない。")
    print("  はっきりしているのは、**散らばり(%.0f µε)より偏り(%.0f µε)の"
          % (1e6 * sc[24], abs(1e6 * out["cum"]["bias"][24])))
    print("  ほうが大きい**こと —— 累積の問題は揺らぎではない(4 節で確かめる)。")
    # 交点
    cross = None
    for k in range(1, T):
        if out["cum"]["rms"][k] > out["dir"]["rms"][k]:
            cross = k
            break
    if cross is None:
        print("  → **時間軸には交点が無かった**。この雑音では最後まで %s が小さい。"
              % ("累積" if out["cum"]["rms"][-1] < out["dir"]["rms"][-1] else "直接"))
    else:
        print("  → 交点は t = %d(真ひずみ %.0f µε)。ここから先は直接のほうが悪い。"
              % (cross, 1e6 * tru[cross]))
    print()
    print("  ★交点は**時間軸ではなく雑音の軸に**あるかもしれない。累積の弱点は")
    print("     揺らぎ(σ√T)なので、雑音を上げれば累積が先に負けるはず —— 実測:")
    print()
    print("  %8s | %12s %12s | %12s %12s | %s"
          % ("雑音 σ", "累積 偏り", "累積 RMS", "直接 偏り", "直接 RMS", "勝ち"))
    print("  " + "-" * 76)
    sweep = {"sigma": [], "cum": [], "dir": []}
    for sg in (0.02, 0.05, 0.10, 0.20, 0.40):
        cs, ds = [], []
        for s in range(3):
            noisy = add_noise(frames, sg, 500 + 17 * s)
            cs.append(history_cumulative(noisy)[-1])
            ds.append(history_direct(noisy)[-1])
        cs, ds = np.asarray(cs) - tru[-1], np.asarray(ds) - tru[-1]
        rc = float(np.sqrt((cs ** 2).mean()))
        rd = float(np.sqrt((ds ** 2).mean()))
        sweep["sigma"].append(sg)
        sweep["cum"].append(1e6 * rc)
        sweep["dir"].append(1e6 * rd)
        print("  %8.2f | %12.0f %12.0f | %12.0f %12.0f | %s"
              % (sg, 1e6 * cs.mean(), 1e6 * rc, 1e6 * ds.mean(), 1e6 * rd,
                 "累積" if rc < rd else "★直接"))
    return out, cums, dirs, tru, sweep


def section4_origin(frames):
    print()
    print("=" * 78)
    print("4) ★対照群 —— 累積の誤差は「揺らぎ」か「1 歩ごとの偏り」か")
    print("=" * 78)
    print("  対照 1: **雑音を切る**。揺らぎ由来なら誤差は消えるはず。")
    print("  対照 2: **コマを間引く**(歩数を 1/2、1/4 に)。1 歩ごとの偏りが")
    print("          原因なら、歩数に比例して誤差が減るはず。")
    print()
    tru_end = true_strain(TIMES[-1])
    print("  %-22s %12s %12s" % ("条件", "終端 E µε", "誤差 µε"))
    print("  " + "-" * 50)
    clean = history_cumulative(frames)
    print("  %-22s %12.0f %12.0f"
          % ("雑音なし・全 25 コマ", 1e6 * clean[-1], 1e6 * (clean[-1] - tru_end)))
    noisy = add_noise(frames, NOISE, 7)
    nz = history_cumulative(noisy)
    print("  %-22s %12.0f %12.0f"
          % ("雑音 σ=0.02・全 25 コマ", 1e6 * nz[-1], 1e6 * (nz[-1] - tru_end)))
    rec = {"steps": [], "err_clean": [], "err_noisy": []}
    for stride in (1, 2, 4, 6):
        idx = np.arange(0, T, stride)
        if idx[-1] != T - 1:
            idx = np.append(idx, T - 1)
        c = history_cumulative(frames[idx])[-1]
        m = history_cumulative(add_noise(frames[idx], NOISE, 7))[-1]
        rec["steps"].append(len(idx) - 1)
        rec["err_clean"].append(1e6 * (c - tru_end))
        rec["err_noisy"].append(1e6 * (m - tru_end))
        print("  %-22s %12.0f %12.0f"
              % ("間引き %d(%d 歩)" % (stride, len(idx) - 1), 1e6 * m,
                 1e6 * (m - tru_end)))
    print()
    print("  歩数 vs 誤差 [µε]:")
    print("  %8s %14s %14s" % ("歩数", "雑音なし", "雑音あり"))
    for k, s in enumerate(rec["steps"]):
        print("  %8d %14.0f %14.0f" % (s, rec["err_clean"][k], rec["err_noisy"][k]))
    return rec


def section5_direct_breaks(frames):
    print()
    print("=" * 78)
    print("5) ★直接測定は何で壊れるか —— 窓の中の変形 と 1/4 則")
    print("=" * 78)
    print("  基準コマとの差が開くと、(i) 窓の中で変位が変わり相関ピークが潰れる")
    print("  (ii) 総変位が窓 x 0.25 を超えると探索範囲から出る。**どちらか**を")
    print("  分けるため、窓を変えた 3 通りと多段(`piv_multipass`)を比べる。")
    print()
    noisy = add_noise(frames, NOISE, 21)
    tru = true_strain(TIMES)
    variants = [("窓 32", {"window": 32}), ("窓 64", {"window": 64}),
                ("多段 64→32", {"multipass": (64, 32)})]
    res = {}
    for name, kw in variants:
        res[name] = history_direct(noisy, **kw)
    print("  %4s %10s |" % ("t", "真値 µε"), end="")
    for name, _ in variants:
        print(" %14s" % (name + " 誤差"), end="")
    print()
    print("  " + "-" * (18 + 15 * len(variants)))
    for k in (4, 8, 12, 16, 20, 24):
        print("  %4d %10.0f |" % (k, 1e6 * tru[k]), end="")
        for name, _ in variants:
            print(" %14.0f" % (1e6 * (res[name][k] - tru[k])), end="")
        print()
    print()
    lim = 0.25 * 32
    over = _CENTER * (np.exp(tru) - 1.0)
    k_over = int(np.argmax(over > lim)) if (over > lim).any() else -1
    print("  端の総変位が窓 32 の 1/4 則(%.1f px)を超えるのは t = %s。"
          % (lim, k_over if k_over > 0 else "最後まで超えない(%.2f px)" % over[-1]))
    print("  窓 64 なら上限は %.1f px なので、この履歴では超えない。" % (0.25 * 64))
    return res, tru


def section6_rate(frames, cums, dirs, tru):
    print()
    print("=" * 78)
    print("6) ★★ひずみ速度 —— 時間平滑化はどれだけ「なまらせる」か")
    print("=" * 78)
    print("  真値は閉形式 dE/dt = A n (t+t0)^(n-1)(t=0 で %.0f µε/コマ、"
          % (1e6 * true_rate(0.0)))
    print("  t=24 で %.0f µε/コマ)。履歴を移動平均してから中央差分で微分する。"
          % (1e6 * true_rate(T - 1)))
    print("  **中央移動平均**(`fs.moving_average`)と**因果移動平均**")
    print("  (`fs.ledger.moving_average_window`、先を見ない = 実時間で使える)")
    print("  を両方かける。分けて数えるのは **なまり(偏り)** と **揺らぎ**。")
    print()
    hist = dirs.mean(axis=0) * 0.0 + dirs  # (n_real, T)
    rate_true = true_rate(TIMES)
    rows = []
    for w in (1, 3, 5, 7, 9, 11):
        for kind in ("中央", "因果"):
            rates = []
            for h in hist:
                sm = _smooth(h, w, kind)
                rates.append(np.gradient(sm, TIMES))
            rates = np.asarray(rates)
            err = rates - rate_true[None, :]
            # 端は差分と平滑化の両方が効くので、中身だけで採点する
            sl = slice(w, T - w)
            bias = float(err[:, sl].mean())
            scat = float(err[:, sl].std(axis=0).mean())
            # なまりが最も効くのは曲率が大きい序盤
            early = float(err[:, w:w + 3].mean())
            rows.append((w, kind, 1e6 * bias, 1e6 * scat, 1e6 * early))
    print("  %5s %6s %14s %14s %16s"
          % ("窓 w", "種類", "偏り µε/コマ", "揺らぎ µε/コマ", "序盤の偏り µε/コマ"))
    print("  " + "-" * 62)
    for w, kind, b, s, e in rows:
        print("  %5d %6s %14.1f %14.1f %16.1f" % (w, kind, b, s, e))
    print()
    print("  真の速度そのもの: 序盤 %.0f / 終盤 %.0f µε/コマ"
          % (1e6 * rate_true[3], 1e6 * rate_true[-4]))
    return rows, rate_true


def _smooth(y, w: int, kind: str):
    """1-D の系列を平滑化する。**fullseye の動画 op を (T,1,1) で借りる**。

    ★1 次元の系列を平滑化する op が無いので、``(T, 1, 1)`` の「動画」に
    仕立てて `moving_average` / `moving_average_window` に渡している
    (8 節の穴 (c))。形は通るが、意味の上では 1 画素の動画である。
    """
    if w <= 1:
        return np.asarray(y, float)
    v = np.asarray(y, float).reshape(-1, 1, 1)
    if kind == "中央":
        return np.asarray(fs.moving_average(v, w)).reshape(-1)
    return np.asarray(fs.ledger.moving_average_window(v, window=w)).reshape(-1)


def section7_figures(frames, out, cums, dirs, tru, rate_rows, rate_true,
                     direct_res, sweep):
    if not figs.enabled():
        return
    noisy = add_noise(frames, NOISE, 1)
    figs.save_grid("speckle",
                   [noisy[0], noisy[T - 1], noisy[T - 1] - noisy[0]],
                   ["t=0", "t=24", "差(t=24 - t=0)"],
                   title="スペックルの履歴(真ひずみ 0 → 6 %)", ncols=3,
                   signed=[False, False, True],
                   caption="粒子を動かしてから描き直しているので真値が厳密。"
                           "差の像が中心から外へ向かって強くなるのが一様な伸び。")
    figs.save_plot("history",
                   [("真値", TIMES, 1e6 * tru),
                    ("累積(ゼロ点)", TIMES, 1e6 * cums.mean(axis=0)),
                    ("直接", TIMES, 1e6 * dirs.mean(axis=0))],
                   xlabel="t [コマ]", ylabel="真ひずみ [µε]",
                   title="クリープのひずみ履歴 E(t) = A((t+2)^0.4 - 2^0.4)",
                   caption="実現 6 通りの平均。目では区別が付かないので、"
                           "次の図で誤差だけを描く。")
    figs.save_plot("errors",
                   [("累積 偏り", TIMES, 1e6 * out["cum"]["bias"]),
                    ("累積 散らばり", TIMES, 1e6 * out["cum"]["scatter"]),
                    ("直接 偏り", TIMES, 1e6 * out["dir"]["bias"]),
                    ("直接 散らばり", TIMES, 1e6 * out["dir"]["scatter"]),
                    ("0", TIMES, np.zeros(T))],
                   xlabel="t [コマ]", ylabel="誤差 [µε]",
                   title="偏りと散らばりを分けて描く",
                   caption="1 つの RMS に畳むと、系統的なずれと揺らぎの"
                           "どちらが効いているかが消える。")
    rows_tbl = [["%d" % w, kind, "%.1f" % b, "%.1f" % s, "%.1f" % e]
                for w, kind, b, s, e in rate_rows]
    figs.save_table("rate_table",
                    ["窓 w", "種類", "偏り µε/コマ", "揺らぎ µε/コマ", "序盤の偏り"],
                    rows_tbl, title="時間平滑化とひずみ速度",
                    caption="窓を広げると揺らぎは減るが、なまり(偏り)が増える。"
                            "因果フィルタは遅れぶんだけ偏りが大きい。")


def section8_findings(out, rec, direct_res, tru, rate_rows):
    print()
    print("=" * 78)
    print("8) 所見")
    print("=" * 78)
    c24 = 1e6 * out["cum"]["rms"][24]
    d24 = 1e6 * out["dir"]["rms"][24]
    print("""
  (1) ★ゼロ点(累積)は「伸びていません」に対して桁で勝つ。ここは当然。
      問題は累積 vs 直接で、終端(6 %% ひずみ)の RMS は
      累積 %.0f µε / 直接 %.0f µε。

  (2) ★累積の**散らばり**は歩数の平方根で伸びる(ランダムウォーク)。
      一方**偏り**は歩数に比例して積もる —— こちらは雑音を切っても
      残るので、揺らぎではなく PIV の 1 歩ごとの系統誤差。
      4 節の対照群(雑音なし・歩数を間引く)でそれを確かめてある。

  (3) ★直接測定は変形が大きくなるほど悪くなるが、**この履歴(端の総変位
      %.1f px、窓 32 の 1/4 則は 8.0 px)では致命傷にならなかった**。
      窓 64 と多段 64→32 の比較で、効いているのが探索範囲なのか
      窓の中の変形なのかを分けてある(5 節)。

  (4) ★★時間平滑化は**なまり(偏り)と揺らぎのトレードオフ**。窓を
      広げると揺らぎは下がるが、曲率のある序盤で速度を系統的に読み違える。
      **因果(先を見ない)フィルタは遅れぶんだけ偏りが大きい** ——
      同じ窓幅でも中央フィルタと差が出る。実時間で速度を出すなら、
      この遅れを見込んで窓を決めること。

  (5) ★真ひずみ(対数ひずみ)を使うと、増分の和が全体とちょうど一致する。
      **工学ひずみで同じことをやると、累積と直接が別の量を推定してしまい、
      比べているのが手法なのか定義なのか分からなくなる。**
""" % (c24, d24, _CENTER * (np.exp(tru[-1]) - 1.0)))


def section9_tool_gaps():
    print("=" * 78)
    print("9) 道具の穴")
    print("=" * 78)
    print("""
  (a) ★★**型つき台帳は複数返り値の op を「1 つ目だけ」に切り詰める**。
      `fs.ledger.piv_synth_pair(...)` は ``(a, b, truth)`` のうち
      **a しか返さない**(画像対を作る op なのに 1 枚しか出てこない)。
      `fs.ledger.piv_cross_correlate(...)` も ``(flow, info)`` の
      ``info`` を落とすので、**窓中心の座標が取れず**、この PoC の
      「変位の傾きを当てはめる」という基本操作ができない。
      台帳の契約(op = 1 つの型を返す)から見れば設計どおりだが、
      **facade に出ていない op ではそれが唯一の入口になる**。
      実測: docstring がタプル返しを明記している台帳 op は 79 個、
      そのうち **14 個は facade に無い**(piv 族 6 個、profile 族 4 個、
      dem 族 2 個、jitter、optscene_instances)。この 14 個は
      公開 API からは**第 1 要素しか取り出せない**。
      この PoC は `poc_dic_strain.py` と同じく ``import pivops`` で
      逃げた —— つまり**例が 2 本続けて内部モジュールに触っている**。

  (b) **ひずみ「履歴」を扱う層が無い**。`strain_from_displacement` は
      1 対のフレームから場を出すところで止まる。時系列側
      (増分の足し上げ、対数ひずみと工学ひずみの往復、速度の推定、
      クリープ則 ``A t^n`` / Norton 則の当てはめ)が空いている。

  (c) **1 次元の系列を平滑化する op が無い**。移動平均は
      `fullseye.moving_average`(中央)と
      `fs.ledger.moving_average_window`(因果)があるが、どちらも
      ``(T, H, W)`` の動画用。この PoC は ``(T, 1, 1)`` に整形して
      借りている。**形は通るが意味は 1 画素の動画**で、
      `poc_particle_tracking.py` の穴 (h) と同じ「形が同じで意味が違う」。
      Savitzky-Golay(多項式平滑微分)も無い —— 速度を出すなら
      移動平均 + 差分より素直で、なまりも小さい。

  (d) **`piv_error_stats` は 1 対のフレーム用**。時系列に対して
      「コマごとの偏りと散らばり」を返す版が無いので、この PoC は
      実現を 6 通り回して自前で集計した。`piv_time_statistics` は
      あるが、あちらは**乱流の変動統計**(平均・RMS・レイノルズ応力)で、
      推定誤差の統計ではない。名前が近いので取り違えやすい。

  (e) `poly_fit` は当てはめと一緒に条件数と残差を返す —— **これは良い**。
      当てはめの健康状態を別 API にしていないので、呼び手が見落とせない。
      同じ設計が時系列側にも欲しい(上の (b))。

  (f) ★**`poly_fit` は ``x`` が厳密に単調増加でないと例外**を出す
      (「補間ノード」の契約)。ところが多項式当てはめのいちばん普通の
      用途は**散布データの最小二乗**で、そちらは x が重複する。
      この PoC は PIV の格子(同じ列が 15 行ぶん並ぶ)をそのまま渡せず、
      列ごとに平均してから渡した。fail-closed の判断としては正しいが、
      **散布データ用の入口が別に要る**(`poly_fit_scatter` なり
      ``allow_duplicates=True`` なり)。今は「最小二乗の道具が
      最小二乗に使えない」状態になっている。
""")
    assert not hasattr(fs, "piv_synth_pair"), \
        "★piv_synth_pair が facade に出た → (a) は直った。この assert を消すこと"
    assert not hasattr(fs, "piv_cross_correlate"), \
        "★piv_cross_correlate が facade に出た → (a) は直った"
    assert np.asarray(fs.ledger.piv_synth_pair(
        (32, 32), (0.5, 0.0), density=0.02, seed=1)).ndim == 2, \
        "★台帳が対を返すようになった → (a) は直った"
    assert not hasattr(fs.ledger, "strain_history"), "★(b) が直った"
    assert not hasattr(fs.ledger, "savitzky_golay"), "★(c) が直った"
    print("  (assert 5 本で現状を固定した。穴が埋まったらこの PoC が落ちる。)")


def main():
    t0 = time.perf_counter()
    print("poc_strain_history — クリープ試験のひずみ履歴(その 3: 時間発展の DIC)")
    print("既存の piv 族 23 op と strain_from_displacement を使う。新しい op は作らない。")
    print()
    frames = section1_check()
    section2_zero_point(frames)
    out, cums, dirs, tru, sweep = section3_crossover(frames)
    rec = section4_origin(frames)
    direct_res, _ = section5_direct_breaks(frames)
    rate_rows, rate_true = section6_rate(frames, cums, dirs, tru)
    section7_figures(frames, out, cums, dirs, tru, rate_rows, rate_true,
                     direct_res, sweep)
    section8_findings(out, rec, direct_res, tru, rate_rows)
    section9_tool_gaps()
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
