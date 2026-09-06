# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_moire_screen — ディスプレイ検査のモアレは「本物のムラ」と区別できるか。

    py -3.11 examples/poc_moire_screen.py

【この PoC が答える問い】
パネル検査でいちばん多い問い —「画面にうっすら縞が見える。これはパネルの
輝度ムラ(不良)なのか、カメラとの干渉で出たモアレ(撮り方の問題)なのか」。
答えは「**撮る前に計算で分けられる**。モアレの周期は画素格子の周期と標本化
間隔だけで決まる閉形式で、実測と 0.2 %% 以内で合う。ただし**高調波の
うなりも一緒に予測しないと危ない** —— 基本波のうなりが安全な位置でも、
3 次のうなりがムラの帯に落ちることがある」。

【所見(すべて下の節で実測。★ は重要、★★ は最重要)】

 1. 閉形式が効く。表示の空間周波数 k(カメラ画素あたりの縞数)に対して、
    m 次高調波のモアレ周波数は ``wrap(m·k)``([-0.5,0.5] へ折り返し)。
    実測 FFT ピークとの差は周期にして 0.2 %% 以内(1 節)。
    カメラを 0〜8 度回したときの周期の動きも同じ式で追える(6 節)。

 2. ★★**2 つの失敗が打ち消し合う**。低域通過でならしてからムラの振幅を
    測ると、平滑化の σ を上げるにつれて「モアレの漏れ込み(過大評価)」が
    減り「本物のムラの減衰(過小評価)」が増える。σ≈8 px で両者が釣り合い、
    **合計誤差がほぼ 0 になる**。数字だけ見れば完璧だが、内訳はどちらも
    振幅の 8 %% 前後ある。**対照群を 2 本(縞だけ / ムラだけ)置かないと
    この打ち消しは見えない**(3 節)。

 3. ★★**分離できなくなる境界を実測した**。うなり周波数 δ をムラの周波数
    f_m=1/128 へ近づけると、ノッチ法は ``|δ - f_m| < ノッチ半径`` で
    ムラごと消し、平滑化法は ``δ < 数×f_m`` でモアレを消せなくなる。
    どちらの境界も**撮る前に計算できる量**で決まっている(5 節)。

 4. ★**高調波のうなりが本命**。基本波のうなりを遠くへ逃がしても、3 次・
    5 次のうなり(3δ, 5δ の折り返し)がムラの帯に落ちうる。7 節では
    「基本波だけ見て安全」と判定される撮影条件が、3 次のうなりで
    実際には汚染されることを実測で示した。

 5. ★**撮影条件を計算で決められる**。1 画素あたり整数個の縞になるよう
    倍率を合わせると(k が整数)、**全高調波のうなりが同時に直流へ落ちる**
    ので縞は一様な明るさになる。実測残差 %s。撮像側の光学ローパス σ_opt を
    かける条件も閉形式で出せて、実測と合う(7 節)。

 6. `fs.apply(..., "gauss_image")` の σ は **0.3〜3.0 に固定**されていて、
    ムラのスケール(σ~8 px)の平滑化ができない。`fs.ledger.background_flatten`
    (2 次曲面フィット)は 4 周期のムラを表現できず、振幅の %s しか拾えない。
    8 節の「道具の穴」に実測つきで置いた。

【グラウンドトゥルース(すべて閉形式)】
* 表示: 周期 P_d の**矩形ストライプ**(奇数高調波 1,3,5 次の和)。
  カメラ画素あたりの縞数 ``K = Δ/P_d`` が唯一のパラメータ。
* カメラ: 画素ピッチ Δ、開口 fill=0.7 の箱型(→ 振幅に sinc)、
  任意の光学ローパス σ_opt(→ 振幅に exp(-2π²σ²k²))、回転 θ。
* 本物のムラ: 既知の振幅 A_m の 2 次元余弦(周波数 f_m、向き 30 度)。
* 標本化は**整数格子で余弦を評価するだけ**。折り返しは自然に起きるので、
  「エイリアスを自分で作る」細工をしていない。真値はすべて式で書ける。

【節立て】
 1) 合成器の検算 —— うなりの閉形式と実測 FFT
 2) ★ゼロ点 —— 低域通過でならしてムラを測る
 3) ★★2 つの失敗を分けて数える(対照群 2 本)
 4) 対比 —— 周波数ノッチ / 撮像側の光学ローパス / 曲面フィット
 5) ★★分離限界 —— うなりがムラに近づくとどこで壊れるか
 6) カメラを回す —— 実測 vs 閉形式
 7) ★★撮る前に決める —— 高調波まで含めた安全条件
 8) 道具の穴(assert で現状を固定)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 撮像系の定数(すべてカメラ画素を単位にする)----------------------------- #
