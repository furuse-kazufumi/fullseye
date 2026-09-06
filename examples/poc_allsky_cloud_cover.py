# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_allsky_cloud_cover — 全天カメラの雲量。**画素を数えると位置で偏る**。

    py -3.11 examples/poc_allsky_cloud_cover.py

【この PoC が答える問い】
全天カメラ(魚眼)の雲量は、日射予測・天文観測・気象観測の基礎量です。素朴な
作り方は「雲と判定した画素 ÷ 空の画素」。問いは「**その 1 行がどれだけ嘘か**」。
答えは「**同じ雲が、天頂にあれば -18.9 %、地平線側にあれば +17.4 % に読める**。
真の雲量は天球上の**立体角**の割合であって、画素の数ではない」。

【グラウンドトゥルース(自分で仕込んだ真値)】
雲は**天球上の球冠**(中心方向と角半径 α)として置く。球冠の立体角は
**2π(1-cos α)** という閉形式。重ならないように置けば全体も閉形式で出る。
それを**等距離射影 r = f·θ**(魚眼の標準)で画像へ落とす。だから
「真の雲量」は測定と無関係に分かっている。マスクを切ったときの真値だけは
(θ, φ) の細かい格子で ∫sinθ dθ dφ を数値積分する —— その積分器は 1 節で
閉形式と突き合わせて検算する。

【この PoC が示すこと(数字はすべて実行時に印字される実測値)】

 1. **検算**。球冠の閉形式と数値積分は α=10/20/30 度で **1.9e-4** 以内。
    立体角重みの範囲は **0.6366 〜 1.0000** —— 地平線の 1 画素は天頂の
    1 画素の **64 %** の立体角しか代表していない。
 2. ★★**ゼロ点(画素数比)は雲の位置で系統的に偏る**。角半径 8 度の同じ雲を
    天頂角 0 → 82 度へ動かすと、雲量の推定は **0.00789 → 0.01142**(真値は
    どちらも 0.00973)。**推定/真値 = 0.811 → 1.174**、つまり同じ空が
    **1.45 倍**違って読める。★閉形式 (θ/sinθ)/(θmax²/2) との差は最大 **0.0026**。
 3. ★★**重み sinθ/θ を掛けると直る**。同じ 6 通りで推定/真値は 0.9990〜1.0004。
    ★**予想が外れた**。着手前は「等距離射影は天頂を引き伸ばし地平線を圧縮する」
    と思っていたが**逆**。r = f·θ では地平線側の**方位方向**が引き伸ばされ
    (θ/sinθ → π/2 = 1.571)、**画素数は地平線を過大に代表する**。
 4. ★**同じ真値・違う配置**。雲を天頂寄りに集めた空と地平線寄りに集めた空で
    真の雲量を揃える(0.07719 と 0.07715)と、画素数比は **0.0641 と 0.0831**
    (**1.30 倍**)。重みつきは **どちらも 0.0772** = 真値。
 5. ★★**太陽まわりの偽陽性**。RBR(赤/青)は散乱で太陽の周りが白むので、
    **雲がゼロの晴天でも雲量 7.25 % が出る**。閉形式 1-cos(ψ_t) との差は
    6 通りで最大 **7.8e-06**(ψ_t = 21.9 度)。しきい値を上げれば
    0.0965 → 0.0064 に減るが、★**薄い雲の検出率が 1.00 → 0.00 に落ちる**。
    両方を 1 つの誤差にまとめると最適点が偽物になる。
 6. ★★**幾何の誤差と検出の誤差は別物で、しかも打ち消し合う**。対照群
    (真のマスク = 検出を止めた条件)で幾何だけの誤差は **-4.65 %**、
    重みつき + RBR で検出だけの誤差は **+47.19 %**。ところが素朴な
    「RBR x 画素数比」は **+38.41 %** —— 足し算(+42.55 %)より**小さい**。
    ★**符号が逆の 2 つの失敗が打ち消して、いちばん素朴な数え方がいちばん
    まともに見える**。重みを掛けると幾何は 0.01 % まで直るが検出は残る。
 7. ★**地平線マスク**を 90 → 70 度に絞ると、真値そのものが 0.1536 → 0.1879
    (**+22 %**)動く。画素数比の偏りは **-4.65 % → -0.71 %** と縮み、
    重みつきは **どの角度でも +0.01 %**。★「マスクを厳しくしたら一致した」は
    直った証拠にならない(いちばん偏っている帯を捨てているだけ)。
    **マスクの角度を書かずに雲量を報告した数字は比較できない** ——
    同じ空・同じ検出器で 0.1536 〜 0.1879 を名乗れる。

