# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""transforms_tour — フーリエ以外の積分変換を「答えの決まる入力」で一巡する(Abel / Hankel / Laplace)。

    py -3.11 examples/transforms_tour.py

【この例が示すこと】
fullseye には FFT・DCT・Radon は揃っていたが、**Laplace 変換の系統が 1 本も無く**、Abel・Hankel も無かった
(2026-10-03 の棚卸し)。ここで足した 10 本を、学生が「何が起きているか」を目で追える順に並べる:
具体的な物 → 変換 → 戻す → 閉じた式(破線)と重ねる → 失敗する条件も隣に置く。

1. **Abel 変換** —— 炎のように軸対称な物は、横から撮ると奥行き方向に足し合わさった投影しか見えない。
   逆 Abel で断面の分布に戻す。2 つの独立な戻し方(微分の求積 / 殻を剥く)がある。雑音を足して
   標本数を振ると、**どちらが良いかは標本数で逆転する**(微分の誤差は 1/dr、殻剥きは 1/√dr で増える)。
2. **Hankel 変換** —— 円い開口の回折像(Airy)。軸対称な関数の 2 次元フーリエ変換は Hankel 変換 1 本に落ちる。
   閉じた式 a·J₁(2πaν)/ν と重ね、最初の暗い輪 ν = 0.61/a に印を付ける。
3. **s 領域** —— 2 次系 ω²/(s² + 2ζωs + ω²) の減衰比 ζ を 4 通りに振る。極が虚軸に近いほど揺れが長く残る。
4. **逆ラプラス(Talbot)** —— 1/√s(分岐点があり部分分数では解けない)を数値で戻す。節点数 M を増やすと
   誤差は指数的に減るが、増やしすぎると丸めで再び悪化する(倍精度の限界)。

【グラウンドトゥルース】すべて閉じた式。Abel: ガウスの対 / Hankel: 円板 ↔ J₁ / s 領域: 2 次系のステップ応答 /
Talbot: 1/√s ↔ 1/√(πt) と行列指数(別経路)。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import special

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs      # noqa: E402
import fullseye as fs          # noqa: E402  公開経路(fs.<名前>)から呼ぶ


def _flame(n=160, nz=96, R=4.0):
    """高さ z ごとに幅の変わる軸対称の「炎」f(r, z)(真値)。"""
    dr = R / n
    r = np.arange(n) * dr
    z = np.linspace(0.0, 1.0, nz)
    width = 0.6 + 1.2 * z                                   # 上ほど広がる
    core = np.exp(-r[None, :] ** 2 / width[:, None] ** 2)
    shell = 0.6 * np.exp(-((r[None, :] - 1.4 * width[:, None]) / 0.25) ** 2)   # 外側の明るい殻(炎の反応帯)
    amp = np.sin(np.pi * np.clip(z, 0.02, 0.98))[:, None]
    return dr, r, amp * (0.5 * core + shell)


def _mirror(rows):
    """動径の行 f(r) を左右に鏡映して、断面・投影を人の見る形(−R..R)にする。"""
    return np.concatenate([rows[:, :0:-1], rows], axis=1)