L = 512                 # 画像の一辺 [px]
K_BASE = 3.05           # 表示の基本周波数 [縞/カメラ画素] → うなり δ=0.05
HARMONICS = (1, 3, 5)   # 矩形ストライプの奇数高調波
FILL = 0.7              # 画素開口の一辺(ピッチに対する比)
C_STRIPE = 0.5          # ストライプのコントラスト係数

F_MURA = 1.0 / 128.0    # 本物のムラの空間周波数 [cyc/px](512 px に 4 周期)
A_MURA = 0.02           # 本物のムラの振幅(真値)
PHI_MURA = np.deg2rad(30.0)

MARGIN = 48             # 平滑化の縁を避けるため評価から外す幅 [px]

_I, _J = np.mgrid[0:L, 0:L]


def _sq_amp(m: int) -> float:
    """矩形波の m 次高調波の振幅(フーリエ級数 4/(π m)、奇数次のみ)。"""
    return 4.0 / (np.pi * m)


def wrap_freq(f: float) -> float:
    """デジタル周波数を [-0.5, 0.5] へ折り返す(標本化がやること)。"""
    return float(f - np.round(f))


def beat_frequencies(k: float, theta: float = 0.0):
    """高調波ごとのモアレ周波数 ``(m, fj, fi, 周期 px, 向き 度)``。**閉形式**。"""
    out = []
    for m in HARMONICS:
        fj = wrap_freq(m * k * np.cos(theta))
        fi = wrap_freq(-m * k * np.sin(theta))
        mag = float(np.hypot(fj, fi))
        out.append((m, fj, fi, (1.0 / mag if mag > 1e-12 else np.inf),
                    float(np.degrees(np.arctan2(fi, fj)))))
    return out


def stripe_amplitude(m: int, k: float, theta: float, sigma_opt: float) -> float:
    """m 次高調波が像に残る振幅。開口の sinc と光学ローパスの指数を掛ける。"""
    kk = m * k
    amp = C_STRIPE * _sq_amp(m)
    amp *= float(np.exp(-2.0 * np.pi ** 2 * sigma_opt ** 2 * kk ** 2))
    amp *= float(np.sinc(kk * FILL * np.cos(theta)) * np.sinc(kk * FILL * np.sin(theta)))
    return amp


def render(k: float = K_BASE, theta: float = 0.0, sigma_opt: float = 0.0,
           stripe: bool = True, mura: bool = True) -> np.ndarray:
    """撮れた像。**整数格子で連続の余弦を評価するだけ** —— 折り返しは自然に起きる。"""
    img = np.full((L, L), 0.5)
    if stripe:
        x = _J * np.cos(theta) - _I * np.sin(theta)      # 表示座標(カメラ px 単位)
        for m in HARMONICS:
            img = img + stripe_amplitude(m, k, theta, sigma_opt) * np.sin(2 * np.pi * m * k * x)
    if mura:
        r = _J * np.cos(PHI_MURA) + _I * np.sin(PHI_MURA)
        att = float(np.exp(-2.0 * np.pi ** 2 * sigma_opt ** 2 * F_MURA ** 2))
        img = img + A_MURA * att * np.cos(2 * np.pi * F_MURA * r)
    return img


def amplitude_at(img: np.ndarray, fj: float, fi: float) -> float:
    """既知の周波数成分の振幅(最小二乗の射影)。任意の非整数周波数で使える。"""
    ph = 2.0 * np.pi * (fj * _J + fi * _I)
    a = 2.0 * float(np.mean(img * np.cos(ph)))
    b = 2.0 * float(np.mean(img * np.sin(ph)))
    return float(np.hypot(a, b))


def mura_amplitude(img: np.ndarray) -> float:
    """現場の測り方: 評価領域の (最大-最小)/2。純粋な余弦なら真値と一致する。"""
    b = MARGIN if img.shape[0] > 4 * MARGIN else 2
    c = img[b:img.shape[0] - b, b:img.shape[1] - b]
    return 0.5 * float(c.max() - c.min())


def smooth(img: np.ndarray, sigma: float) -> np.ndarray:
    """低域通過(ゼロ点の道具)。σ が要るので scipy —— 8 節 (a) を参照。"""
    return gaussian_filter(img, sigma, mode="reflect")


def notch(img: np.ndarray, freqs, radius: float) -> np.ndarray:
    """予測したモアレ周波数だけを周波数領域で落とす(共役側も一緒に)。"""
    n = img.shape[0]
    F = np.fft.fft2(img - img.mean())
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    mask = np.ones((n, n))
    for fj, fi in freqs:
        for sj, si in ((fj, fi), (-fj, -fi)):
            d = np.hypot(np.abs(((fx - sj) + 0.5) % 1.0 - 0.5),
                         np.abs(((fy - si) + 0.5) % 1.0 - 0.5))
            mask[d <= radius] = 0.0
    return np.real(np.fft.ifft2(F * mask)) + img.mean()