【節立て】
 1) 合成器と積分器の検算
 2) ★★ゼロ点(画素数比)と 2 つの偏り / ★重み sinθ/θ で直す(予想外の向き)
 3) ★同じ真値・違う配置
 4) ★★RBR と太陽 —— 検出の誤差
 5) ★★幾何と検出を分けて数える(対照群 = 真のマスク)
 6) ★地平線マスク掃引
 7) 道具の穴(assert で現状を固定)

EXTEND: 実写に差し替えるなら :func:`render` の返り値と ``CAPS`` の対を、
全天カメラの RGB と「同時刻の雲の立体角」に置き換える。**真値を別の全天
カメラの画素数比から作らないこと** —— 同じ偏りを共有するので、この PoC が
測っている量が丸ごと消える。ライダー・シーロメータの雲底高度から立体角を
組むか、静止気象衛星の雲マスクを地表点から見た立体角に投影する。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 魚眼の諸元 -------------------------------------------------------------- #
N_PX = 512
R_PX = 244.0                       # 天頂角 90 度が落ちる半径 [px]
TH_MAX = np.pi / 2
F_PX = R_PX / TH_MAX               # 等距離射影 r = f*theta
CTR = (N_PX - 1) / 2.0
SS = 3                             # 画素あたりの副標本(片側)

# --- 空のモデル -------------------------------------------------------------- #
TH_SUN, PH_SUN = np.deg2rad(45.0), np.deg2rad(30.0)
PSI0 = np.deg2rad(20.0)            # 太陽まわりの白み(アウレオール)の広がり
RBR_BASE, RBR_AUR = 0.45, 0.50     # 晴天 RBR = BASE + AUR*exp(-(psi/PSI0)^2)
RBR_T = 0.60                       # 雲判定のしきい値(Long & DeLuisi の定番)
CLOUD_LEVEL = 1.2                  # 雲の放射輝度(R も B も同じ = 白い)

#: 雲 = 球冠 (天頂角, 方位角, 角半径, 不透明度)。重ならないように置いてある。
CAPS = [(15.0, 200.0, 12.0, 1.00),
        (38.0, 120.0, 14.0, 1.00),
        (55.0, 300.0, 16.0, 1.00),
        (70.0, 240.0, 14.0, 1.00),
        (78.0, 20.0, 10.0, 1.00),
        (45.0, 220.0, 11.0, 0.35)]     # ★最後の 1 つは薄い雲
CAPS_ZENITH = [(8.0, 0.0, 14.0, 1.0), (22.0, 140.0, 13.0, 1.0),
               (26.0, 260.0, 12.0, 1.0)]
CAPS_HORIZON = [(72.0, 0.0, 14.0, 1.0), (70.0, 140.0, 13.0, 1.0),
                (74.0, 260.0, 12.0, 1.0)]


def unit(th, ph):
    """(天頂角, 方位角) → 単位ベクトル。末尾軸が xyz。"""
    th, ph = np.broadcast_arrays(np.asarray(th, float), np.asarray(ph, float))
    return np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)], -1)


def _pixel_grid():
    """副標本ごとの (theta, phi, 円の内か)。**画像の幾何をここに 1 か所だけ持つ**。"""
    off = (np.arange(SS) + 0.5) / SS - 0.5
    th, ph, ins = [], [], []
    yy, xx = np.mgrid[0:N_PX, 0:N_PX].astype(float)
    for dy in off:
        for dx in off:
            dr, dc = yy + dy - CTR, xx + dx - CTR
            r = np.hypot(dr, dc)
            th.append(r / F_PX)
            ph.append(np.arctan2(dr, dc))
            ins.append(r <= R_PX)
    return np.array(th), np.array(ph), np.array(ins)


TH, PH, INSIDE = _pixel_grid()
N_HAT = unit(TH, PH)
PSI = np.arccos(np.clip(N_HAT @ unit(TH_SUN, PH_SUN), -1.0, 1.0))

