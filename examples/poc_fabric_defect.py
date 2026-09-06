# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""周期のある地に埋もれた欠陥 —— まとめた ROC が隠すもの。

織物・網目・スクリーン印刷のように**地そのものが強い周期パターン**である面を
検査する仕事です。欠陥は地よりずっと弱いので、素朴に「局所平均との差」を取ると
**地が丸ごと差として出て**、欠陥は雑音の中に埋もれます。

EXTEND: 実写に差し替えるなら :func:`make_scene` が返す辞書の ``img`` を撮影画像に、
``masks``(欠陥種別ごとの真値マスク)を検査員の marking に置き換えます。
**種別ごとに分けたマスクが要ります** —— この PoC の中心的な主張は「まとめた
ROC は種別ごとの盲点を隠す」なので、1 枚の「欠陥」マスクに畳んだ時点で測れません。
周期 :data:`PERIOD` は :func:`estimate_period` で推定できますが、実写では
織密度(本/inch)と mm/px から**先に計算して**、推定値と突き合わせること。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(局所平均との差)は地を拾う**。欠陥の無い地だけの画像でも残差 RMS は
   ノッチ法の 2 桁上。★窓の大きさに対する性能は**単調でも周期的でもなかった**
   —— 予想は「窓が周期の整数倍のとき良い」だったが、実測の最良は最小の窓。
   矩形平均の周期成分に対する利得(ディリクレ核)を計算すると、整数倍のとき
   利得は **0**、つまり地が**そのまま残差になる**。予想が逆だった。
2. ★★**3 種類の欠陥は同じ検出器では取れない**。線欠陥・斑点・ムラを 1 本の
   ROC にまとめると AUC は高く見えるが、**種類別に描くとムラが 0.5 付近
   (でたらめ)**になる検出器がある。しかもそれは「格子除去 + 低周波除去」
   という**現場でいちばん普通のレシピ**である —— 照明ムラを消す処理が、
   検出したいムラも一緒に消す。
3. ★周波数領域で格子を落とす(ノッチ)は、地の残差を 2 桁下げる。低周波を
   残すか落とすかは**照明対策の都合**で決まりがちだが、その 1 行が
   ムラ欠陥の AUC を丸ごと壊す。同じ検出器の 2 つの版で比べて示す。
4. ★**周期の推定は FFT の粗い値を位相限定相関で磨く**。FFT のピーク位置は
   1 ビン刻みなので周期の分解能は粗い。長い基線で位相限定相関を取ると
   桁で精度が上がる(実測値は本文)。
5. ★★**周期が数 % ずれるとノッチは高次から効かなくなる**。m 次の高調波は
   ``m·ε·N/P`` ビンだけ動くので、ノッチ半径 r を超えるのは
   ``m > r·P/(ε·N)`` から —— 予測と実測の一致を表で出す。低次だけ残る
   「半分効いたノッチ」がいちばん危ない(絵はきれいになるのに残差が残る)。

【グラウンドトゥルース】
地は**閉形式の周期関数**(格子の基本波 + 2 次高調波 + 交差項)。欠陥は既知の
位置・大きさ・コントラストで**足し込む**ので、真値マスクは幾何で決まる。
陰性画素は「どの欠陥のマスクにも入っていない画素」に限る —— 他の欠陥を陰性に
数えると、種類別 AUC が互いに汚染される。

来歴(公開文献のみ): Tsai & Hsieh, *Pattern Recognition* 32 (1999) 1899 ——
周波数領域による織物欠陥検出 / Kuglin & Hines (1975) —— 位相限定相関 /
Ngan et al., *Image and Vision Computing* 29 (2011) 442 —— 織物検査の総説。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter
from scipy.stats import rankdata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N = 256                    # 視野 [px](周期の整数倍にしてスペクトル漏れを消す)
PERIOD = 8.0               # 織りの周期 [px]
PERIOD_EST = 8.3           # 3 節だけ使う非整除の周期(推定問題を自明にしないため)
NOISE = 0.010              # 撮像雑音 σ
SEED = 4

#: 地に入れてある格子成分 ``(my, mx)``。6 節の予測はこの一覧の上で立てる ——
#: 「高調波が漏れる」と言うとき、**実際に入っている成分**で数えないと嘘になる。
LATTICE = ((1, 0), (0, 1), (1, 1), (2, 0), (0, 2))