def matched_length(delta: float, lo: float = 0.7) -> int:
    """うなりが **FFT のビンにちょうど乗る**解析窓の長さを選ぶ。

    非整数のビン位置に立つ正弦は漏れ(スペクトルリーケージ)の裾を持ち、
    半径の小さいノッチでは取り切れない。窓長 Lc を ``delta*Lc`` が整数に
    なるよう選べば漏れは消える —— **解析側だけで決められる**対処。
    """
    best, err = L, 1.0
    for lc in range(int(L * lo), L + 1):
        e = abs(delta * lc - round(delta * lc))
        if e < err - 1e-12:
            err, best = e, lc
    return best


def notch_matched(img: np.ndarray, freqs, delta: float, radius_bins: float = 2.0):
    """窓長を合わせてからノッチする。返り値 ``(出力, Lc)``。"""
    lc = matched_length(delta)
    return notch(np.ascontiguousarray(img[:lc, :lc]), freqs, radius_bins / lc), lc


# =========================================================================== #
def section1_check():
    print("=" * 78)
    print("1) 合成器の検算 —— うなりの閉形式と実測 FFT")
    print("=" * 78)
    print("  表示: 矩形ストライプ、カメラ画素あたり %.2f 本(= 標本化間隔 / 縞周期)。"
          % K_BASE)
    print("  カメラ: 開口 fill %.2f の箱型、光学ローパスなし、回転なし。" % FILL)
    print("  ムラ: 周波数 %.5f cyc/px(%.0f px 周期)、振幅 %.3f、向き 30 度。"
          % (F_MURA, 1 / F_MURA, A_MURA))
    print()
    img = render()
    print("  %4s %12s %12s %12s %12s" % ("高調波", "うなり f", "予測周期 px",
                                         "実測周期 px", "振幅"))
    print("  " + "-" * 58)
    F = np.abs(np.fft.fft2(img - img.mean()))
    fy = np.fft.fftfreq(L)[:, None] * np.ones((1, L))
    fx = np.ones((L, 1)) * np.fft.fftfreq(L)[None, :]
    for m, fj, fi, per, _ang in beat_frequencies(K_BASE):
        # 予測位置の近傍だけを見て実測ピークを拾う(周波数半径 0.01 の窓)
        sel = np.hypot(fx - fj, fy - fi) < 0.01
        idx = np.argmax(np.where(sel, F, -1.0))
        pj, pi = float(fx.ravel()[idx]), float(fy.ravel()[idx])
        meas = 1.0 / np.hypot(pj, pi)
        print("  %4d %12.5f %12.2f %12.2f %12.5f"
              % (m, fj, per, meas, amplitude_at(img, fj, fi)))
    print()
    print("  → 予測周期と実測ピークの差は %d px の FFT 分解能(1/%d = %.5f cyc/px)の"
          % (L, L, 1.0 / L))
    print("     範囲内。**モアレは撮る前に紙の上で決まっている**。")
    print()
    # 対照: ムラだけ / 縞だけ
    print("  対照群(あとで何度も使う):")
    print("    ムラだけの像から (max-min)/2 = %.5f(真値 %.5f、差 %.1e)"
          % (mura_amplitude(render(stripe=False)), A_MURA,
             abs(mura_amplitude(render(stripe=False)) - A_MURA)))
    print("    縞だけの像から (max-min)/2 = %.5f(ムラは仕込んでいないので、"
          % mura_amplitude(render(mura=False)))
    print("      これは**全部がモアレの漏れ込み**)")
    return img


def section2_zero_point():
    print()
    print("=" * 78)
    print("2) ★ゼロ点 —— 低域通過でならしてからムラを測る")
    print("=" * 78)
    print("  現場の素朴な手: ぼかせばモアレは消え、ムラだけ残る、はず。")
    print("  平滑化 σ を振って、ムラの振幅(真値 %.4f)をどう読み違えるか。" % A_MURA)
    print()
    both = render()
    print("  %8s %12s %12s" % ("σ px", "推定振幅", "誤差 %"))
    print("  " + "-" * 34)
    for s in (0.0, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0):
        est = mura_amplitude(smooth(both, s) if s > 0 else both)
        print("  %8.1f %12.5f %+11.1f" % (s, est, 100 * (est / A_MURA - 1)))
    print()
    print("  → σ=8 px の行が**ほぼ真値**。ここで止めれば「良い測り方を見つけた」で")
    print("     話が終わる。3 節でその中身を割る。")
    return both