#: ★立体角の重み。dΩ/dA = sinθ/(f²θ) —— 等距離射影のヤコビアン。
W_SOLID = np.where(TH > 1e-9, np.sin(TH) / np.maximum(TH, 1e-9), 1.0) * INSIDE


def _rad(caps):
    return [(np.deg2rad(t), np.deg2rad(p), np.deg2rad(a), tau) for t, p, a, tau in caps]


def coverage(caps):
    """副標本ごとの雲の不透明度(重なりは濃いほうを採る)。"""
    c = np.zeros(TH.shape)
    for th, ph, al, tau in _rad(caps):
        c = np.maximum(c, tau * ((N_HAT @ unit(th, ph)) >= np.cos(al)))
    return c


def render(caps):
    """RBR 画像と、見せるための RGB。放射輝度で混ぜてから比を取る。"""
    c = coverage(caps)
    clear = RBR_BASE + RBR_AUR * np.exp(-(PSI / PSI0) ** 2)
    blue = c * CLOUD_LEVEL + (1 - c) * 1.0
    red = c * CLOUD_LEVEL + (1 - c) * clear
    rbr = (red / blue).mean(0)
    r8, b8 = red.mean(0), blue.mean(0)
    disc = INSIDE.mean(0)
    rgb = np.stack([r8, 0.5 * (r8 + b8), b8], -1) / CLOUD_LEVEL * disc[..., None]
    return rbr, np.clip(rgb, 0, 1), disc


def truth_fraction(caps, th_max=TH_MAX, n_th=1400, n_ph=1400):
    """真の雲量 = 立体角の割合。(θ, φ) の細かい格子で ∫sinθ dθ dφ を数える。"""
    th = (np.arange(n_th) + 0.5) / n_th * th_max
    ph = (np.arange(n_ph) + 0.5) / n_ph * 2 * np.pi
    nv = unit(th[:, None], ph[None, :])
    m = np.zeros(nv.shape[:2], bool)
    for t, p, al, _ in _rad(caps):
        m |= (nv @ unit(t, p)) >= np.cos(al)
    w = np.sin(th)
    return float((m * w[:, None]).sum() / (w.sum() * n_ph))


def estimate(mask, th_max=TH_MAX):
    """雲量の 2 通りの数え方 → (画素数比, 立体角の重みつき)。"""
    lim = TH <= th_max
    dom = INSIDE & lim
    px = float(mask[dom].mean()) if dom.any() else float("nan")
    w = W_SOLID * lim
    return px, float((mask * w).sum() / w.sum())


def detect(rbr_sub, t=RBR_T):
    """RBR で雲を判定(副標本ごと)。"""
    return rbr_sub > t


def rbr_sub(caps):
    """副標本を潰さない RBR(判定は副標本の解像度で行う)。"""
    c = coverage(caps)
    clear = RBR_BASE + RBR_AUR * np.exp(-(PSI / PSI0) ** 2)
    return (c * CLOUD_LEVEL + (1 - c) * clear) / (c * CLOUD_LEVEL + (1 - c) * 1.0)


# --------------------------------------------------------------------------- #
# 1) 検算                                                                      #
# --------------------------------------------------------------------------- #
def section1_check():
    print("=" * 78)
    print("1) 合成器と積分器の検算(ゼロ点その 0)")
    print("=" * 78)
    print("  球冠の立体角は 2π(1-cos α)。数値積分がそれを再現するか。")
    print()
    print("  %8s %14s %14s %12s" % ("α [度]", "閉形式", "数値積分", "差"))
    print("  " + "-" * 52)
    worst = 0.0
    for a in (10.0, 20.0, 30.0):
        closed = 1.0 - np.cos(np.deg2rad(a))
        num = truth_fraction([(0.0, 0.0, a, 1.0)])
        worst = max(worst, abs(num - closed))
        print("  %8.0f %14.6f %14.6f %12.2e" % (a, closed, num, abs(num - closed)))
    tot = float(W_SOLID.sum() / W_SOLID.sum())
    print()
    print("  → 差は最大 %.1e。積分器は使える。" % worst)
    print("     立体角重み map の総和(正規化後)= %.6f、重みの範囲 %.4f 〜 %.4f。"
          % (tot, W_SOLID[INSIDE].min(), W_SOLID[INSIDE].max()))
    print("     天頂で 1.000、地平線で sin(90°)/(π/2) = %.4f —— **地平線の 1 画素は"
          % (1.0 / (np.pi / 2)))
    print("     天頂の 1 画素の %.0f %% の立体角しか代表していない**。"
          % (100.0 / (np.pi / 2)))
    return worst