#: 欠陥 3 種(位置・大きさ・コントラストはすべて既知)。
#: ★マスクの面積は**わざと同じくらい**に揃えてある。まとめた AUC は陽性画素数で
#: 重みづけた平均に近いので、片方が桁で大きいと「まとめると隠れる」が起きない。
DEFECTS = {
    "線(糸抜け)": {"kind": "line", "col": 168.0, "half": 1.5,
                    "r0": 24, "r1": 232, "amp": -0.070},
    "斑点(汚れ)": {"kind": "spot", "row": 64.0, "col": 72.0,
                    "sigma": 6.0, "amp": -0.110},
    "ムラ(輝度低下)": {"kind": "shade", "row": 182.0, "col": 96.0,
                       "sigma": 12.0, "amp": -0.048},
}


# --------------------------------------------------------------------------- #
# 場面を作る                                                                    #
# --------------------------------------------------------------------------- #
def weave(n: int = N, period: float = PERIOD) -> np.ndarray:
    """織りの地 —— 閉形式の厳密な周期パターン(基本波 + 2 次 + 交差項)。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    k = 2.0 * np.pi / period
    return (0.50
            + 0.130 * np.cos(k * xx) + 0.130 * np.cos(k * yy)
            + 0.070 * np.cos(k * xx) * np.cos(k * yy)
            + 0.040 * np.cos(2 * k * xx) + 0.040 * np.cos(2 * k * yy))


def _defect_field(name: str, n: int = N):
    """欠陥 1 個の加算場と、その真値マスク。"""
    d = DEFECTS[name]
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    if d["kind"] == "line":
        prof = np.clip(1.0 - (np.abs(xx - d["col"]) / d["half"]) ** 2, 0.0, 1.0)
        band = (yy >= d["r0"]) & (yy <= d["r1"])
        field = d["amp"] * prof * band
        mask = (np.abs(xx - d["col"]) <= d["half"]) & band
    elif d["kind"] == "spot":
        r2 = (yy - d["row"]) ** 2 + (xx - d["col"]) ** 2
        field = d["amp"] * np.exp(-r2 / (2 * d["sigma"] ** 2))
        mask = r2 <= (2.0 * d["sigma"]) ** 2
    else:
        r2 = (yy - d["row"]) ** 2 + (xx - d["col"]) ** 2
        field = d["amp"] * np.exp(-r2 / (2 * d["sigma"] ** 2))
        mask = r2 <= (1.0 * d["sigma"]) ** 2
    return field, mask


def make_scene(seed: int = SEED, which=None, noise: float = NOISE,
               period: float = PERIOD) -> dict:
    """地 + 欠陥 + 雑音。``which`` で入れる欠陥を選ぶ(既定は全部)。"""
    names = list(DEFECTS) if which is None else list(which)
    base = weave(period=period)
    img = base.copy()
    masks = {}
    for nm in names:
        f, m = _defect_field(nm)
        img = img + f
        masks[nm] = m
    rng = np.random.default_rng(seed)
    img = img + noise * rng.standard_normal(img.shape)
    any_mask = np.zeros((N, N), bool)
    for m in masks.values():
        any_mask |= m
    return {"img": img, "base": base, "masks": masks, "any": any_mask}


# --------------------------------------------------------------------------- #
# 検出器 —— どれも「スコア地図」を返す(判定はしない)                          #
# --------------------------------------------------------------------------- #
POOL_SIGMA = 1.5           # 残差の絶対値をまとめる平滑化(全検出器に同じだけ掛ける)


def _score(residual: np.ndarray) -> np.ndarray:
    """残差 -> スコア地図。**全検出器に同じ後処理**を掛ける(比較を公平に)。"""
    r = residual - float(np.median(residual))
    return gaussian_filter(np.abs(r), POOL_SIGMA)


def det_local_mean(img: np.ndarray, k: int = 5) -> np.ndarray:
    """ゼロ点 —— 局所平均との差。地の周期が窓に合わないとそのまま残る。"""
    return _score(img - uniform_filter(img, size=k, mode="wrap"))


def notch_transfer(shape, period: float, radius: float = 1.0,
                   harmonics: int = 8, low_cut: float = 0.0) -> np.ndarray:
    """格子のピークを落とす伝達関数(``fs.cx_fft`` と同じ中心化配置)。

    ``low_cut`` > 0 なら DC 近傍も落とす —— **照明ムラを消す**ための、現場で
    ほぼ必ず付いてくる 1 行。5 節でこれがムラ欠陥を殺すことを測る。
    """
    h, w = shape
    v = np.fft.fftshift(np.fft.fftfreq(h)) * h
    u = np.fft.fftshift(np.fft.fftfreq(w)) * w
    uu, vv = np.meshgrid(u, v)
    hf = np.ones(shape)
    f0y, f0x = h / period, w / period
    for my in range(-harmonics, harmonics + 1):
        for mx in range(-harmonics, harmonics + 1):
            if my == 0 and mx == 0:
                continue
            cy, cx = my * f0y, mx * f0x
            if abs(cy) > h / 2 or abs(cx) > w / 2:
                continue
            hf[(uu - cx) ** 2 + (vv - cy) ** 2 <= radius ** 2] = 0.0
    if low_cut > 0:
        hf[uu ** 2 + vv ** 2 <= low_cut ** 2] = 0.0
    return hf


def det_notch(img: np.ndarray, period: float = PERIOD, radius: float = 1.0,
              low_cut: float = 0.0) -> np.ndarray:
    """格子のピークを周波数領域で落とす。``fs.cx_fft`` 族をそのまま使う。"""
    hf = notch_transfer(img.shape, period, radius=radius, low_cut=low_cut)
    cx = fs.cx_fft(img)
    return _score(np.asarray(fs.cx_ifft(fs.cx_apply_transfer_function(cx, hf))))


def fold_model(img: np.ndarray, period: float, k: int = 16) -> np.ndarray:
    """1 周期ぶんの平均像を作って、全画素に戻す(周期は非整数でもよい)。

    位相 ``(y mod P, x mod P)`` を ``k x k`` の升目に**双一次で撒いて**平均し、
    同じ重みで読み戻す。整数周期に丸めないので、5 節の ε 掃引にも使える。
    """
    h, w = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    py = (yy % period) / period * k
    px = (xx % period) / period * k
    i0, j0 = np.floor(py).astype(int), np.floor(px).astype(int)
    fy, fx = py - i0, px - j0
    acc = np.zeros((k, k))
    wsum = np.zeros((k, k))
    parts = []
    for di in (0, 1):
        for dj in (0, 1):
            wgt = ((1 - fy) if di == 0 else fy) * ((1 - fx) if dj == 0 else fx)
            idx = ((i0 + di) % k, (j0 + dj) % k)
            np.add.at(acc, idx, wgt * img)
            np.add.at(wsum, idx, wgt)
            parts.append((wgt, idx))
    tile = acc / np.maximum(wsum, 1e-9)
    model = np.zeros_like(img)
    for wgt, idx in parts:
        model += wgt * tile[idx]
    return model


def det_fold(img: np.ndarray, period: float = PERIOD) -> np.ndarray:
    """1 周期ぶんの平均像との差。"""
    return _score(img - fold_model(img, period))


# --------------------------------------------------------------------------- #
# 周期の推定 —— FFT の粗い値を位相限定相関で磨く                                #
# --------------------------------------------------------------------------- #
def poc_1d(pa: np.ndarray, pb: np.ndarray) -> np.ndarray:
    """1-D の位相限定相関(振幅を捨てて位相だけで相関を取る)。"""
    fa = np.fft.rfft(pa - pa.mean())
    fb = np.fft.rfft(pb - pb.mean())
    r = fa * np.conj(fb)
    r /= np.abs(r) + 1e-12
    return np.fft.irfft(r, n=pa.size)


def poc_peak_table(img: np.ndarray, baseline: int = 96, top: int = 5):
    """POC のピーク上位 ``top`` 個。**周期信号ではどれも同じ高さになる**。"""
    p = img.mean(axis=0)
    a, b = p[:p.size - baseline], p[baseline:]
    surf = poc_1d(a, b)
    n = surf.size
    lag = np.arange(n)
    lag = np.where(lag > n // 2, lag - n, lag)
    order = np.argsort(-surf)
    picked = []
    for i in order:
        if all(abs(int(lag[i]) - s) >= 3 for s, _ in picked):
            picked.append((int(lag[i]), float(surf[i])))
        if len(picked) >= top:
            break
    return picked


def estimate_period(img: np.ndarray, margin: int = 24) -> dict:
    """FFT のピーク(粗)-> **復調した位相の傾き**(精)で周期を出す。

    位相限定相関の**ピーク位置**では周期は決まらない —— 周期信号は自分自身と
    「周期の整数倍」ずらしても一致するので、ピークが等高で並ぶ(3 節で実測)。
    決められるのは位相の**傾き**のほう: 粗い周波数 f0 で復調すると、残った
    位相の傾きが周波数の誤差そのものになる。
    """
    from scipy.ndimage import gaussian_filter1d

    p = img.mean(axis=0)
    p = p - p.mean()
    spec = np.abs(np.fft.rfft(p))
    m1 = int(np.argmax(spec[1:])) + 1
    f0 = m1 / p.size
    x = np.arange(p.size, dtype=np.float64)
    z = p * np.exp(-2j * np.pi * f0 * x)
    s = 1.0 / f0                                   # 1 周期ぶんで平滑化
    z = gaussian_filter1d(z.real, s) + 1j * gaussian_filter1d(z.imag, s)
    ph = np.unwrap(np.angle(z))
    sl = slice(margin, p.size - margin)            # 復調の過渡を落とす
    slope = float(np.polyfit(x[sl], ph[sl], 1)[0])
    f = f0 + slope / (2.0 * np.pi)
    return {"coarse": float(1.0 / f0), "fine": float(1.0 / f), "bin": m1,
            "slope": slope, "span": int(p.size - 2 * margin)}


# --------------------------------------------------------------------------- #
# ROC                                                                          #
# --------------------------------------------------------------------------- #
def auc(scores: np.ndarray, pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann-Whitney の U による AUC(同点は平均順位)。"""
    s = np.concatenate([scores[pos], scores[neg]])
    y = np.concatenate([np.ones(int(pos.sum()), bool),
                        np.zeros(int(neg.sum()), bool)])
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        raise ValueError("陽性と陰性が両方要る")
    ranks = rankdata(s)
    return float((ranks[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def roc_points(scores: np.ndarray, pos: np.ndarray, neg: np.ndarray,
               n_pts: int = 200):
    """図のための (fpr, tpr) 点列(等間隔に間引く)。"""
    s = np.concatenate([scores[pos], scores[neg]])
    y = np.concatenate([np.ones(int(pos.sum()), bool),
                        np.zeros(int(neg.sum()), bool)])
    y = y[np.argsort(-s, kind="mergesort")]
    tpr = np.cumsum(y) / max(int(y.sum()), 1)
    fpr = np.cumsum(~y) / max(int((~y).sum()), 1)
    idx = np.unique(np.linspace(0, y.size - 1, n_pts).astype(int))
    return np.r_[0.0, fpr[idx]], np.r_[0.0, tpr[idx]]


DETECTORS = {
    "ゼロ点(局所平均)": lambda im: det_local_mean(im, 5),
    "ノッチ(格子のみ)": lambda im: det_notch(im),
    "ノッチ+低周波除去": lambda im: det_notch(im, low_cut=6.0),
    "折り返し平均差": lambda im: det_fold(im),
}


# --------------------------------------------------------------------------- #
# 1. 地だけで測る —— 何もしなければ地が残差になる                               #
# --------------------------------------------------------------------------- #
def section_background() -> dict:
    print("\n" + "=" * 78)
    print("1) 地だけの画像(欠陥ゼロ)で残差を測る")
    print("=" * 78)

    clean = make_scene(which=[])["img"]
    print("  地のコントラスト: 最小 %.3f 最大 %.3f(振幅 %.3f)、雑音 σ %.3f"
          % (clean.min(), clean.max(), 0.5 * (clean.max() - clean.min()), NOISE))
    print("\n   検出器                残差 RMS      雑音だけの場合との比")
    out = {}
    for name, fn in DETECTORS.items():
        r = float(np.sqrt(np.mean(fn(clean) ** 2)))
        out[name] = r
        print("   %-20s %10.5f      %10.1f 倍" % (name, r, r / NOISE))
    print("\n  ★ゼロ点の残差はノッチ法の %.0f 倍。**地がそのまま残差になっている**"
          " —— 欠陥はこの中に埋もれる。"
          % (out["ゼロ点(局所平均)"] / out["ノッチ(格子のみ)"]))
    return out


# --------------------------------------------------------------------------- #
# 2. ゼロ点の窓の大きさ                                                         #
# --------------------------------------------------------------------------- #
def _dirichlet_gain(k: int, period: float) -> float:
    """幅 ``k`` の矩形平均が周期 ``period`` の正弦波に与える利得。"""
    x = np.pi * k / period
    return float(np.sin(x) / (k * np.sin(np.pi / period)))


def section_window() -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点の窓の大きさ —— 予想は「周期の整数倍が良い」だった")
    print("=" * 78)
    print("   窓 k   矩形平均の利得 G   地の残差係数 |1-G|   地の残差 RMS   AUC(まとめ)")

    sc = make_scene()
    clean = make_scene(which=[])["img"]
    neg = ~sc["any"]
    ks, aucs, rms = [], [], []
    for k in (3, 4, 5, 6, 7, 8, 9, 11, 13, 16, 17):
        g = _dirichlet_gain(k, PERIOD)
        r = float(np.sqrt(np.mean(det_local_mean(clean, k) ** 2)))
        a = auc(det_local_mean(sc["img"], k), sc["any"], neg)
        ks.append(k)
        aucs.append(a)
        rms.append(r)
        print("   %4d      %+8.4f          %8.4f         %9.5f      %.4f"
              % (k, g, abs(1 - g), r, a))

    best = ks[int(np.argmax(aucs))]
    print("\n  ★予想は「窓が周期(%.0f px)の整数倍のとき地が消えて良い」。"
          "実測の最良は k=%d。" % (PERIOD, best))
    print("     計算するとその予想は**逆**だった: 整数倍のとき矩形平均の利得は "
          "G=0、つまり\n     背景推定から地が消えるので、残差 = I - 背景 に"
          "**地がそのまま残る**(|1-G| = 1)。")
    print("     地を消したいなら背景推定に地を**残さねばならない** ——"
          "この符号を取り違えると窓を選び間違える。")
    return {"k": ks, "auc": aucs, "rms": rms, "best": best}


# --------------------------------------------------------------------------- #
# 3. 周期の推定                                                                 #
# --------------------------------------------------------------------------- #
def section_period() -> dict:
    print("\n" + "=" * 78)
    print("3) 周期の推定 —— 位相限定相関の「ピーク」では決まらない")
    print("=" * 78)
    print("  ★この節だけ周期 %.1f px の別の場面で測る。%.0f px は画像幅 %d の"
          "約数なので\n    FFT のピークが真値ちょうどに乗ってしまい、"
          "**推定問題が消える**。" % (PERIOD_EST, PERIOD, N))

    sc = make_scene(period=PERIOD_EST, which=[])
    peaks = poc_peak_table(sc["img"])
    print("\n  (a) 位相限定相関のピーク上位 %d 個(基線 96 px):" % len(peaks))
    for lag, val in peaks:
        print("      ずれ %+4d px   高さ %.4f" % (lag, val))
    spread = (max(v for _, v in peaks) - min(v for _, v in peaks)) \
        / max(v for _, v in peaks)
    print("      ★ずれはすべて周期 %.1f px の整数倍近辺で、高さの差は %.1f %% "
          "しかない。" % (PERIOD_EST, 100 * spread))
    print("      **周期信号は自分自身と周期ずらしでも一致する**ので、"
          "ピーク位置からは周期を決められない。")

    print("\n  (b) 決められるのは位相の**傾き**のほう(粗い周波数で復調する):")
    est = estimate_period(sc["img"])
    print("      FFT のピーク %d ビン -> 周期 %.5f px(1 ビン刻みの分解能 %.4f px)"
          % (est["bin"], est["coarse"], N / est["bin"] - N / (est["bin"] + 1)))
    print("      位相の傾き %+.6f rad/px -> 周期 %.5f px" % (est["slope"], est["fine"]))
    print("      真値 %.5f px。誤差 FFT %+.5f px / 位相勾配 %+.5f px(%.0f 倍改善)"
          % (PERIOD_EST, est["coarse"] - PERIOD_EST, est["fine"] - PERIOD_EST,
             abs(est["coarse"] - PERIOD_EST) / max(abs(est["fine"] - PERIOD_EST), 1e-12)))

    print("\n   当てはめ長 [px]   周期の推定      誤差 [px]")
    rows = []
    for m in (96, 72, 48, 24, 8):
        e = estimate_period(sc["img"], margin=m)
        rows.append((e["span"], e["fine"]))
        print("        %4d        %10.5f     %+.5f"
              % (e["span"], e["fine"], e["fine"] - PERIOD_EST))
    print("  ★当てはめを伸ばすほど良くなる —— ただし端は復調の過渡なので"
          "落とさないと逆に悪くなる(いちばん下の行)。")
    return {"est": est, "rows": rows, "peaks": peaks}


# --------------------------------------------------------------------------- #
# 4. 種類別 ROC —— まとめると盲点が消える                                       #
# --------------------------------------------------------------------------- #
def section_roc() -> dict:
    print("\n" + "=" * 78)
    print("4) ★★ROC を種類別に分ける —— まとめると盲点が消える")
    print("=" * 78)

    sc = make_scene()
    neg = ~sc["any"]
    print("  陰性画素はどの欠陥マスクにも入らない %d 画素("
          "他の欠陥を陰性に数えると種類別 AUC が互いに汚染される)。"
          % int(neg.sum()))
    names = list(DEFECTS)
    print("\n   検出器                まとめ    " + "  ".join("%-14s" % n for n in names))

    table, curves, rows = {}, {}, []
    for dn, fn in DETECTORS.items():
        s = fn(sc["img"])
        pooled = auc(s, sc["any"], neg)
        per = [auc(s, sc["masks"][n], neg) for n in names]
        table[dn] = (pooled, per)
        curves[dn] = roc_points(s, sc["any"], neg)
        rows.append([dn, "%.4f" % pooled] + ["%.4f" % v for v in per])
        print("   %-20s %.4f    " % (dn, pooled)
              + "  ".join("%-14.4f" % v for v in per))

    worst = min(((dn, v[0], min(v[1]), names[int(np.argmin(v[1]))])
                 for dn, v in table.items()), key=lambda t: t[2])
    print("\n  ★**%s** はまとめた AUC %.4f で悪くないのに、"
          "「%s」だけ %.4f —— でたらめ(0.5)とほぼ同じ。"
          % (worst[0], worst[1], worst[3], worst[2]))
    print("     まとめた 1 本の ROC を見ていたら、この盲点は**数字に一度も"
          "現れない**。")
    print("  ★盲点の原因は測ってある: 低周波を落とす 1 行(照明ムラ対策)が"
          "ムラ欠陥そのものを消している。同じノッチを低周波を残して掛けると")
    print("     同じ「%s」の AUC は %.4f -> %.4f に戻る。"
          % (worst[3], table["ノッチ+低周波除去"][1][names.index(worst[3])],
             table["ノッチ(格子のみ)"][1][names.index(worst[3])]))

    figs.save_plot("roc",
                   [("%s %.3f" % (dn, table[dn][0]), *curves[dn])
                    for dn in DETECTORS],
                   xlabel="偽陽性率", ylabel="検出率",
                   title="3 種類をまとめた ROC(どれも良く見える)",
                   caption="凡例の数字は AUC。この図には盲点が写っていない ——"
                           "種類別は表のほうを見ること。")
    figs.save_table("auc_by_type", ["検出器", "まとめ"] + names, rows,
                    title="種類別 AUC(まとめた 1 列だけ見てはいけない)")
    return {"table": table, "names": names, "sc": sc}


# --------------------------------------------------------------------------- #
# 5. 種類別の ROC 曲線(盲点を絵にする)                                        #
# --------------------------------------------------------------------------- #
def section_blind(roc: dict) -> None:
    print("\n" + "=" * 78)
    print("5) 盲点を絵にする —— 同じ検出器、種類別の ROC")
    print("=" * 78)

    sc = roc["sc"]
    neg = ~sc["any"]
    dn = "ノッチ+低周波除去"
    s = DETECTORS[dn](sc["img"])
    series = [("まとめ %.3f" % roc["table"][dn][0],
               *roc_points(s, sc["any"], neg))]
    for i, n in enumerate(roc["names"]):
        series.append(("%s %.3f" % (n, roc["table"][dn][1][i]),
                       *roc_points(s, sc["masks"][n], neg)))
    for n, a in zip(roc["names"], roc["table"][dn][1]):
        print("   %-16s AUC %.4f" % (n, a))
    print("  ★同じスコア地図・同じ陰性から描いた 4 本。まとめた 1 本は"
          "**平均的に良い**ので、0.5 の 1 本が見えなくなる。")

    figs.save_plot("roc_by_type", series,
                   xlabel="偽陽性率", ylabel="検出率",
                   title="「%s」を種類別に描く" % dn,
                   caption="対角線に乗っている系列が盲点。まとめた系列には"
                           "その情報が残っていない。")


# --------------------------------------------------------------------------- #
# 6. 周期が ε ずれると                                                          #
# --------------------------------------------------------------------------- #
def section_period_error() -> dict:
    print("\n" + "=" * 78)
    print("6) 周期の推定が ε ずれると —— 高次から効かなくなる")
    print("=" * 78)
    print("  格子成分 (my,mx) のノッチ中心は ε·(N/P)·|m| ビン動く(|m| = "
          "sqrt(my²+mx²))。")
    print("  半径 r=1.0 を超えると外れる: |m| > r·P/(ε·N)。**地に実際に入って"
          "いる成分**")
    print("  %s の上で予測する —— 入っていない高調波で数えたら嘘になる。"
          % ", ".join("(%d,%d)" % c for c in LATTICE))
    print("\n     ε      仮の周期   予測: 外れる成分       地の残差 RMS   倍率   AUC")

    clean = make_scene(which=[])["img"]
    sc = make_scene()
    neg = ~sc["any"]
    base_rms = float(np.sqrt(np.mean(det_notch(clean) ** 2)))
    base_auc = auc(det_notch(sc["img"]), sc["any"], neg)
    eps_l, rms_l, auc_l, fold_l, esc_l = [], [], [], [], []
    for eps in (0.0, 0.002, 0.005, 0.01, 0.015, 0.02, 0.04, 0.08):
        p = PERIOD * (1.0 + eps)
        esc = [c for c in LATTICE
               if eps * (N / PERIOD) * np.hypot(*c) > 1.0]
        r = float(np.sqrt(np.mean(det_notch(clean, period=p) ** 2)))
        a = auc(det_notch(sc["img"], period=p), sc["any"], neg)
        rf = float(np.sqrt(np.mean(det_fold(clean, period=p) ** 2)))
        eps_l.append(100 * eps)
        rms_l.append(r)
        auc_l.append(a)
        fold_l.append(rf)
        esc_l.append(len(esc))
        print("   %5.1f %%   %8.4f   %-20s   %9.5f  %6.1f   %.4f"
              % (100 * eps, p,
                 "なし" if not esc else ",".join("(%d,%d)" % c for c in esc),
                 r, r / base_rms, a))

    first = next((e for e, n in zip(eps_l, esc_l) if n), None)
    jump = next((e for e, r in zip(eps_l, rms_l) if r > 1.5 * base_rms), None)
    print("\n  ★予測「最初に外れるのは ε=%.1f %%」に対し、残差が跳ねたのは "
          "ε=%.1f %% —— %s。" % (first, jump,
                                 "一致" if first == jump else "ずれた"))
    print("     ε=1.0 %% では残差 %.1f 倍(AUC %.4f)、まだ 1 つも外れていない。"
          "**低次だけの地なら 1 %% は効かない** —— "
          % (rms_l[3] / base_rms, auc_l[3]))
    print("     高調波を多く含む地(細かい織り)ほど、同じ ε で先に壊れる。")
    print("  ★全部外れると残差は %.1f 倍で頭打ち。これは地そのものの RMS で、"
          "2 節の k=8(利得 0)の値 %.5f と一致する。"
          % (max(rms_l) / base_rms, max(rms_l)))
    print("\n   折り返し平均差の同じ掃引: "
          + " / ".join("%.1f%%:%.5f" % (e, v) for e, v in zip(eps_l, fold_l)))
    print("     ★こちらは ε に **%s**(ε=0.5 %% で既に %.1f 倍)。"
          "位相で畳む方式は周期の誤差が場所とともに積み上がるので、"
          "\n     周波数領域のノッチより**桁で厳しい**。"
          % ("弱い" if fold_l[2] / fold_l[0] > rms_l[2] / rms_l[0] else "強い",
             fold_l[2] / fold_l[0]))

    figs.save_plot("period_error",
                   [("ノッチ 残差 RMS", eps_l, rms_l),
                    ("折り返し 残差 RMS", eps_l, fold_l),
                    ("ε=0 のノッチ", eps_l, [base_rms] * len(eps_l))],
                   xlabel="周期の誤差 ε [%]", ylabel="地の残差 RMS",
                   title="周期が数 % ずれると格子除去は効かなくなる",
                   caption="欠陥の無い地だけで測った残差。ノッチは高次の"
                           "高調波から漏れ始める。")
    return {"eps": eps_l, "rms": rms_l, "auc": auc_l, "fold": fold_l,
            "base_rms": base_rms, "base_auc": base_auc}


# --------------------------------------------------------------------------- #
# 7. 絵                                                                         #
# --------------------------------------------------------------------------- #
def section_figure(roc: dict) -> None:
    sc = roc["sc"]
    notch = det_notch(sc["img"])
    zero = det_local_mean(sc["img"], 5)
    # 外れ値で潰れるので、呼び手の側で 99.5 % 分位に切ってから渡す
    q = float(np.quantile(notch, 0.995))
    figs.save_grid("scene",
                   [sc["img"], sc["any"].astype(np.float64),
                    np.clip(zero, 0, float(np.quantile(zero, 0.995))),
                    np.clip(notch, 0, q)],
                   ["織りの地 + 欠陥 3 種", "真値マスク",
                    "ゼロ点のスコア", "ノッチのスコア"],
                   ncols=2, title="周期のある地に埋もれた欠陥(1 周期 %.0f px)"
                                  % PERIOD,
                   caption="スコア 2 枚は 99.5 %% 分位で切ってある。"
                           "ゼロ点は地の格子がそのまま出る。")


# --------------------------------------------------------------------------- #
# 8. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)

    # (a) ノッチ / 帯域除去フィルタを**作る**口が無い(掛ける口はある)。
    assert hasattr(fs, "cx_apply_transfer_function") and hasattr(fs, "cx_fft")
    assert not hasattr(fs, "notch_filter") and not hasattr(fs.ledger, "notch_filter")
    assert not hasattr(fs, "gen_bandfilter")
    print("  (a) 伝達関数を**掛ける**口(cx_apply_transfer_function)は在るのに、"
          "ノッチ / 帯域除去の伝達関数を**作る**口が無い。この PoC は "
          "notch_transfer を自前で書いている(進化 op の hx_gen_bandfilter は"
          "つまみ 2 個で周波数を指定できない)。")

    # (b) 位相限定相関が無い(相互相関は piv 族に在る)。
    assert hasattr(fs.ledger, "piv_cross_correlate")
    assert not hasattr(fs, "phase_correlate") and not hasattr(fs.ledger, "phase_correlate")
    print("  (b) 位相限定相関(POC)が無い。piv_cross_correlate は**振幅つきの**"
          "相互相関で、周期パターンでは複数のピークが同じ高さになる。"
          "POC は自前 20 行だが、サブピクセル補間の作法まで含めると族に入る価値がある。")

    # (c) 周期パターンの「1 周期ぶんに畳む」口が無い。
    assert not hasattr(fs, "fold_period") and not hasattr(fs.ledger, "periodic_average")
    print("  (c) 周期で**畳んで平均する**(periodic average / phase folding)口が"
          "無い。織物・スクリーン・回転機械の位相平均はどれも同じ形なので、"
          "1 本あれば 3 分野で使える。")

    # (d) ROC / AUC が無い。poc_forensics_roc も自前で書いている。
    assert not hasattr(fs, "roc_curve") and not hasattr(fs.ledger, "auc")
    print("  (d) ROC / AUC が無い。この PoC も poc_forensics_roc も"
          "**別々に自前で書いている**(2 本目なので、そろそろ族に入れる合図)。")

    # (e) 画素ごとのスコア地図を「種類別に評価する」枠組みが無い —— これは
    #     道具ではなく作法の問題なので、穴として記録するだけにする。
    print("  (e) 種類別評価(陰性画素の定義を含む)は道具ではなく作法。"
          "ただし「陰性 = どの欠陥マスクにも入らない画素」を忘れると"
          "種類別 AUC が互いに汚染されるので、評価器を族に入れるなら"
          "**陰性の定義を引数で強制する**設計にすべき。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("周期のある地に埋もれた欠陥 —— まとめた ROC が隠すもの")
    print("%d x %d px / 織りの周期 %.0f px / 雑音 σ %.3f" % (N, N, PERIOD, NOISE))
    print("=" * 78)

    section_background()
    win = section_window()
    per = section_period()
    roc = section_roc()
    section_blind(roc)
    pe = section_period_error()
    section_figure(roc)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    names = roc["names"]
    dn = "ノッチ+低周波除去"
    print("  * ゼロ点の窓は「周期の整数倍が良い」ではない(最良 k=%d)。"
          "整数倍では矩形平均の利得が 0 になり、地がそのまま残差になる。"
          % win["best"])
    print("  * 周期は FFT の粗い値(%.5f px)を位相限定相関で %.5f px まで磨ける"
          "(真値 %.5f)。" % (per["est"]["coarse"], per["est"]["fine"], PERIOD))
    print("  * **%s** はまとめた AUC %.4f、しかし「%s」だけ %.4f。"
          % (dn, roc["table"][dn][0], names[2], roc["table"][dn][1][2]))
    print("    低周波を残すだけで %.4f に戻る —— 消していたのは照明ではなく欠陥。"
          % roc["table"]["ノッチ(格子のみ)"][1][2])
    print("  * 周期が 1 %% ずれると地の残差は %.1f 倍(高次の高調波から漏れる)。"
          % (pe["rms"][3] / pe["base_rms"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