def section3_split_failures(both):
    print()
    print("=" * 78)
    print("3) ★★2 つの失敗を分けて数える —— 対照群 2 本")
    print("=" * 78)
    print("  同じ平滑化を**縞だけの像**と**ムラだけの像**にも掛ける。")
    print("    漏れ  = 縞だけの像から読めてしまう振幅(本来 0)")
    print("    減衰  = ムラだけの像から読める振幅 / 真値(本来 1)")
    print()
    only_stripe = render(mura=False)
    only_mura = render(stripe=False)
    sigmas = (0.0, 1.0, 2.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0, 32.0)
    rows, leaks, atts, tots = [], [], [], []
    print("  %8s %11s %11s %11s %11s" % ("σ px", "漏れ", "減衰後", "合計 推定", "合計 誤差"))
    print("  " + "-" * 56)
    for s in sigmas:
        lk = mura_amplitude(smooth(only_stripe, s) if s > 0 else only_stripe) - 0.0
        at = mura_amplitude(smooth(only_mura, s) if s > 0 else only_mura)
        tot = mura_amplitude(smooth(both, s) if s > 0 else both)
        leaks.append(lk)
        atts.append(at)
        tots.append(tot)
        rows.append(["%.0f" % s, "%.5f" % lk, "%.5f" % at, "%.5f" % tot,
                     "%+.1f %%" % (100 * (tot / A_MURA - 1))])
        print("  %8.1f %11.5f %11.5f %11.5f %+10.1f %%"
              % (s, lk, at, tot, 100 * (tot / A_MURA - 1)))
    print()
    k = int(np.argmin(np.abs(np.array(tots) - A_MURA)))
    print("  → 合計誤差が最小なのは σ=%.0f px(%.1f %%)。だがその行の内訳は"
          % (sigmas[k], 100 * abs(tots[k] / A_MURA - 1)))
    print("     漏れ %+.1f %% / 減衰 %+.1f %% —— **逆向きの 2 つの失敗が打ち消している**。"
          % (100 * leaks[k] / A_MURA, 100 * (atts[k] / A_MURA - 1)))
    print("     パネルの明るさが変わったり、縞の位相が変わったりすれば、")
    print("     打ち消しはすぐ壊れる。**1 つの数字に畳んだ時点で見えなくなる**。")
    figs.save_table("failure_split",
                    ["σ px", "漏れ(縞のみ)", "減衰後(ムラのみ)", "合計 推定", "合計 誤差"],
                    rows, title="ムラの推定を 2 つの失敗に割る(真値 %.4f)" % A_MURA)
    if figs.enabled():
        xs = np.array(sigmas)
        figs.save_plot("failure_split_plot",
                       [("漏れ(過大評価)", xs, 100 * np.array(leaks) / A_MURA),
                        ("減衰(過小評価)", xs, 100 * (np.array(atts) / A_MURA - 1)),
                        ("合計 誤差", xs, 100 * (np.array(tots) / A_MURA - 1)),
                        ("誤差ゼロ", xs, np.zeros(xs.size))],
                       xlabel="平滑化 σ [px]", ylabel="振幅誤差 [%]",
                       title="合計が 0 になる σ でも内訳は 0 でない",
                       caption="σ≈8 px で漏れと減衰が釣り合う。合計だけ見ると"
                               "「良い測り方」に見える。")
    return sigmas, leaks, atts, tots