# --------------------------------------------------------------------------- #
# 2) ゼロ点と重み                                                              #
# --------------------------------------------------------------------------- #
def section2_zero_point():
    print()
    print("=" * 78)
    print("2) ★★ゼロ点(雲の画素 ÷ 空の画素)—— 同じ雲を天頂から地平線へ")
    print("=" * 78)
    alpha = 8.0
    truth = 1.0 - np.cos(np.deg2rad(alpha))
    print("  角半径 %.0f 度の雲を 1 つだけ置く。真の雲量は位置によらず %.5f。"
          % (alpha, truth))
    print("  閉形式の予測: 画素数比/真値 = (θ/sinθ)/(θmax²/2)。")
    print()
    print("  %8s %11s %11s %11s %11s %11s" %
          ("天頂角", "画素数比", "重みつき", "画素/真値", "重み/真値", "閉形式"))
    print("  " + "-" * 68)
    thc = [0.0, 20.0, 40.0, 60.0, 75.0, 82.0]
    px_r, wt_r, law = [], [], []
    for t in thc:
        m = coverage([(t, 0.0, alpha, 1.0)]) > 0
        px, wt = estimate(m)
        tr = np.deg2rad(t)
        pred = ((tr / np.sin(tr)) if tr > 1e-9 else 1.0) / (TH_MAX ** 2 / 2)
        px_r.append(px / truth)
        wt_r.append(wt / truth)
        law.append(pred)
        print("  %8.0f %11.5f %11.5f %11.4f %11.4f %11.4f"
              % (t, px, wt, px_r[-1], wt_r[-1], pred))
    dev = float(np.max(np.abs(np.array(px_r) - np.array(law))))
    print()
    print("  → ★★同じ雲が **%.5f 〜 %.5f**(%.2f 倍)に読める。真値は一定。"
          % (min(px_r) * truth, max(px_r) * truth, max(px_r) / min(px_r)))
    print("     画素数比/真値 は %.3f(天頂)→ %.3f(地平線側)。閉形式との差は"
          % (px_r[0], px_r[-1]))
    print("     最大 %.4f —— **ヤコビアン θ/sinθ そのもの**。" % dev)
    print("  → ★★重み sinθ/θ を掛けると %.4f 〜 %.4f。**位置に依らなくなる**。"
          % (min(wt_r), max(wt_r)))
    print("  → ★**予想が外れた**。着手前は「等距離射影は天頂を引き伸ばし、地平線を")
    print("     圧縮する」と思っていた。**逆**だった —— r = f·θ では地平線側で")
    print("     方位方向の周長 f·θ·dφ が立体角 sinθ·dθ·dφ より速く伸びるので、")
    print("     **画素数は地平線を過大に**代表する(θ/sinθ → π/2 = 1.571)。")
    figs.save_plot("jacobian",
                   [("実測 画素/真値", thc, px_r),
                    ("閉形式 (θ/sinθ)/(θmax²/2)", thc, law),
                    ("重みつき/真値", thc, wt_r),
                    ("正しい値 1.0", thc, [1.0] * len(thc))],
                   xlabel="雲の天頂角 [度]", ylabel="推定 / 真値",
                   title="同じ雲、違う答え(等距離射影のヤコビアン)",
                   caption="画素数比は天頂で 0.81、地平線側で 1.17。重みを掛けると 1 に張り付く。")
    return px_r, wt_r, law, dev