def run() -> dict:
    t0 = time.perf_counter()
    out = {}

    # ---- 1. Abel --------------------------------------------------------------- #
    dr, r, F = _flame()
    A = np.stack([fs.abel_transform(row, dr) for row in F])
    Fd = np.stack([fs.abel_inverse(row, dr) for row in A])
    Fo = np.stack([fs.abel_inverse(row, dr, method="onion") for row in A])
    ed, eo = float(np.abs(Fd - F).max()), float(np.abs(Fo - F).max())
    print("1) Abel: 投影から断面へ。最大誤差 微分 %.2e / 殻剥き %.2e(真値の最大 %.2f)" % (ed, eo, F.max()))
    assert ed < 2e-3 and eo < 3e-2
    # 雑音 1% で標本数を振る: 微分の誤差 ∝ n(= 1/dr)、殻剥き ∝ √n。どちらが良いかは n で逆転する。
    ns = (60, 120, 240, 480, 960)
    prof = lambda rr: 0.5 * np.exp(-rr ** 2 / 1.44) + 0.6 * np.exp(-((rr - 1.7) / 0.25) ** 2)   # noqa: E731
    noise_d, noise_o = [], []
    for n in ns:
        rr = np.arange(n) * (4.0 / n)
        fr, Ar = prof(rr), fs.abel_transform(prof(rr), 4.0 / n)
        ed_, eo_ = [], []
        for k in range(6):
            An = Ar + np.random.default_rng(k).normal(0.0, 0.01 * Ar.max(), n)
            ed_.append(np.abs(fs.abel_inverse(An, 4.0 / n) - fr).mean())
            eo_.append(np.abs(fs.abel_inverse(An, 4.0 / n, method="onion") - fr).mean())
        noise_d.append(float(np.mean(ed_)))
        noise_o.append(float(np.mean(eo_)))
    slope_d = float(np.polyfit(np.log(ns), np.log(noise_d), 1)[0])
    slope_o = float(np.polyfit(np.log(ns), np.log(noise_o), 1)[0])
    nd, no = noise_d[-1], noise_o[-1]
    print("   雑音 1%%: 標本数 %d→%d で 微分 %.3f→%.3f(傾き %.2f)/ 殻剥き %.3f→%.3f(傾き %.2f)—— n=%d では%s"
          % (ns[0], ns[-1], noise_d[0], nd, slope_d, noise_o[0], no, slope_o, ns[0],
             "微分" if noise_d[0] < noise_o[0] else "殻剥き") + "が良い")
    assert 0.8 < slope_d < 1.2 and 0.3 < slope_o < 0.7 and noise_d[0] < noise_o[0] and no < nd
    # 単独の閉じた式でも確かめる: ガウス ↔ √π σ ガウス
    sig = 1.1
    g = np.exp(-r ** 2 / sig ** 2)
    gerr = float(np.abs(fs.abel_transform(g, dr) - math.sqrt(math.pi) * sig * g).max())
    assert gerr < 1e-5
    out.update(abel_err_derivative=ed, abel_err_onion=eo, abel_noise_derivative=nd, abel_noise_onion=no)

    # ---- 2. Hankel: 円い開口 → Airy ------------------------------------------------ #
    a = 1.0
    h = fs.hankel_transform(None, lambda rr: (rr <= a).astype(float), r_max=12.0, n=1200)
    nu = h["nu"]
    airy = a * special.j1(2 * math.pi * a * nu) / np.where(nu > 0, nu, 1.0)
    sel = nu < 2.5
    herr = float(np.abs(h["F"] - airy)[sel].max())
    first_zero = special.jn_zeros(1, 1)[0] / (2 * math.pi * a)
    print("2) Hankel: 円板 → a·J₁(2πaν)/ν。誤差 %.2e(ν<2.5)。最初の暗い輪 ν = %.4f(= 0.61/a)" % (herr, first_zero))
    assert herr < 0.02 * math.pi * a * a                          # 円板の縁の不連続ぶん(標本化の誤差)
    selfdual = fs.hankel_transform(None, lambda rr: np.exp(-math.pi * rr ** 2), r_max=6.0, n=256)
    assert np.abs(selfdual["F"] - np.exp(-math.pi * selfdual["nu"] ** 2)).max() < 1e-12
    out.update(hankel_airy_err=herr, airy_first_zero=float(first_zero))

    # ---- 3. s 領域: 2 次系の減衰比 ---------------------------------------------------- #
    w0 = 2.0 * math.pi
    t = np.linspace(0.0, 3.0, 301)
    zetas = (0.1, 0.3, 0.7, 1.0)
    steps, poles = [], []
    for z in zetas:
        num, den = [w0 * w0], [1.0, 2 * z * w0, w0 * w0]
        steps.append(fs.tf_step_response(num, den, t))
        poles.append(fs.tf_poles_zeros(num, den)["poles"])
    wd = w0 * math.sqrt(1 - 0.3 ** 2)
    closed = 1 - np.exp(-0.3 * w0 * t) * (np.cos(wd * t) + 0.3 / math.sqrt(1 - 0.09) * np.sin(wd * t))
    serr = float(np.abs(steps[1] - closed).max())
    over = [float(s.max() - 1.0) for s in steps]
    print("3) 2 次系: ζ = %s の行き過ぎ %s。ζ=0.3 の閉じた式との差 %.1e"
          % (zetas, ", ".join("%.3f" % o for o in over), serr))
    assert serr < 1e-12 and over[0] > over[1] > over[2] > -1e-9 and over[3] < 1e-9
    w = np.logspace(-1, 2, 200) * w0 / 10
    bode = [fs.tf_freq_response([w0 * w0], [1.0, 2 * z * w0, w0 * w0], w) for z in zetas]
    peak = [float(b["mag_db"].max()) for b in bode]
    assert peak[0] > peak[1] > peak[2]                            # 共振の山は ζ が小さいほど高い
    out.update(step_err=serr, overshoot=over)

    # ---- 4. 逆ラプラス(Talbot)と M ---------------------------------------------------- #
    tt = np.linspace(0.05, 4.0, 40)
    truth = 1.0 / np.sqrt(math.pi * tt)
    Ms = list(range(4, 72, 4))
    errs = [float(np.abs(fs.laplace_inverse_func(lambda s: 1 / np.sqrt(s), tt, M=m) - truth).max()) for m in Ms]
    best = Ms[int(np.argmin(errs))]
    print("4) Talbot: 1/√s → 1/√(πt)。M=%d で最小誤差 %.1e、M=%d では %.1e(丸めで悪化)"
          % (best, min(errs), Ms[-1], errs[-1]))
    assert min(errs) < 1e-9 and errs[-1] > 10 * min(errs) and errs[0] > 1e-4
    two_paths = float(np.abs(fs.laplace_inverse_talbot([1, 3], [1, 2, 5], tt)
                             - fs.tf_impulse_response([1, 3], [1, 2, 5], tt)).max())
    assert two_paths < 1e-8
    out.update(talbot_best_M=best, talbot_best_err=min(errs), talbot_two_paths=two_paths)

    # ---- 図(学習系サイトの型: 真値は破線、失敗例を隣に、同じ量は同じ色) ---------------------- #
    if figs.enabled():
        figs.save_grid("abel_flame",
                       [_mirror(F), _mirror(A / A.max()), _mirror(Fo), _mirror(np.abs(Fo - F))],
                       ["断面(真値)", "横から見た像(投影)", "逆 Abel で戻した断面", "真値との差(同じ色の目盛り)"],
                       ncols=4, title="Abel 変換 —— 横から撮った像から、炎の断面を取り戻す",
                       vrange=[(0.0, float(F.max())), (0.0, 1.0), (0.0, float(F.max())), (0.0, float(F.max()))],
                       caption="縦が高さ、横が中心からの距離(左右対称)。(b) しか撮れなくても、軸対称なら (c) に戻せる。"
                               "(d) は (a) と同じ色の目盛りで描いた差で、ほぼ黒 = 戻せている(殻剥き法、最大誤差 %.3f、"
                               "真値の最大 %.2f)。" % (eo, F.max()))
        figs.save_plot("abel_noise_scaling",
                       [("微分で戻す(傾き %.2f)" % slope_d, np.log10(ns), np.log10(noise_d)),
                        ("殻を剥いて戻す(傾き %.2f)" % slope_o, np.log10(ns), np.log10(noise_o)),
                        ("傾き 1 の参照", np.log10(ns), np.log10(noise_d[0]) + np.log10(np.asarray(ns) / ns[0])),
                        ("傾き 1/2 の参照", np.log10(ns), np.log10(noise_o[0]) + 0.5 * np.log10(np.asarray(ns) / ns[0]))],
                       styles=[None, None, "dashed", "dashed"],
                       xlabel="log10(標本数 n)", ylabel="log10(平均誤差)",
                       title="雑音 1% の投影を戻す —— どちらが良いかは標本数で逆転する",
                       caption="雑音が無ければ 2 つとも真値に重なる(誤差 %.0e と %.0e)。雑音があると、微分する方法の誤差は"
                               "標本間隔に反比例して増え(傾き 1)、殻剥きは平方根でしか増えない(傾き 1/2)。"
                               "粗い格子では微分、細かい格子では殻剥き。" % (ed, eo))
        figs.save_plot("hankel_airy",
                       [("hankel_transform", nu[sel], h["F"][sel]),
                        ("閉じた式 a·J₁(2πaν)/ν", nu[sel], airy[sel]),
                        ("最初の暗い輪 0.61/a", [first_zero, first_zero], [airy[sel].min(), airy[sel].max()])],
                       styles=[None, "dashed", "dotted"],
                       xlabel="空間周波数 ν", ylabel="振幅",
                       title="円い穴の回折像(Airy)—— 2 次元のフーリエ変換が 1 本の積分になる",
                       caption="軸対称なものの 2-D フーリエ変換は Hankel 変換に等しい。円板は J₁ の形になり、"
                               "最初に 0 を切る位置 0.61/a が望遠鏡やカメラの分解能(1.22λ/D)の正体。")
        figs.save_plot("second_order_steps",
                       [("ζ = %.1f(極 %s)" % (z, ", ".join("%.1f%+.1fj" % (p.real, p.imag) for p in pl[:1])), t, s)
                        for z, s, pl in zip(zetas, steps, poles)] + [("目標値 1", [0, 3], [1, 1])],
                       styles=[None] * len(zetas) + ["dashed"],
                       xlabel="時間 t [s]", ylabel="出力 y(t)",
                       title="2 次系のステップ応答 —— 減衰比 ζ を 4 通り",
                       caption="極が虚軸に近い(実部が小さい)ほど揺れが長く残る。ζ=0.3 は閉じた式と %.0e で一致。" % serr)
        figs.save_plot("bode",
                       [("ζ = %.1f" % z, np.log10(b["w"] / w0), b["mag_db"]) for z, b in zip(zetas, bode)],
                       xlabel="log10(ω / ω₀)", ylabel="ゲイン [dB]",
                       title="Bode 線図(大きさ)—— 共振の山は ζ が小さいほど高い",
                       caption="横軸は固有周波数で割った周波数の対数。ω₀ を越えると −40 dB/decade で下がる(2 次系)。")
        figs.save_plot("talbot_M",
                       [("最大誤差の log10", Ms, np.log10(errs))],
                       xlabel="節点の数 M", ylabel="log10(最大誤差)",
                       title="数値逆ラプラス(Talbot)—— 増やせば良い、わけではない",
                       caption="M を増やすと誤差は指数的に減る(直線的に下がる部分)。M=%d を越えると、"
                               "大きな数の打ち消し合いで丸め誤差が勝ち、再び悪化する。" % best)
        figs.save_table("numbers", ["主張", "実測", "真値 / 期待"],
                        [["Abel 逆(殻剥き)の最大誤差", "%.2e" % eo, "< 3e-2"],
                         ["Abel 逆(微分)の最大誤差", "%.2e" % ed, "< 2e-3"],
                         ["雑音の誤差の傾き(微分 / 殻剥き)", "%.2f / %.2f" % (slope_d, slope_o), "1 / 0.5"],
                         ["Airy の最初の暗い輪", "%.4f" % first_zero, "0.6098 / a"],
                         ["2 次系(ζ=0.3)と閉じた式の差", "%.1e" % serr, "< 1e-12"],
                         ["Talbot の最良誤差(M=%d)" % best, "%.1e" % min(errs), "< 1e-9"],
                         ["Talbot と行列指数の差", "%.1e" % two_paths, "< 1e-8"]],
                        title="transforms_tour の数")
    assert not figs.errors(), figs.errors()

    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  transforms_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()