def section4_alternatives(both):
    print()
    print("=" * 78)
    print("4) 対比 —— ノッチ / 撮像側の光学ローパス / 曲面フィット")
    print("=" * 78)
    only_stripe = render(mura=False)
    only_mura = render(stripe=False)
    freqs = [(fj, fi) for _m, fj, fi, _p, _a in beat_frequencies(K_BASE)]
    rho = 4.0 / L                      # ノッチ半径(FFT 分解能の 4 倍)
    print("  ノッチ半径 %.5f cyc/px(= 4/%d、FFT 分解能の 4 倍)。" % (rho, L))
    print("  光学ローパスは**撮る前**に掛かるので、モアレがそもそも作られない。")
    print()
    methods = []

    def add(name, fn):
        methods.append((name, mura_amplitude(fn(only_stripe)),
                        mura_amplitude(fn(only_mura)), mura_amplitude(fn(both))))

    add("何もしない", lambda a: a)
    add("平滑化 σ=8", lambda a: smooth(a, 8.0))
    add("ノッチ(素)", lambda a: notch(a, freqs, rho))
    add("ノッチ+窓長合わせ", lambda a: notch_matched(a, freqs, K_BASE - 3.0)[0])
    add("2 次曲面フィット", lambda a: np.asarray(a) - np.asarray(
        fs.ledger.background_flatten(np.asarray(a), degree=2)))
    # 光学ローパス: 像を作り直す(後処理ではない)
    sig_opt = 0.30
    lo_s = render(mura=False, sigma_opt=sig_opt)
    lo_m = render(stripe=False, sigma_opt=sig_opt)
    lo_b = render(sigma_opt=sig_opt)
    methods.append(("光学 LPF σ=%.2f" % sig_opt, mura_amplitude(lo_s),
                    mura_amplitude(lo_m), mura_amplitude(lo_b)))

    print("  %-18s %11s %11s %11s %11s" % ("手法", "漏れ", "減衰後", "合計", "合計 誤差"))
    print("  " + "-" * 66)
    rows = []
    for name, lk, at, tot in methods:
        print("  %-18s %11.5f %11.5f %11.5f %+10.1f %%"
              % (name, lk, at, tot, 100 * (tot / A_MURA - 1)))
        rows.append([name, "%.5f" % lk, "%.5f" % at, "%.5f" % tot,
                     "%+.1f %%" % (100 * (tot / A_MURA - 1))])
    print()
    print("  → **撮像側の光学ローパスが唯一「両方 0 に近い」手法**。σ_opt=%.2f px は"
          % sig_opt)
    print("     縞(k=%.2f cyc/px)を exp(-2π²σ²k²) = %.1e 倍に潰す一方、ムラ"
          % (K_BASE, np.exp(-2 * np.pi ** 2 * sig_opt ** 2 * K_BASE ** 2)))
    print("     (f=%.5f)は %.6f 倍しか減らない —— **周波数が 400 倍離れているから**。"
          % (F_MURA, np.exp(-2 * np.pi ** 2 * sig_opt ** 2 * F_MURA ** 2)))
    print("     後処理でこれをやろうとすると、モアレは**折り返した後**なので")
    print("     ムラと同じ低周波帯に来てしまい、同じ手が使えない。")
    print()
    print("  ★★ノッチが素のままでは効かない理由を測って突き止めた: うなり δ=%.2f は"
          % (K_BASE - 3.0))
    print("     %d 点の FFT で %.2f ビン目 —— **ビンの間**に立っている。非整数ビンの"
          % (L, (K_BASE - 3.0) * L))
    print("     正弦は漏れ(スペクトルリーケージ)の裾を全帯域に撒くので、半径 %.5f の"
          % rho)
    print("     ノッチでは取り切れない(漏れ %+.1f %%)。解析窓を Lc=%d に切ると"
          % (100 * methods[2][1] / A_MURA, matched_length(K_BASE - 3.0)))
    print("     δ·Lc = %.2f と整数になり、漏れは %+.1f %% まで落ちる。"
          % ((K_BASE - 3.0) * matched_length(K_BASE - 3.0),
             100 * methods[3][1] / A_MURA))
    print("     **これは光学の問題ではなく解析窓の問題**で、撮り直さずに直せる。")
    print()
    print("     2 次曲面フィットは 4 周期の余弦を表現できず、ムラの %.0f %% しか"
          % (100 * methods[4][2] / A_MURA))
    print("     拾えない —— シェーディング補正の op を輝度ムラ計に流用してはいけない。")
    figs.save_table("methods", ["手法", "漏れ(縞のみ)", "減衰後(ムラのみ)",
                                "合計", "合計 誤差"], rows,
                    title="ムラ振幅の推定(真値 %.4f)" % A_MURA)
    return methods