# --------------------------------------------------------------------------- #
# 3) 同じ真値・違う配置                                                        #
# --------------------------------------------------------------------------- #
def section3_layout():
    print()
    print("=" * 78)
    print("3) ★同じ真値・違う配置 —— 天頂寄りの空と地平線寄りの空")
    print("=" * 78)
    print("  雲を 3 つずつ、角半径を揃えて天頂寄り / 地平線寄りに置く。")
    print("  **真の雲量は同じ**(球冠の立体角は中心の位置によらない)。")
    print()
    print("  %-16s %12s %12s %12s %10s" % ("配置", "真値", "画素数比", "重みつき", "画素 誤差%"))
    print("  " + "-" * 66)
    out = {}
    for name, caps in (("天頂寄り", CAPS_ZENITH), ("地平線寄り", CAPS_HORIZON)):
        tr = truth_fraction(caps)
        m = coverage(caps) > 0
        px, wt = estimate(m)
        out[name] = (tr, px, wt)
        print("  %-16s %12.5f %12.5f %12.5f %+10.2f" % (name, tr, px, wt, 100 * (px / tr - 1)))
    a, b = out["天頂寄り"], out["地平線寄り"]
    print()
    print("  → 真値は %.5f と %.5f(差 %.1e)。画素数比は %.4f と %.4f で **%.2f 倍**。"
          % (a[0], b[0], abs(a[0] - b[0]), a[1], b[1], b[1] / a[1]))
    print("     重みつきは %.5f と %.5f —— **どちらも真値**。" % (a[2], b[2]))
    print("  → 実務の含意: 積雲が高く湧く午後と、層雲が地平線に居座る朝で、")
    print("     **同じ雲量でも画素数比は %.0f %% 違う**。日変化として報告される。"
          % (100 * (b[1] / a[1] - 1)))
    return out


# --------------------------------------------------------------------------- #
# 4) RBR と太陽                                                                #
# --------------------------------------------------------------------------- #
def section4_rbr_sun():
    print()
    print("=" * 78)
    print("4) ★★太陽まわりの偽陽性 —— 晴れているのに雲と判定される")
    print("=" * 78)
    print("  晴天 RBR = %.2f + %.2f·exp(-(ψ/%.0f度)²)。ψ = 太陽からの角距離。"
          % (RBR_BASE, RBR_AUR, np.rad2deg(PSI0)))
    print("  しきい値 t を超える領域は**太陽を中心とする球冠**なので、偽陽性の")
    print("  立体角は 1-cos(ψ_t)、ψ_t = ψ0·sqrt(ln(AUR/(t-BASE))) と閉形式で出る。")
    print()
    clear = rbr_sub([])
    full = rbr_sub(CAPS)
    thin = coverage([CAPS[-1]]) > 0
    print("  %6s %8s %10s %10s %10s %12s" %
          ("t", "ψ_t 度", "偽陽性 px", "偽陽性 重み", "閉形式", "薄雲 検出率"))
    print("  " + "-" * 62)
    ts = [0.55, 0.60, 0.65, 0.70, 0.80, 0.90]
    fp, law, thin_rec = [], [], []
    for t in ts:
        d0 = detect(clear, t)
        px, wt = estimate(d0)
        arg = max(np.log(RBR_AUR / max(t - RBR_BASE, 1e-12)), 0.0)
        psi_t = PSI0 * np.sqrt(arg)
        cl = 1.0 - np.cos(psi_t)
        rec = float((detect(full, t) & thin).sum() / max(thin.sum(), 1))
        fp.append(wt)
        law.append(cl)
        thin_rec.append(rec)
        print("  %6.2f %8.1f %10.4f %10.4f %10.4f %12.3f"
              % (t, np.rad2deg(psi_t), px, wt, cl, rec))
    dev = float(np.max(np.abs(np.array(fp) - np.array(law))))
    j = ts.index(RBR_T)
    print()
    print("  → ★★**雲がゼロの晴天で雲量 %.2f %% が出る**(t=%.2f)。閉形式との差は"
          % (100 * fp[j], RBR_T))
    print("     全 %d 通りで最大 %.1e —— **偽陽性の量は設計で決まっている**。"
          % (len(ts), dev))
    print("  → ★しきい値を上げれば偽陽性は %.4f → %.4f に減るが、**薄い雲の"
          % (fp[0], fp[-1]))
    print("     検出率が %.2f → %.2f に落ちる**。2 つを 1 つの誤差にまとめると、"
          % (thin_rec[0], thin_rec[-1]))
    print("     打ち消し合った点が「最適なしきい値」に見える —— 分けて数えること。")
    figs.save_plot("rbr_threshold",
                   [("偽陽性(実測 重みつき)", ts, fp),
                    ("偽陽性(閉形式 1-cosψ_t)", ts, law),
                    ("薄い雲の検出率", ts, thin_rec)],
                   xlabel="RBR のしきい値 t", ylabel="立体角の割合 / 検出率",
                   title="太陽の偽陽性と薄い雲は逆に動く",
                   caption="偽陽性は実測と閉形式が重なる。しきい値を上げると薄い雲が消える。")
    return ts, fp, law, thin_rec, dev


# --------------------------------------------------------------------------- #
# 5) 幾何と検出を分ける                                                        #
# --------------------------------------------------------------------------- #
def section5_split_errors():
    print()
    print("=" * 78)
    print("5) ★★幾何の誤差と検出の誤差を**分けて数える**")
    print("=" * 78)
    print("  全部入りの空(雲 %d 個 + 太陽)。対照群は「検出を止めた条件」= 真の" % len(CAPS))
    print("  雲マスクをそのまま数える。残る差は幾何だけになる。")
    print()
    tr = truth_fraction(CAPS)
    m_true = coverage(CAPS) > 0
    m_rbr = detect(rbr_sub(CAPS))
    rows = []
    print("  %-26s %12s %12s" % ("数え方", "雲量", "真値との差 %"))
    print("  " + "-" * 54)
    for name, m, how in (("真のマスク x 画素数比", m_true, 0),
                         ("真のマスク x 重みつき", m_true, 1),
                         ("RBR 判定 x 画素数比", m_rbr, 0),
                         ("RBR 判定 x 重みつき", m_rbr, 1)):
        v = estimate(m)[how]
        rows.append([name, "%.5f" % v, "%+.2f" % (100 * (v / tr - 1))])
        print("  %-26s %12.5f %+12.2f" % (name, v, 100 * (v / tr - 1)))
    geo = 100 * (estimate(m_true)[0] / tr - 1)
    det_err = 100 * (estimate(m_rbr)[1] / tr - 1)
    both = 100 * (estimate(m_rbr)[0] / tr - 1)
    print()
    print("  → 真値 %.5f。**幾何だけ**の誤差 %+.2f %%、**検出だけ**の誤差 %+.2f %%。"
          % (tr, geo, det_err))
    print("     両方入ると %+.2f %% —— **足し算ではない**(%.2f + %.2f = %.2f のはず)。"
          % (both, geo, det_err, geo + det_err))
    print("     幾何の偏りは**負**(雲が天頂寄りに多い空だった)、検出の偏りは**正**")
    print("     なので、素朴な数え方では**打ち消して小さく見える**。")
    print("  → ★★重みを掛けると幾何は %.2f %% まで直るが、**検出の誤差は残る**"
          % abs(100 * (estimate(m_true)[1] / tr - 1)))
    print("     (%+.2f %%)。「立体角で数えたから正しい」は成り立たない。" % det_err)
    return tr, geo, det_err, both, rows


# --------------------------------------------------------------------------- #
# 6) 地平線マスク                                                              #
# --------------------------------------------------------------------------- #
def section6_horizon_mask():
    print()
    print("=" * 78)
    print("6) ★地平線マスク —— 建物や木を切るしきい値で雲量がどれだけ動くか")
    print("=" * 78)
    print("  真値もマスクの内側で定義しなおす(分母が変わる)。検出は真のマスク")
    print("  (幾何だけを見るため)と RBR の両方。")
    print()
    m_true = coverage(CAPS) > 0
    m_rbr = detect(rbr_sub(CAPS))
    print("  %8s %10s %10s %10s %10s %10s" %
          ("θ 上限", "真値", "真x画素", "真x重み", "RBRx画素", "RBRx重み"))
    print("  " + "-" * 62)
    rows, err_px, err_wt = [], [], []
    tms = [90.0, 85.0, 80.0, 75.0, 70.0]
    trs = []
    for tm in tms:
        lim = np.deg2rad(tm)
        tr = truth_fraction(CAPS, th_max=lim)
        p1, w1 = estimate(m_true, lim)
        p2, w2 = estimate(m_rbr, lim)
        trs.append(tr)
        err_px.append(100 * (p1 / tr - 1))
        err_wt.append(100 * (w1 / tr - 1))
        rows.append(["%.0f" % tm, "%.4f" % tr, "%.4f" % p1, "%.4f" % w1,
                     "%.4f" % p2, "%.4f" % w2])
        print("  %8.0f %10.4f %10.4f %10.4f %10.4f %10.4f" % (tm, tr, p1, w1, p2, w2))
    print()
    print("  → ★**真値そのものが %.4f → %.4f と %.0f %% 動く**。切り捨てた地平線側は"
          % (trs[0], trs[-1], 100 * (trs[-1] / trs[0] - 1)))
    print("     この空では雲が薄い帯だったので、切ると雲量が上がる。")
    print("  → 画素数比の偏りは %+.2f %% → %+.2f %%、重みつきは %+.2f %% → %+.2f %%。"
          % (err_px[0], err_px[-1], err_wt[0], err_wt[-1]))
    print("     ★重みつきはどのマスクでも ±%.2f %% で動かない。画素数比の偏りは"
          % max(abs(x) for x in err_wt))
    print("     マスクを絞るほど小さくなる —— **いちばん偏っている帯を捨てている**")
    print("     から。「マスクを厳しくしたら一致した」は直った証拠にならない。")
    print("  → ★実務の含意: **マスクの角度を書かずに雲量を報告した数字は比較")
    print("     できない**。同じ空・同じ検出器で %.4f 〜 %.4f を名乗れる。"
          % (min(float(r[1]) for r in rows), max(float(r[1]) for r in rows)))
    figs.save_table("mask_sweep",
                    ["θ 上限 [度]", "真値", "真x画素", "真x重み", "RBRx画素", "RBRx重み"],
                    rows, title="地平線マスクを変えると真値も推定も動く",
                    caption="真値はマスクの内側で定義しなおしている。重みつきだけが真値に張り付く。")
    return trs, err_px, err_wt