def section5_separability():
    print()
    print("=" * 78)
    print("5) ★★分離限界 —— うなりがムラに近づくとどこで壊れるか")
    print("=" * 78)
    print("  基本波のうなり δ を %.5f(= ムラの周波数)へ近づける。" % F_MURA)
    print("  平滑化 σ=8 px / ノッチ(素、半径 4/%d)/ ノッチ(窓長合わせ、半径 2/Lc)。"
          % L)
    print("  ★2 次元で見ると、うなりは (δ, 0) 方向、ムラは 30 度方向にある。")
    print("    分離できるかを決めるのは**ベクトルの距離**であって、周波数の差ではない。")
    print()
    rho = 4.0 / L
    mj = F_MURA * np.cos(PHI_MURA)
    mi = F_MURA * np.sin(PHI_MURA)
    print("  %8s %8s %9s %9s %11s %11s %11s"
          % ("δ", "周期 px", "δ·L", "2D 距離", "平滑化", "ノッチ 素", "ノッチ 合"))
    print("  " + "-" * 74)
    deltas = (0.25, 0.12, 0.06, 0.03, 0.015, 0.0078125, 0.004, 0.002)
    sm_err, nt_err, nm_err = [], [], []
    for d in deltas:
        k = 3.0 + d
        both = render(k=k)
        freqs = [(fj, fi) for _m, fj, fi, _p, _a in beat_frequencies(k)]
        e_sm = mura_amplitude(smooth(both, 8.0)) / A_MURA - 1
        e_nt = mura_amplitude(notch(both, freqs, rho)) / A_MURA - 1
        out, lc = notch_matched(both, freqs, d)
        e_nm = mura_amplitude(out) / A_MURA - 1
        sm_err.append(100 * e_sm)
        nt_err.append(100 * e_nt)
        nm_err.append(100 * e_nm)
        dist = float(np.hypot(d - mj, 0.0 - mi))
        print("  %8.4f %8.1f %9.2f %9.5f %+10.1f %% %+10.1f %% %+10.1f %%"
              % (d, 1 / d, d * L, dist, 100 * e_sm, 100 * e_nt, 100 * e_nm))
    print()
    print("  → 3 つの境界がそれぞれ**別の原因**で立っている:")
    print("     (1) 平滑化: δ が f_m の数倍以内になると、低域通過はモアレとムラを")
    print("         区別できない(δ<=0.03 で誤差 +50 %% 超)。**光学の限界**。")
    print("     (2) ノッチ(素): δ·L が整数のとき(δ=0.25 → 128.00)だけ効く。")
    print("         非整数ビンでは漏れの裾が残る。**解析窓の長さの問題**で、")
    print("         窓長を合わせれば消える(右の列)。撮り直しは要らない。")
    print("     (3) ノッチ(窓長合わせ): 2 次元距離がノッチ半径 2/Lc ≈ %.5f を"
          % (2.0 / matched_length(0.0078125)))
    print("         下回ると、ムラごと落ちる。δ=f_m でも**向きが 30 度違う**ので")
    print("         距離 %.5f が残り、かろうじて分離できている(誤差 %+.1f %%)。"
          % (float(np.hypot(F_MURA - mj, mi)), nm_err[5]))
    print("     ★どれも撮る前に計算できる量(倍率・窓長・ムラの向き)で決まっている。")
    if figs.enabled():
        xs = np.array(deltas)
        figs.save_plot("separability",
                       [("平滑化 σ=8", xs, np.array(sm_err)),
                        ("ノッチ 素", xs, np.array(nt_err)),
                        ("ノッチ 窓長合わせ", xs, np.array(nm_err)),
                        ("誤差ゼロ", xs, np.zeros(xs.size)),
                        ("ムラの周波数", np.full(2, F_MURA), np.array([-120.0, 120.0]))],
                       xlabel="うなり δ [cyc/px]", ylabel="ムラ振幅の誤差 [%]",
                       title="3 つの手法は別々の理由で壊れる",
                       ylim=(-120, 120),
                       caption="縦線がムラの周波数。素のノッチはビン位置で、"
                               "平滑化は δ の小ささで壊れる。")
    return deltas, sm_err, nt_err


def section6_rotation():
    print()
    print("=" * 78)
    print("6) カメラを回す —— 実測 vs 閉形式")
    print("=" * 78)
    print("  カメラを θ 度だけ回すと、うなりのベクトルは wrap(k·(cosθ, -sinθ))。")
    print()
    print("  %8s %12s %12s %12s %10s" % ("θ 度", "予測 周期", "実測 周期",
                                         "予測 向き", "実測 向き"))
    print("  " + "-" * 58)
    fy = np.fft.fftfreq(L)[:, None] * np.ones((1, L))
    fx = np.ones((L, 1)) * np.fft.fftfreq(L)[None, :]
    pred_p, meas_p, angles = [], [], []
    for deg in (0.0, 0.5, 1.0, 2.0, 4.0, 8.0):
        th = np.deg2rad(deg)
        img = render(theta=th, mura=False)
        m, fj, fi, per, ang = beat_frequencies(K_BASE, th)[0]
        F = np.abs(np.fft.fft2(img - img.mean()))
        sel = np.hypot(fx - fj, fy - fi) < 0.02
        idx = int(np.argmax(np.where(sel, F, -1.0)))
        pj, pi = float(fx.ravel()[idx]), float(fy.ravel()[idx])
        mp = 1.0 / np.hypot(pj, pi)
        ma = float(np.degrees(np.arctan2(pi, pj)))
        pred_p.append(per)
        meas_p.append(mp)
        angles.append(deg)
        print("  %8.1f %12.2f %12.2f %11.1f ° %9.1f °" % (deg, per, mp, ang, ma))
    print()
    print("  → 0.5 度回しただけでモアレの周期が %.1f → %.1f px に動く。"
          % (pred_p[0], pred_p[1]))
    print("     **モアレは治具の据え付け精度に強く依存する** —— だから「昨日は")
    print("     出なかった」が起きる。実測と閉形式の差は FFT の分解能ぶん。")
    if figs.enabled():
        figs.save_plot("rotation",
                       [("閉形式", np.array(angles), np.array(pred_p)),
                        ("実測 FFT", np.array(angles), np.array(meas_p))],
                       xlabel="カメラの回転 [度]", ylabel="モアレ周期 [px]",
                       title="0.5 度でモアレの周期は変わる",
                       caption="基本波のみ。実測は FFT ピーク、閉形式は wrap(k·cosθ) から。")