# --------------------------------------------------------------------------- #
# 7) 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section7_gaps():
    print()
    print("=" * 78)
    print("7) 道具の穴 —— fullseye に無かったもの / 使いにくかったもの")
    print("=" * 78)
    print("""
  (a) ★★**魚眼(等距離射影)の口が 3 層のどこにも無い**。`distort_points` /
      `undistort_points` は Brown の半径・接線歪み(ピンホールの周りの補正)で、
      **r = f·tanθ を前提にしている**。魚眼は r = f·θ で、θ→90 度で tanθ が
      発散するため**原理的に表せない**。`op_find("fisheye")` も
      `op_find("equidistant")` も 0 件。全天カメラ・広角レンズ・360 度カメラは
      どれもこの射影なので、1 本の関数が欠けているだけで族ごと入れない。

  (b) ★★**立体角の重み map を作る口が無い**。この PoC の主役 `sinθ/θ` は
      3 行で書けるが、**書けることと在ることは別**。射影の種類(等距離 /
      等立体角 / 正射影 / 立体射影)ごとにヤコビアンが違うので、呼び手が
      毎回導出することになる —— 2 節が示したとおり、**間違えると符号ごと
      間違える**(私も向きを逆に予想した)。
      ★同じ「半球上の立体角の重み」は **DEM 族に既に在る**:
      `fs.ledger.dem_sky_view_factor` は `mean(cos²(horizon))` で天空率を
      出す。半球の重み付けを知っている族が在るのに、**画像側から使えない**。

  (c) ★`polar_trans_image`(進化 op、`cv2.warpPolar`)は魚眼を (θ, φ) の
      展開図に開く道具そのものだが、**中心と最大半径が画像サイズから自動で
      決まり、指定できない**(`a`, `b` は未使用)。全天画像の円は普通、
      画像の中心にも、`min(H,W)/2` にも無い。

  (d) **雲量・天空の量を扱う語彙が無い**。RBR(赤/青比)は全天カメラの標準
      指標(Long & DeLuisi 2000)だが、`op_find("rbr")` は 0 件。
      `irradiance_map` は在るのに、その入力になる雲量の側が無い。

  (e) ★**「割合」を返す op が、分母の定義を持たない**。この PoC で 3 回
      出てきた事故はすべて分母(空の画素か、立体角か、マスクの内側か)の
      取り違えだった。`blob_features` の `spacing` のように、**面積の単位を
      値と一緒に運ぶ**仕組みが、球面の量にも要る。
""")
    for name in ("fisheye_project", "fisheye_unproject", "equidistant_project",
                 "solid_angle_map", "sky_view_weights", "red_blue_ratio", "cloud_cover"):
        assert not hasattr(fs, name), "%s が生えた(良い変化。この節を書き換えること)" % name
        assert not hasattr(fs.ledger, name), "%s が台帳に出た(良い変化)" % name
    assert fs.op_find("fisheye") == [] and fs.op_find("equidistant") == [], \
        "魚眼の op が生えた(この節を書き換えること)"
    # (a) Brown 歪みは 90 度を表せない —— 実測で固定する
    k = np.array([[F_PX, 0, CTR], [0, F_PX, CTR], [0, 0, 1.0]])
    th = np.deg2rad(88.0)
    uv = np.array([[CTR + F_PX * np.tan(th), CTR]])          # ピンホールの像高
    assert uv[0, 0] - CTR > 15 * R_PX, uv                    # tan で発散している
    back = np.asarray(fs.distort_points(uv, k, [0.0, 0.0, 0.0, 0.0]))
    assert abs(back[0, 0] - uv[0, 0]) < 1e-6, back           # 歪みゼロなら恒等
    # (b) 半球の重みを知っている族は DEM 側にしかない
    assert hasattr(fs.ledger, "dem_sky_view_factor")
    assert not hasattr(fs, "dem_sky_view_factor"), "ファサードに出た(良い変化)"
    # (c) polar_trans_image は中心も半径も選べない
    hits = [h for h in fs.op_find("polar_trans_image") if h["op"] == "polar_trans_image"]
    assert hits and "未使用" in hits[0]["doc"], hits[:1]


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    print("poc_allsky_cloud_cover — 全天カメラの雲量は投影を無視すると偏る")
    print("(真値 = 天球上の立体角の割合。球冠の閉形式 2π(1-cos α))")
    print()
    worst = section1_check()
    px_r, wt_r, law, dev2 = section2_zero_point()
    lay = section3_layout()
    ts, fp, fp_law, thin_rec, dev4 = section4_rbr_sun()
    tr, geo, det_err, both, rows5 = section5_split_errors()
    trs, err_px, err_wt = section6_horizon_mask()
    section7_gaps()

    rbr, rgb, disc = render(CAPS)
    det = detect(rbr_sub(CAPS)).mean(0)
    figs.save_grid("allsky",
                   [rgb, rbr * disc, det, W_SOLID.mean(0)],
                   ["全天 RGB", "RBR", "RBR>0.60 判定", "立体角の重み"],
                   title="全天カメラ(等距離射影 r = f·θ)", ncols=2,
                   caption="4 枚目が sinθ/θ。天頂で 1、地平線で 0.64 —— 画素の重みはここまで違う。")

    print()
    print("=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  ・積分器の検算              最大差 %.1e" % worst)
    print("  ・同じ雲の画素数比/真値      %.3f(天頂)〜 %.3f(地平線側)= %.2f 倍"
          % (px_r[0], px_r[-1], px_r[-1] / px_r[0]))
    print("  ・重みつき/真値             %.4f 〜 %.4f" % (min(wt_r), max(wt_r)))
    print("  ・同じ真値の 2 つの空        画素 %.4f vs %.4f / 重み %.4f vs %.4f"
          % (lay["天頂寄り"][1], lay["地平線寄り"][1],
             lay["天頂寄り"][2], lay["地平線寄り"][2]))
    print("  ・晴天なのに出る雲量        %.4f(閉形式との差 %.1e)"
          % (fp[ts.index(RBR_T)], dev4))
    print("  ・幾何 %+.2f %% / 検出 %+.2f %% / 両方 %+.2f %%" % (geo, det_err, both))
    print("  ・マスクを絞ると真値が      %.4f → %.4f" % (trs[0], trs[-1]))

    assert worst < 5e-4, worst
    assert px_r[0] < 0.83 < 1.15 < px_r[-1], px_r
    assert dev2 < 0.01, dev2
    assert max(abs(x - 1.0) for x in wt_r) < 0.005, wt_r
    assert abs(lay["天頂寄り"][0] - lay["地平線寄り"][0]) < 1e-3, lay
    assert lay["地平線寄り"][1] > 1.25 * lay["天頂寄り"][1], lay
    assert abs(lay["天頂寄り"][2] - lay["地平線寄り"][2]) < 1e-3, lay
    assert dev4 < 1e-3, dev4
    assert thin_rec[0] > 0.95 and thin_rec[-1] < 0.05, thin_rec
    assert geo < 0 < det_err and abs(both) < abs(det_err), (geo, det_err, both)
    assert max(abs(x) for x in err_wt) < 0.1, err_wt
    assert abs(err_px[0]) > 3 * abs(err_px[-1]), err_px
    assert len(rows5) == 4

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\n経過 %.1f 秒" % (time.time() - t0))
    print("\nPASS")


if __name__ == "__main__":
    main()