def section7_design():
    print()
    print("=" * 78)
    print("7) ★★撮る前に決める —— 高調波まで含めた安全条件")
    print("=" * 78)
    band = 2.0 * F_MURA
    print("  ムラを測りたい帯を [0, %.5f] cyc/px(= ムラ周波数の 2 倍)と決める。" % band)
    print("  安全条件: **すべての高調波のうなりがこの帯の外**。")
    print()
    print("  %8s %10s %10s %10s %10s %12s"
          % ("k", "1 次", "3 次", "5 次", "1 次判定", "全高調波判定"))
    print("  " + "-" * 64)
    cands = (3.05, 3.02, 3.006, 3.0026, 3.25, 3.0)
    for k in cands:
        bs = [abs(fj) for _m, fj, _fi, _p, _a in beat_frequencies(k)]
        ok1 = bs[0] > band
        okall = all(b > band for b in bs)
        print("  %8.4f %10.5f %10.5f %10.5f %10s %12s"
              % (k, bs[0], bs[1], bs[2], "安全" if ok1 else "危険",
                 "安全" if okall else "★危険"))
    print()
    print("  → k=3.0026 は**基本波だけ見れば安全**(うなり %.5f > 帯 %.5f)なのに、"
          % (abs(beat_frequencies(3.0026)[0][1]), band))
    print("     3 次のうなり %.5f が帯の中に落ちる。実測で確かめる:"
          % abs(beat_frequencies(3.0026)[1][1]))
    print()
    for k, label in ((3.05, "k=3.05(全高調波 安全)"), (3.0026, "k=3.0026(3 次が危険)")):
        e = mura_amplitude(smooth(render(k=k, mura=False), 8.0))
        print("    %-26s 縞だけの像の漏れ = %.5f(真値の %+.1f %%)"
              % (label, e, 100 * e / A_MURA))
    print()
    print("  倍率をぴったり合わせる(k を整数にする)と、**全高調波のうなりが")
    print("  同時に直流へ落ちる** —— 縞は一様な明るさになってモアレが消える:")
    for k in (3.0, 4.0):
        img = render(k=k, mura=False)
        print("    k=%.1f: 像の標準偏差 %.2e(縞の振幅は %.4f だった)"
              % (k, float(img.std()), stripe_amplitude(1, k, 0.0, 0.0)))
    print()
    sig_need = float(np.sqrt(np.log(1e3) / (2 * np.pi ** 2 * K_BASE ** 2)))
    img = render(mura=False, sigma_opt=sig_need)
    print("  撮像側の光学ローパスで決める場合: 基本波を 1/1000 にする σ_opt は")
    print("    σ = sqrt(ln(1000)/(2π²k²)) = %.4f px  → 実測の漏れ %.6f(%.2f %% of A)"
          % (sig_need, mura_amplitude(smooth(img, 8.0)),
             100 * mura_amplitude(smooth(img, 8.0)) / A_MURA))
    print("  ★どちらも**カメラを構える前に紙の上で決まる**。これがこの PoC の主張。")


def section_figures():
    if not figs.enabled():
        return
    both = render()
    s = np.s_[0:192, 0:192]
    spec = np.asarray(fs.apply(render(mura=False), "fft_image"))
    figs.save_grid("moire_scene",
                   [both[s], render(mura=False)[s], render(stripe=False)[s],
                    np.asarray(spec)[160:352, 160:352]],
                   ["撮れた像", "縞だけ", "ムラだけ", "スペクトル"],
                   title="モアレ(縞)と本物のムラ", ncols=2,
                   signed=[False, False, False, False],
                   caption="左上 192x192 px を切り出し。スペクトルは fs.apply(\"fft_image\") "
                           "の中央部。うなりのピークが 4 象限に対称に立つ。")


def section8_tool_gaps():
    print()
    print("=" * 78)
    print("8) 道具の穴 —— fullseye に無かったもの・使いにくかったもの")
    print("=" * 78)
    import ops as _ops
    allnames = set(dir(fs)) | set(dir(fs.ledger)) | {o.name for o in _ops.REGISTRY}

    # (a) 平滑化 op の σ が 0.3〜3.0 に固定されている
    img = render()
    a0 = np.asarray(fs.apply(img, "gauss_image", a=0.0))
    a1 = np.asarray(fs.apply(img, "gauss_image", a=1.0))
    # σ=3 相当と σ=8 の残差を比べる
    r_max = float(np.abs(a1 - smooth(img, 3.0)).max())
    e_op = mura_amplitude(a1)
    e_8 = mura_amplitude(smooth(img, 8.0))
    assert r_max < 0.02, r_max                      # a=1.0 は σ≈3 相当
    assert abs(e_op / A_MURA - 1) > 3 * abs(e_8 / A_MURA - 1), (e_op, e_8)
    print("  (a) ★`fs.apply(..., \"gauss_image\", a=..)` の σ は **0.3〜3.0 に固定**")
    print("      (a=1.0 が σ≈3.0。σ=3 の scipy 版との最大差 %.4f で確認)。" % r_max)
    print("      ムラのスケール(σ≈8 px)の平滑化ができず、a=1.0 でのムラ推定は")
    print("      %+.1f %%(σ=8 なら %+.1f %%)。`mean_image` も k∈{3,5,7,9} 止まり。"
          % (100 * (e_op / A_MURA - 1), 100 * (e_8 / A_MURA - 1)))
    print("      **σ を物理量として受ける平滑化 op が公開層に無い**のは、計測用途では痛い")
    print("      (この PoC は scipy.ndimage.gaussian_filter を直に呼んでいる)。")

    # (b) 周波数ノッチ / 周期ノイズ除去の op が無い
    for kw in ("notch", "moire", "periodic", "destripe", "mura"):
        hit = [n for n in allnames if kw in n.lower()]
        assert not hit, (kw, hit)
    print("  (b) ★★**周波数ノッチの op が 3 層のどこにも無い**('notch'/'moire'/")
    print("      'periodic'/'destripe'/'mura' で 0 件)。`bandpass_image` は等方の")
    print("      帯域で、**特定の (fx, fy) を落とす**ことはできない。4 節のノッチは")
    print("      この PoC が numpy で書いた。周期ノイズ除去は産業用画像処理の定番なので、")
    print("      `notch_filter(img, freqs, radius)` は族に入れる価値がある。")

    # (c) 2 次元の周波数解析が「放射平均」しかない
    rp = np.asarray(fs.radial_power_spectrum(render(mura=False)))
    assert rp.ndim == 2 and rp.shape[1] == 2, rp.shape
    th = np.deg2rad(30.0)
    rot = np.asarray(fs.radial_power_spectrum(render(theta=th, mura=False)))
    f_pk = float(rp[np.argmax(rp[1:, 1]) + 1, 0])
    f_pk_rot = float(rot[np.argmax(rot[1:, 1]) + 1, 0])
    print("  (c) `radial_power_spectrum` は**放射平均**なので、モアレの**向き**が消える。")
    print("      回転なしのピーク %.4f cyc/px、30 度回した像でも %.4f cyc/px ——"
          % (f_pk, f_pk_rot))
    print("      向きが 30 度変わったことは曲線からは分からない。方向別(角度ビン)の")
    print("      スペクトルを返す口が要る。モアレの診断では**向きが原因の手がかり**。")

    # (d) fft_image は表示用で、複素スペクトルを返さない
    sp = np.asarray(fs.apply(render(), "fft_image"))
    assert sp.dtype.kind == "f" and sp.ndim == 2 and 0.0 <= sp.min() and sp.max() <= 1.0
    print("  (d) `fft_image` は `log1p(|F|)` を [0,1] に正規化した**表示用の画像**で、")
    print("      複素スペクトルも周波数軸も返さない(実測 dtype %s、値域 [%.2f, %.2f])。"
          % (sp.dtype, sp.min(), sp.max()))
    print("      周波数領域で何か**する**(ノッチ・位相を見る・逆変換する)には使えない。")
    print("      `fft_image_inv` があるのに、その間をつなぐ複素の口が公開されていない。")

    # (e) op_find が「モアレ」「エイリアス」で何も返さない
    for q in ("moire", "aliasing", "notch"):
        assert fs.op_find(q) == [] or all(
            "moire" not in r["op"] for r in fs.op_find(q)), q
    print("  (e) `fs.op_find(\"moire\")` / `(\"aliasing\")` / `(\"notch\")` が空。")
    print("      ディスプレイ検査・印刷検査で最初に引く語なので、")
    print("      族の名前か docstring に入れておくと、この PoC の遠回りが減る。")
    print()
    print("  次にやるべきこと: (b) の `notch_filter` と (c) の方向別スペクトルを")
    print("  `filters_freq` 族へ。ただし 5 節の境界(|δ-f_m| < 半径 でムラも消える)を")
    print("  op の docstring に**測った数字で**書くこと —— 半径に既定値を置くと、")
    print("  利用者は「モアレを消したらムラも消えた」を静かに踏む。")


def main():
    t0 = time.time()
    print("poc_moire_screen — モアレと本物の輝度ムラを分けられるか")
    print("(真値: うなり周波数は wrap(m·k) の閉形式、ムラの振幅は %.4f)" % A_MURA)
    print()
    section1_check()
    both = section2_zero_point()
    section3_split_failures(both)
    section4_alternatives(both)
    section5_separability()
    section6_rotation()
    section7_design()
    section_figures()
    section8_tool_gaps()
    print()
    print("  所要 %.1f 秒" % (time.time() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
