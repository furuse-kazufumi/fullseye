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

1. ★★**まとめた ROC は盲点を隠す**。「格子除去 + 低周波除去」——現場でいちばん
   普通のレシピ——のまとめた AUC は **0.8113** で、実務なら合格に見える。
   種類別に割ると 線 1.0000 / 斑点 0.9753 / **ムラ 0.4746(でたらめ以下)**。
   まとめた 1 本の ROC 曲線には、この盲点が一度も現れない。
2. ★★**消していたのは照明ではなく欠陥だった**。低周波を落とす 1 行を外すだけ
   でムラの AUC は 0.4746 → 0.9998 に戻る。照明ムラ対策と、検出したいムラは
   **同じ周波数帯に居る**ので、片方だけを消すことはできない。
3. **ゼロ点(局所平均との差)は地を拾う**。地だけの画像で残差 RMS 0.0665 ——
   ノッチ法の 8.3 倍、雑音の 6.7 倍。★予想は「窓が周期の整数倍なら地が消える」
   だったが**符号が逆**で、整数倍では矩形平均の利得が 0 になり
   「背景推定から地が消える」= 残差に地がそのまま残る。実測の残差は
   ディリクレ核 |1-G| と相関 0.994。★そして窓を 3〜17 px で振っても
   AUC は 0.509〜0.541 —— **窓を選んでもゼロ点は救われない**。
4. ★**周期の推定: 位相限定相関のピークでは周期は決まらない**。POC が返すのは
   「基線 ÷ 周期の余り」で、ピークは周期おきに並ぶ(実測の間隔 平均 8.5 px、
   真値 8.3 px)。周期に直すには何周期ぶんか k が要り、**k を 1 つ間違えると
   推定が 0.333 px 飛ぶ**(自身の誤差の 13 倍)。基線を伸ばすとおおむね
   良くなるが単調ではない。★k の要らない**位相の傾き**なら誤差 +0.00008 px
   (FFT の粗い値の 532 倍の精度)。
5. ★★**周期が 1 % ずれても、この地では何も起きなかった**。予想は「1 % で
   効かなくなる」。実際は格子成分 (my,mx) の中心が ε·(N/P)·|m| ビン動くので、
   ノッチ半径 1.0 を超えるのは |m| > P/(ε·N) —— 地に入っている最大の
   |m| = 2 では **ε = 2 % から**。予測と実測(残差 1.0 倍 → 4.1 倍の跳ね)が
   一致した。**高調波を多く含む細かい織りほど同じ ε で先に壊れる**。
   全部外れると残差は 14 倍で頭打ちになり、それは地そのものの RMS
   (2 節の利得 0 の行)と一致する。
6. ★**折り返し平均(位相で畳む)は周期の誤差に桁で弱い**。ε=0.5 % で残差は
   既に 4.5 倍(ノッチは 1.0 倍)。位相のずれが視野の端まで積み上がるから。
   周期が既知でないなら、ノッチのほうが安全側。
7. ★★**本物の欠陥では、採点の仕方で数が変わる**(9b 節)。公開の織物の実写 RAW-FABRID
   (CC BY 4.0、ラインスキャン 4 px/mm)に付いた欠陥マスク 360 個で採点する。配布物のマスクは
   欠陥より太い(骨格上の幅の中央値 16 px)。太いマスクの画素で格子のみ 0.557(折り返し 0.525、
   格子+低周波除去 0.503)だが、マスクの芯(骨格 ±2 px)を陽性・6 px 外を陰性にすると
   芯で格子のみ 0.657、折り返し 0.614 —— 同じ検出器・同じ欠陥が 0.56 にも 0.66 にもなる。
   どちらの採点でも、合成の「格子を除けば欠陥はほぼ全部取れる(AUC 1.00)」には遠い。
   ★ゼロ点(局所平均との差)は 0.5 を下回るが当て推量ではなく**符号が逆**(本物の欠陥は周りより
   織り目の凹凸が少ない)で、符号を反転すれば 0.717(芯)。★この反転は結果(0.5 未満)を見てから
   決めた事後の選択なので、反転していない他の 3 手法と並べた順位(「4 手法で最良」)は主張しない
   (同じ規則「0.5 未満なら反転」を他の 3 手法に当てても、どれも 0.5 を超えるので値は変わらない)。
   ★芯の採点は陰性からマスクのすぐ外 6 px(いちばん紛らわしい地)を除くので、太いマスクより甘くなる
   向きがある。芯の値を「本当の AUC」とは読まない —— 言えるのは「採点の規則で 0.1 動く」まで。
   ★低周波除去を足すと芯で平均 -0.100(画像単位の区間 -0.118〜-0.082、360 個中 290 個で下がる)、
   太いマスクでは -0.054 —— 向きは合成と同じだが、大きさは合成の 0.9998 → 0.4746 とは桁が違う。
   注記は 1 種類だけで、本物の中にムラが在るかは分からない。★「低周波除去がムラを消す」を
   0.96 → 0.50 の大きさで示せたのは、実写の地に**描き足した**ムラだけ(9a 節、機構の説明。
   描き足したムラで格子のみ 0.96、低周波除去つき 0.50。振幅の倍率は目で決めた)。
   ★前の版は太いマスクの画素 AUC だけで「どの手法も当て推量に近い」と書き、さらに前の版は 7 個
   だけを見て「低周波除去で悪くならない」と読める数を出していた。

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
from scipy.ndimage import binary_dilation, distance_transform_edt, gaussian_filter, uniform_filter
from scipy.stats import rankdata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import realdata                                                  # noqa: E402

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
                    "sigma": 6.0, "amp": -0.110, "rmask": 1.80},
    "ムラ(輝度低下)": {"kind": "shade", "row": 186.0, "col": 92.0,
                       "sigma": 20.0, "amp": -0.045, "rmask": 0.65},
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
    else:
        # 斑点もムラも同じガウス。違うのは σ(空間スケール)と、マスク半径。
        # ★マスク半径は σ の倍率で個別に決めてある —— **面積を揃えるため**。
        #   面積が桁で違うと「まとめた AUC は面積の大きいほうの AUC」に
        #   なってしまい、この PoC が測りたい「まとめると隠れる」が
        #   「面積が大きいほうが勝つ」という別の話にすり替わる。
        r2 = (yy - d["row"]) ** 2 + (xx - d["col"]) ** 2
        field = d["amp"] * np.exp(-r2 / (2 * d["sigma"] ** 2))
        mask = r2 <= (d["rmask"] * d["sigma"]) ** 2
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


def poc_peak_table(img: np.ndarray, baseline: int = 96, top: int = 3):
    """POC のピーク上位 ``top`` 個。**周期信号ではどれも同じ高さになる**。"""
    p = img.mean(axis=0)
    a, b = p[:p.size - baseline], p[baseline:]
    surf = poc_1d(a, b)
    n = surf.size
    lag = np.arange(n)
    lag = np.where(lag > n // 2, lag - n, lag)
    loc = np.nonzero((surf > np.roll(surf, 1)) & (surf > np.roll(surf, -1)))[0]
    order = loc[np.argsort(-surf[loc])]
    picked = []
    for i in order:
        if all(abs(int(lag[i]) - s) >= 6 for s, _ in picked):
            picked.append((int(lag[i]), float(surf[i])))
        if len(picked) >= top:
            break
    return sorted(picked)


def period_from_poc(img: np.ndarray, baseline: int, coarse: float) -> dict:
    """POC のピーク位置(サブピクセル)から周期を出す。

    ``a(x) = p(x)``、``b(x) = p(x+B)`` の POC のピーク ``L`` は
    ``B - L = k·P`` を満たす。**周期そのものではなく余りが出る**ので、
    ``k`` を粗い推定から決める必要がある —— そこを 1 つ間違えると
    推定は不連続に飛ぶ(下でその量も出す)。
    """
    p = img.mean(axis=0)
    a, b = p[:p.size - baseline], p[baseline:]
    surf = poc_1d(a, b)
    n = surf.size
    i = int(np.argmax(surf))
    c, lo, hi = surf[i], surf[(i - 1) % n], surf[(i + 1) % n]
    den = lo - 2 * c + hi
    sub = 0.5 * (lo - hi) / den if abs(den) > 1e-12 else 0.0
    lag = i + float(np.clip(sub, -1.0, 1.0))
    if lag > n / 2:
        lag -= n
    k = int(round((baseline - lag) / coarse))
    return {"lag": lag, "k": k, "period": (baseline - lag) / k if k else np.nan,
            "jump": abs((baseline - lag) / k - (baseline - lag) / (k + 1))
            if k else np.nan}


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
    g_abs = [abs(1 - _dirichlet_gain(k, PERIOD)) for k in ks]
    corr = float(np.corrcoef(g_abs, rms)[0, 1])
    print("\n  ★予想は「窓が周期(%.0f px)の整数倍のとき地が消えて良い」だったが、"
          "**符号が逆**だった。" % PERIOD)
    print("     整数倍のとき矩形平均の利得は G=0 —— 背景推定のほうから地が"
          "消えるので、\n     残差 = I - 背景 に**地がそのまま残る**(|1-G| = 1)。"
          "地を消したいなら\n     背景に地を**残さねばならない**。")
    print("     実測の残差 RMS は |1-G| とよく合う(相関 %.3f)。" % corr)
    print("  ★そして、どの窓でも AUC は %.4f 〜 %.4f。**窓を選んでもゼロ点は"
          "救われない**" % (min(aucs), max(aucs)))
    print("     (最良は k=%d だが差は %.4f で、地の残差 %.1f 倍の違いに対して"
          "無意味)。" % (best, max(aucs) - min(aucs), max(rms) / min(rms)))
    print("     効く/効かないは窓の大きさではなく、**背景モデルが周期を"
          "表現できるか**で決まる。")
    return {"k": ks, "auc": aucs, "rms": rms, "best": best, "corr": corr}


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
    print("\n  (a) 位相限定相関のピーク(基線 96 px、ずれの順):")
    for lag, val in peaks:
        print("      ずれ %+4d px   高さ %.4f" % (lag, val))
    gaps = np.diff([lag for lag, _ in peaks])
    print("      ★ピークの間隔 %s px(平均 %.1f)—— 真の周期 %.1f px の格子に"
          "乗っている。" % (", ".join(str(int(g)) for g in gaps),
                            float(np.mean(gaps)), PERIOD_EST))
    print("      POC が返すのは**基線を周期で割った余り**であって周期そのもの"
          "ではない。周期に直すには何周期ぶんか(k)を別に知る必要がある。")

    est = estimate_period(sc["img"])
    print("\n  (b) 3 通りで周期を出して比べる(真値 %.5f px):" % PERIOD_EST)
    print("      FFT のピーク  %d ビン        -> %.5f px  (誤差 %+.5f)"
          % (est["bin"], est["coarse"], est["coarse"] - PERIOD_EST))
    print("      位相の傾き   %+.6f rad/px  -> %.5f px  (誤差 %+.5f)"
          % (est["slope"], est["fine"], est["fine"] - PERIOD_EST))
    print("\n      POC(サブピクセル補間つき)を基線を変えて:")
    print("       基線 [px]   ずれ      k    周期       誤差      k を 1 つ誤ると")
    pc = None
    for b in (48, 96, 152, 200):
        e = period_from_poc(sc["img"], b, est["coarse"])
        pc = e if b == 200 else pc
        print("        %4d    %+7.3f  %3d  %8.5f  %+9.5f      %.3f px"
              % (b, e["lag"], e["k"], e["period"],
                 e["period"] - PERIOD_EST, e["jump"]))
    print("      ★POC は基線を伸ばすとおおむね良くなる(余りの誤差が k で"
          "割られる)が、**単調ではない**")
    print("         —— 152 px で悪化する。余りの測り方そのものが窓の重なりで"
          "変わるから。最良でも誤差 %+.5f px で、位相勾配の %.0f 倍。"
          % (pc["period"] - PERIOD_EST,
             abs(pc["period"] - PERIOD_EST) / max(abs(est["fine"] - PERIOD_EST), 1e-12)))
    print("      さらに k を 1 つ取り違えると %.3f px 飛ぶ —— **誤差の %.0f 倍**。"
          "粗い推定が要る手法の宿命。"
          % (pc["jump"], pc["jump"] / max(abs(pc["period"] - PERIOD_EST), 1e-9)))
    print("      位相勾配は k を要らない(粗い周波数で復調して残りを測るだけ)ので"
          "\n      その飛びが原理的に起きない。FFT の %.0f 倍の精度。"
          % (abs(est["coarse"] - PERIOD_EST) / max(abs(est["fine"] - PERIOD_EST), 1e-12)))

    print("\n   当てはめ長 [px]   位相勾配の推定   誤差 [px]")
    rows = []
    for m in (96, 72, 48, 24, 8):
        e = estimate_period(sc["img"], margin=m)
        rows.append((e["span"], e["fine"]))
        print("        %4d        %10.5f     %+.5f"
              % (e["span"], e["fine"], e["fine"] - PERIOD_EST))
    err = [abs(v - PERIOD_EST) for _, v in rows]
    print("  ★当てはめ長は %d〜%d px で誤差 %.5f〜%.5f px。**単調ではない** ——"
          % (rows[0][0], rows[-1][0], min(err), max(err)))
    print("     長く取るほど傾きの当てはめは安定するが、端は復調の過渡なので"
          "混ぜると悪くなる。両方が効いて最良は中ほど(%d px)に出た。"
          % rows[int(np.argmin(err))][0])
    return {"est": est, "rows": rows, "peaks": peaks, "poc": pc}


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

    table, rows = {}, []
    for dn, fn in DETECTORS.items():
        s = fn(sc["img"])
        pooled = auc(s, sc["any"], neg)
        per = [auc(s, sc["masks"][n], neg) for n in names]
        table[dn] = (pooled, per)
        rows.append([dn, "%.4f" % pooled] + ["%.4f" % v for v in per])
        print("   %-20s %.4f    " % (dn, pooled)
              + "  ".join("%-14.4f" % v for v in per))

    areas = [int(sc["masks"][n].sum()) for n in names]
    print("\n  陽性画素数(意図的に揃えてある): "
          + " / ".join("%s %d" % (n, a) for n, a in zip(names, areas)))
    zp = table["ゼロ点(局所平均)"]
    print("\n  ★ゼロ点はまとめても種類別も %.2f 〜 %.2f —— 全面的に効いていない。"
          % (min([zp[0]] + zp[1]), max([zp[0]] + zp[1])))
    dn, i_sh = "ノッチ+低周波除去", names.index("ムラ(輝度低下)")
    print("  ★★問題は %s のほう。まとめた AUC %.4f は**実務なら合格に見える**"
          "のに、" % (dn, table[dn][0]))
    print("     「%s」だけ %.4f。まとめた 1 本の ROC には、この盲点が"
          "**一度も現れない**。" % (names[i_sh], table[dn][1][i_sh]))
    print("  ★原因は測ってある: 低周波を落とす 1 行(照明ムラ対策)が"
          "ムラ欠陥そのものを消している。")
    print("     同じノッチを低周波を残して掛けると %.4f -> %.4f に戻る —— "
          "消していたのは照明ではなく欠陥。"
          % (table[dn][1][i_sh], table["ノッチ(格子のみ)"][1][i_sh]))

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
                   caption="スコア 2 枚は 99.5 % 分位で切ってある。"
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
# 9. 実写の地(RAW-FABRID)で同じ測定をやり直す                                  #
# --------------------------------------------------------------------------- #
#: 実データの置き場の環境変数(``<root>/raw_fabrid/`` を探す)。
REAL_DATA_ENV = "FULLSEYE_POC_REAL_DATA"
REAL_DATASET = "mendeley:db6g85xsyg/RAW-FABRID"
#: 図と印字に添える帰属表記(配布元 Mendeley Data のライセンス欄は "CC BY 4.0")。
REAL_CREDIT = ("RAW-FABRID — R. Pérez-Llorens, T. Albero-Albero, J. Silvestre-Blanes, "
               "Mendeley Data db6g85xsyg v1 (doi:10.17632/db6g85xsyg.1), CC BY 4.0")
#: 1 枚の実写から切り出す 256 px 角の位置(縦・横の割合)。決定的に選ぶ。
REAL_CROPS = ((0.30, 0.30), (0.70, 0.65))
#: 撮像の分解能(データの Readme: "a spatial resolution of 4 pixels per millimeter")。
REAL_PX_PER_MM = 4.0
#: 欠陥の振幅の倍率 α の掃引。合成では「振幅 / 検出器が見る残差 σ(= 撮像雑音)」が
#: 線 7・斑点 11・ムラ 4.5。実写では同じ比を α 倍して足す(α = 1 が合成と同じ見え方)。
REAL_ALPHAS = (0.1, 0.2, 0.35, 0.5, 1.0)
#: 本文と図で使う α(ムラの振幅が残差 σ の 1.6 倍 —— 目で見て「うっすら」の強さ)。
REAL_ALPHA = 0.35
#: 照明のゆるい傾きを抜く平滑の σ [px](周期の推定の前にだけ使う)。
REAL_DETREND = 16.0

#: 実データで出た数値(2026-11-08、Python 3.11、``section_real_fabric`` の stdout から転記)。
#: データの無い CI ではこれを印字し、:func:`check_recorded` が中身(鍵・有限・docstring との一致)を
#: 検査する。データありでは実測と完全一致を求める(変えたら記録と docstring を一緒に直す)。
RECORDED_REAL: dict = {
    "n_grounds": 14, "alpha": 0.35, "keep_ratio": 0.969,
    "mura_notch": 0.9645, "mura_lowcut": 0.4998, "mura_lowcut_max_over_alpha": 0.5063,
    "pooled_notch": 0.9653, "pooled_lowcut": 0.7623,
    "defects_n": 360, "defects_images": 201,
    "defects_auc": [0.3479, 0.5575, 0.5031, 0.5255],
    "auc_ci": [[0.3305, 0.5377, 0.4835, 0.5075], [0.3659, 0.5778, 0.5247, 0.544]],
    "lowcut_minus_notch": -0.0544, "lowcut_minus_notch_ci": [-0.0667, -0.0433],
    "n_lowcut_worse": 255, "n_drop_gt_0p2": 33, "n_drop_gt_0p2_dark": 33,
    "n_dark": 118, "n_bright": 242,
    "dark_auc": [0.2697, 0.6152, 0.4611, 0.5622],
    "bright_auc": [0.3861, 0.5294, 0.5236, 0.5075],
    "mask_width_px": 16.0,
    "core_auc": [0.2826, 0.6567, 0.5572, 0.6141],
    "core_auc_ci": [[0.2554, 0.6256, 0.5262, 0.5828], [0.3121, 0.6904, 0.5906, 0.6482]],
    "core_lowcut_minus_notch": -0.0995, "core_lowcut_minus_notch_ci": [-0.118, -0.0818],
    "core_n_lowcut_worse": 290, "zero_flipped_core": 0.7174,
}


def real_data_root() -> Path:
    """実データ一式の repo 外の置き場(``FULLSEYE_POC_REAL_DATA`` で上書き)。

    開発の作業木が ``<root>/projects/<checkout>`` にあれば ``<root>/data/fullseye_poc_real``、
    それ以外はユーザーのキャッシュ。手元の絶対パスをソースに書かないための分岐。
    """
    import os

    configured = os.environ.get(REAL_DATA_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    root = Path(__file__).resolve().parents[1]
    if root.parent.name.lower() == "projects":
        return root.parent.parent / "data" / "fullseye_poc_real"
    return Path.home() / ".cache" / "fullseye" / "poc_real"


def _fabrid_dir() -> Path | None:
    """展開済みの RAW-FABRID(``images/`` と メタデータ CSV がある所)。無ければ None。"""
    base = real_data_root() / "raw_fabrid" / "extracted" / "RAW_FABRID"
    if (base / "images").is_dir() and (base / "RAW_FABRID_HighRes_Metadata.csv").is_file():
        return base
    return None


def _fabrid_pick(base: Path) -> tuple[list, list]:
    """ロール(織物の種類)ごとに、欠陥なしの最初の 1 枚と欠陥ありの最初の 1 枚を返す。"""
    import csv

    with open(base / "RAW_FABRID_HighRes_Metadata.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    good, bad = {}, {}
    for r in rows:
        tgt = good if r["has_defect"] == "False" else bad
        tgt.setdefault(r["roll_id"], r["filename"])
    return sorted(good.items()), sorted(bad.items())


def _gray(path: Path) -> np.ndarray:
    from PIL import Image

    with Image.open(path) as im:
        return np.asarray(im.convert("L"), np.float64) / 255.0


def notch_transfer_xy(shape, period_y: float, period_x: float, radius: float = 1.0,
                      harmonics: int = 8, low_cut: float = 0.0) -> np.ndarray:
    """:func:`notch_transfer` の縦横で周期が違う版(実写の織りは縦糸と横糸で密度が違う)。"""
    h, w = shape
    v = np.fft.fftshift(np.fft.fftfreq(h)) * h
    u = np.fft.fftshift(np.fft.fftfreq(w)) * w
    uu, vv = np.meshgrid(u, v)
    hf = np.ones(shape)
    f0y, f0x = h / period_y, w / period_x
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


def _notch_residual(img: np.ndarray, period_y: float, period_x: float,
                    low_cut: float = 0.0) -> np.ndarray:
    hf = notch_transfer_xy(img.shape, period_y, period_x, low_cut=low_cut)
    return np.real(np.asarray(fs.cx_ifft(fs.cx_apply_transfer_function(fs.cx_fft(img), hf))))


def _real_detectors(period_y: float, period_x: float) -> dict:
    """DETECTORS と同じ 4 つを、実写から推定した周期で組む(折り返しは横の周期)。"""
    return {
        "ゼロ点(局所平均)": lambda im: det_local_mean(im, 5),
        "ノッチ(格子のみ)": lambda im: _score(_notch_residual(im, period_y, period_x)),
        "ノッチ+低周波除去": lambda im: _score(_notch_residual(im, period_y, period_x, low_cut=6.0)),
        "折り返し平均差": lambda im: det_fold(im, period_x),
    }


def _outline(mask: np.ndarray) -> np.ndarray:
    """マスクの**外側**に 2 px 離して描く輪(欠陥そのものを線で隠さないため)。"""
    from scipy.ndimage import binary_dilation

    return binary_dilation(mask, iterations=4) & ~binary_dilation(mask, iterations=2)


def _gray_view(img: np.ndarray) -> np.ndarray:
    """実写を 0.5〜99.5 % 分位で [0,1] に伸ばした灰色の RGB(擬似色は使わない)。"""
    lo, hi = np.quantile(img, [0.005, 0.995])
    base = np.clip((img - lo) / max(hi - lo, 1e-9), 0, 1)
    return np.repeat(base[..., None], 3, axis=2)


def _real_figure(g: np.ndarray, img: np.ndarray, masks: dict, s_notch: np.ndarray,
                 s_low: np.ndarray, a_notch: float, a_low: float, roll: str) -> None:
    """機構の図: 実写の地 + 描き足した欠陥の輪郭 / 格子のみのスコア / 格子+低周波除去のスコア。

    ★欠陥は**描き足し**(合成の 1〜8 節と同じ形)。本物の欠陥での結果は :func:`_real_defect_figures`。
    """
    if not figs.enabled():
        return
    colors = {"線(糸抜け)": (0.15, 0.55, 1.0), "斑点(汚れ)": (1.0, 0.75, 0.1),
              "ムラ(輝度低下)": (1.0, 0.25, 0.25)}
    rgb = _gray_view(img)
    for nm, m in masks.items():
        rgb[_outline(m)] = colors[nm]
    q = float(np.quantile(s_notch, 0.995))
    # 糸の 1 本が 3 px なので、画素を最近傍で 2 倍に広げて織り目を見せる(補間で糸をぼかさない)
    up = lambda v: np.repeat(np.repeat(v, 2, axis=0), 2, axis=1)            # noqa: E731
    figs.save_grid(
        "real_fabric",
        [up(rgb), up(np.clip(s_notch, 0, q) / q), up(np.clip(s_low, 0, q) / q)],
        ["実写の生機 + **描き足した**欠陥(青=線 黄=斑点 赤=ムラ)",
         "格子のみ: 描き足したムラ AUC %.2f" % a_notch,
         "格子+低周波除去: 描き足したムラ AUC %.2f" % a_low],
        ncols=3, gray=[False, True, True], vrange=[None, (0.0, 1.0), (0.0, 1.0)],
        title="機構の説明: 実写の地(RAW-FABRID %s)に描き足したムラは、低周波除去の 1 行で消える" % roll,
        caption=("欠陥 3 種は合成と同じ位置・形で**描き足した**もの(本物の欠陥ではない)。振幅の倍率"
                 " α = %.2f は目で見て「うっすら」に決めた値。スコア 2 枚は同じ 99.5 %% 分位で切った灰色。"
                 "描き足したムラの AUC は格子のみ %.2f、低周波除去を足すと %.2f。本物の欠陥 %d 個での"
                 "結果は別の図。%s" % (REAL_ALPHA, a_notch, a_low, RECORDED_REAL["defects_n"], REAL_CREDIT)))


# --------------------------------------------------------------------------- #
# 9b. 本物の欠陥(データ付属のマスク)で 4 つの検出器を採点する                 #
# --------------------------------------------------------------------------- #
#: 欠陥 1 個ごとに、注記の外接矩形の中心で 256 px 角を切り出して採点する。
REAL_DEFECT_BOOT = 2000          # 画像単位のブートストラップの回数(同じ画像の欠陥はまとめて引く)
#: ★配布物のマスクは欠陥より太い(骨格上の幅の中央値は実測で 16 px 前後)。太いマスクの画素 AUC は
#: 欠陥の周りの正常な織り目を陽性に数えるので 0.5 側へ寄る。そこで**芯**でも採点する:
#: 陽性 = マスクの骨格を REAL_CORE_PX だけ太らせた帯(マスクの内側に限る)、
#: 陰性 = マスクを REAL_GUARD_PX 太らせた外。どちらの採点も並べて出す(どちらか一方に寄せない)。
REAL_CORE_PX = 2
REAL_GUARD_PX = 6
REAL_DET_NAMES = ("ゼロ点(局所平均)", "ノッチ(格子のみ)", "ノッチ+低周波除去", "折り返し平均差")


def _real_defects(base: Path) -> list[dict]:
    """COCO の注記 1 個 = 1 行。切り出し・マスク・4 検出器の AUC・明暗・形を返す。

    陽性 = 切り出しの中でマスクが立つ画素(同じ画像の別の欠陥も含む)、陰性 = それ以外。
    周期は画像ごとに照明の傾きを抜いてから推す(1〜8 節と同じ :func:`estimate_period`)。
    """
    import json

    coco = json.loads((base / "RAW_FABRID_HighRes_COCO.json").read_text(encoding="utf-8"))
    names = {i["id"]: i["file_name"] for i in coco["images"]}
    cache: dict = {}
    rows = []
    for a in coco["annotations"]:
        fn = names[a["image_id"]]
        mp = base / "masks" / fn
        if not mp.is_file():
            continue
        if fn not in cache:
            cache.clear()                                    # 注記は画像の順に並ぶ。1 枚だけ持つ
            img = _gray(base / "images" / fn)
            flat = img - gaussian_filter(img, REAL_DETREND)
            cache[fn] = (img, _gray(mp) > 0.5, estimate_period(flat.T)["fine"],
                         estimate_period(flat)["fine"])
        img, m, per_y, per_x = cache[fn]
        x, y, w, h = a["bbox"]
        r0 = int(np.clip(y + h / 2 - N / 2, 0, img.shape[0] - N))
        c0 = int(np.clip(x + w / 2 - N / 2, 0, img.shape[1] - N))
        crop, mc = img[r0:r0 + N, c0:c0 + N], m[r0:r0 + N, c0:c0 + N]
        if mc.sum() < 20 or (~mc).sum() < 20:
            continue
        scores = [fn_(crop) for fn_ in _real_detectors(per_y, per_x).values()]
        aucs = [auc(sc, mc, ~mc) for sc in scores]
        skel = np.asarray(fs.apply(mc.astype(np.float64), "thinning")) > 0.5
        core = binary_dilation(skel, iterations=REAL_CORE_PX) & mc
        neg_g = ~binary_dilation(mc, iterations=REAL_GUARD_PX)
        if not core.any():                                   # 骨格が空の小さいマスクは全体を芯とみなす
            core = mc
        aucs_core = [auc(sc, core, neg_g) for sc in scores]
        width = 2.0 * float(distance_transform_edt(mc)[skel].mean()) if skel.any() else float("nan")
        rows.append({"file": fn, "roll": fn.split("_")[0], "area": float(a["area"]),
                     "aspect": max(w, h) / max(1.0, min(w, h)), "auc": aucs, "auc_core": aucs_core,
                     "width": width,
                     "contrast": float((np.mean(crop[mc]) - np.median(crop[~mc])) / np.std(crop[~mc])),
                     "r0": r0, "c0": c0, "py": per_y, "px": per_x})
    return rows


def _cluster_boot(rows: list[dict], stat, n: int = REAL_DEFECT_BOOT, seed: int = 0):
    """画像単位のブートストラップ(同じ画像の欠陥は独立でないのでまとめて引く)の 95 % 区間。"""
    files = sorted({r["file"] for r in rows})
    by = {f: [r for r in rows if r["file"] == f] for f in files}
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        pick = rng.choice(len(files), len(files))
        vals.append(stat([r for i in pick for r in by[files[i]]]))
    return np.percentile(np.asarray(vals), [2.5, 97.5], axis=0)


def _real_defect_figures(base: Path, rows: list[dict], res: dict) -> None:
    """本物の欠陥の図 4 枚(代表・入力の一覧・結果の表・限界)。名前は story GIF 用に real_ を頭に付ける。"""
    if not figs.enabled():
        return
    a = np.array([r["auc"] for r in rows])
    med = np.median(a[:, 1:3], axis=0)
    i_med = int(np.argmin(np.abs(a[:, 1] - med[0]) + np.abs(a[:, 2] - med[1])))
    dark = [i for i, r in enumerate(rows) if r["contrast"] < 0]
    i_dark = max(dark, key=lambda i: rows[i]["area"]) if dark else i_med
    orange = (1.0, 0.55, 0.0)

    def panels(i):
        r = rows[i]
        img = _gray(base / "images" / r["file"])
        m = _gray(base / "masks" / r["file"]) > 0.5
        crop = img[r["r0"]:r["r0"] + N, r["c0"]:r["c0"] + N]
        mc = m[r["r0"]:r["r0"] + N, r["c0"]:r["c0"] + N]
        rgb = _gray_view(crop)
        rgb[_outline(mc)] = orange
        det = _real_detectors(r["py"], r["px"])
        s1, s2 = det[REAL_DET_NAMES[1]](crop), det[REAL_DET_NAMES[2]](crop)
        q = float(np.quantile(s1, 0.995))
        return rgb, np.clip(s1, 0, q) / q, np.clip(s2, 0, q) / q, crop, mc

    p1, p2 = panels(i_med), panels(i_dark)
    r1, r2 = rows[i_med], rows[i_dark]
    figs.save_grid(
        "real_defects",
        [p1[0], p1[1], p1[2], p2[0], p2[1], p2[2]],
        ["本物の欠陥(%s、AUC が中央値に近い 1 個)" % r1["roll"],
         "格子のみ: 太いマスク %.2f / 芯 %.2f" % (r1["auc"][1], r1["auc_core"][1]),
         "格子+低周波除去: 太いマスク %.2f / 芯 %.2f" % (r1["auc"][2], r1["auc_core"][2]),
         "本物の暗い欠陥(%s、暗い %d 個で面積最大)" % (r2["roll"], len(dark)),
         "格子のみ: 太いマスク %.2f / 芯 %.2f" % (r2["auc"][1], r2["auc_core"][1]),
         "格子+低周波除去: 太いマスク %.2f / 芯 %.2f" % (r2["auc"][2], r2["auc_core"][2])],
        ncols=3, gray=[False, True, True, False, True, True],
        vrange=[None, (0.0, 1.0), (0.0, 1.0), None, (0.0, 1.0), (0.0, 1.0)],
        title="本物の織物の欠陥 %d 個: 格子のみの AUC は採点の仕方で %.2f にも %.2f にもなる(太いマスク / 芯)"
              % (res["defects_n"], res["defects_auc"][1], res["core_auc"][1]),
        caption=("データ付属の欠陥マスク(橙の輪郭)で画素ごとに採点。マスクは欠陥より太い(骨格上の幅の"
                 "中央値 %.0f px)ので、太いマスクの画素 AUC は 0.5 側へ寄る。芯 = 骨格 ±%d px を陽性、マスクを %d px"
                 "太らせた外を陰性にした採点。上段は 2 手法の AUC が全体の中央値に"
                 "近い 1 個、下段は暗い欠陥のうち面積が最大の 1 個(選び方は結果を見ずに決めた規則)。"
                 "スコアは同じ 99.5 %% 分位で切った灰色。%s"
                 % (res["mask_width_px"], REAL_CORE_PX, REAL_GUARD_PX, REAL_CREDIT)))
    # 入力の一覧(scene): ロールごとに最初の欠陥 1 個 + 上の暗い 1 個
    firsts = []
    for roll in sorted({r["roll"] for r in rows}):
        firsts.append(next(i for i, r in enumerate(rows) if r["roll"] == roll))
    if i_dark not in firsts:
        firsts.append(i_dark)
    tiles, caps = [], []
    for i in firsts[:8]:
        rgb = panels(i)[0]
        tiles.append(rgb)
        caps.append("%s 格子 %.2f / +低周波 %.2f" % (rows[i]["roll"], rows[i]["auc"][1], rows[i]["auc"][2]))
    figs.save_grid("real_input_defects", tiles, caps, ncols=4,
                   title="入力: 本物の欠陥(データ付属のマスクを橙の輪郭で)、ロールごとに最初の 1 個",
                   caption="ラインスキャン 4 px/mm の生機。各 256 px = 64 mm 角。%s" % REAL_CREDIT)
    # 結果の表(result)
    hdr = ["検出器", "太いマスク 全 %d 個" % res["defects_n"], "芯 全体", "芯の 95 % 区間",
           "太いマスク 暗い %d" % res["n_dark"], "太いマスク 明るい %d" % res["n_bright"]]
    body = []
    for k, dn in enumerate(REAL_DET_NAMES):
        body.append([dn, "%.3f" % res["defects_auc"][k], "%.3f" % res["core_auc"][k],
                     "%.3f〜%.3f" % (res["core_auc_ci"][0][k], res["core_auc_ci"][1][k]),
                     "%.3f" % res["dark_auc"][k], "%.3f" % res["bright_auc"][k]])
    figs.save_table("real_result_auc_table", hdr, body,
                    title="本物の欠陥での平均 AUC: 太いマスクと芯(ゼロ点の 0.5 未満は符号が逆)",
                    caption="区間は画像単位のブートストラップ %d 回。%s" % (REAL_DEFECT_BOOT, REAL_CREDIT))
    # 限界(limit): 欠陥ごとの「低周波除去を足した差」を並べる
    d = np.sort(a[:, 2] - a[:, 1])
    ac_ = np.array([r["auc_core"] for r in rows])
    dc = np.sort(ac_[:, 2] - ac_[:, 1])
    x = np.arange(d.size, dtype=np.float64)
    figs.save_plot("real_limit_lowcut_diff",
                   [("差(太いマスク)", x, d), ("差(芯)", x, dc), ("差なし", x, np.zeros_like(x))],
                   xlabel="欠陥(差の小さい順)", ylabel="AUC の差",
                   title="低周波除去を足した AUC の差: 芯で平均 %+.3f、太いマスクで %+.3f"
                         % (res["core_lowcut_minus_notch"], res["lowcut_minus_notch"]),
                   caption="本物の欠陥 1 個ごとの差を小さい順に。区間は芯 %+.3f〜%+.3f、太いマスク %+.3f〜%+.3f"
                           "(画像単位のブートストラップ)。"
                           % (tuple(res["core_lowcut_minus_notch_ci"]) + tuple(res["lowcut_minus_notch_ci"])))


def section_real_defects(base: Path) -> dict:
    """本物の欠陥(マスク付き 204 枚・注記 361 個)で、4 検出器を外の真値で採点する。"""
    print("\n  ---- 9b) 本物の欠陥(データ付属のマスク)で採点する ----")
    t0 = time.perf_counter()
    rows = _real_defects(base)
    n_img = len({r["file"] for r in rows})
    print("  注記は 1 種類だけ(category 'fabric_defect')—— 糸抜け・汚れ・ムラの区別は配布物に無い。")
    print("  欠陥 %d 個(画像 %d 枚・ロール %d 本)。注記の外接矩形の中心で 256 px 角を切り出す。"
          % (len(rows), n_img, len({r["roll"] for r in rows})))
    a = np.array([r["auc"] for r in rows])
    con = np.array([r["contrast"] for r in rows])
    asp = np.array([r["aspect"] for r in rows])
    big = np.array([r["area"] for r in rows]) >= 5000
    dark, bright = con < 0, con >= 0
    ci = _cluster_boot(rows, lambda rr: np.mean([r["auc"] for r in rr], axis=0))
    diff = a[:, 2] - a[:, 1]
    dci = _cluster_boot(rows, lambda rr: float(np.mean([r["auc"][2] - r["auc"][1] for r in rr])))
    print("\n   検出器                全体 [95 %% 区間]        暗い %3d   明るい %3d   線状 %3d   大きい %3d"
          % (dark.sum(), bright.sum(), (asp >= 4).sum(), big.sum()))
    for k, dn in enumerate(REAL_DET_NAMES):
        print("   %-20s %.3f [%.3f〜%.3f]   %.3f      %.3f        %.3f      %.3f"
              % (dn, a[:, k].mean(), ci[0][k], ci[1][k], a[dark, k].mean(), a[bright, k].mean(),
                 a[asp >= 4, k].mean(), a[big, k].mean()))
    print("  (線状 = 外接矩形の縦横比 4 以上、大きい = 面積 5000 px = 3.1 cm² 以上。形だけの代わりの分類)")
    print("\n  ★★太いマスクの画素で採点すると、最良の格子のみでも %.3f。合成の「格子除去で欠陥が"
          "ほぼ全部取れる(AUC 1.00)」は本物の欠陥では成り立たない(芯の採点は下)。" % a[:, 1].mean())
    print("  ★低周波除去を足すと平均 %+.3f(区間 %+.3f〜%+.3f)、%d 個中 %d 個で下がる。"
          % (diff.mean(), dci[0], dci[1], len(rows), int((diff < 0).sum())))
    print("     向きは合成と同じ(低周波除去は欠陥の一部を消す)だが、大きさは合成の 0.96 → 0.50 とは"
          "桁が違う。暗い欠陥では %.3f → %.3f。" % (a[dark, 1].mean(), a[dark, 2].mean()))
    drop = diff < -0.2
    print("  ★大きく下がる(-0.2 より)のは %d 個で、%d 個とも周りより暗い欠陥(全体では暗いのは %.0f %%)。"
          % (int(drop.sum()), int((drop & dark).sum()), 100 * dark.mean()))
    print("     その %d 個の平均 AUC は格子のみ %.3f → +低周波 %.3f。低周波除去が消すのは暗い欠陥の側。"
          % (int(drop.sum()), a[drop, 1].mean(), a[drop, 2].mean()))
    ac = np.array([r["auc_core"] for r in rows])
    wid = float(np.nanmedian([r["width"] for r in rows]))
    cci = _cluster_boot(rows, lambda rr: np.mean([r["auc_core"] for r in rr], axis=0))
    dcore = ac[:, 2] - ac[:, 1]
    dcci = _cluster_boot(rows, lambda rr: float(np.mean([r["auc_core"][2] - r["auc_core"][1] for r in rr])))
    print("\n  ★★採点の仕方で数が変わる。配布物のマスクは欠陥より太い(骨格上の幅の中央値 %.1f px、"
          "糸 1 本の傷にも帯)。" % wid)
    print("     太いマスクの画素 AUC は欠陥の周りの正常な織り目を陽性に数える。芯(骨格 ±%d px)を陽性、"
          "マスクを %d px 太らせた外を陰性にすると:" % (REAL_CORE_PX, REAL_GUARD_PX))
    print("   検出器                太いマスク   芯 [95 % 区間]")
    for k, dn in enumerate(REAL_DET_NAMES):
        print("   %-20s %.3f        %.3f [%.3f〜%.3f]" % (dn, a[:, k].mean(), ac[:, k].mean(), cci[0][k], cci[1][k]))
    print("  ★格子のみは太いマスクで %.3f、芯で %.3f —— 同じ検出器・同じ欠陥が、採点の仕方で 0.56 にも"
          " 0.66 にもなる。" % (a[:, 1].mean(), ac[:, 1].mean()))
    print("  ★低周波除去の害は芯の採点では平均 %+.3f(区間 %+.3f〜%+.3f)、%d 個中 %d 個で下がる。"
          % (round(float(dcore.mean()), 4), dcci[0], dcci[1], len(rows), int((dcore < 0).sum())))
    print("  ★ゼロ点(局所平均との差)は 太いマスク %.3f / 芯 %.3f で 0.5 を**下回る** —— 当て推量ではなく"
          % (a[:, 0].mean(), ac[:, 0].mean()))
    print("     **符号が逆**: 本物の欠陥の画素は周りより織り目の凹凸が少ない(糸抜け・汚れで地の模様が")
    print("     消える)。スコアの符号を反転すれば 1 − AUC = %.3f(芯)。" % (1.0 - ac[:, 0].mean()))
    print("     ★反転は結果(0.5 未満)を見てから決めた事後の選択。反転しない他の 3 手法(芯 %s)と並べた"
          % " / ".join("%.3f" % v for v in ac[:, 1:].mean(axis=0)))
    print("     順位は主張しない(同じ規則「0.5 未満なら反転」を当てても他の 3 手法はどれも 0.5 超で変わらない)。")
    print("  ★芯の採点は陰性からマスクのすぐ外 %d px(いちばん紛らわしい地)を除くので、太いマスクより甘くなる"
          "向きがある。芯の値を本当の AUC とは読まない。" % REAL_GUARD_PX)
    print("  ★7 枚(ロールごとに最初の 1 枚)だけで見た前の版は 格子のみ 0.575 / +低周波 0.582 で、"
          "低周波除去で悪くならないように見えた。全 %d 個では逆。" % len(rows))
    res = {"defects_n": len(rows), "defects_images": n_img,
           "defects_auc": [round(float(v), 4) for v in a.mean(axis=0)],
           "auc_ci": [[round(float(v), 4) for v in ci[0]], [round(float(v), 4) for v in ci[1]]],
           "lowcut_minus_notch": round(float(diff.mean()), 4),
           "lowcut_minus_notch_ci": [round(float(dci[0]), 4), round(float(dci[1]), 4)],
           "n_lowcut_worse": int((diff < 0).sum()),
           "n_drop_gt_0p2": int(drop.sum()), "n_drop_gt_0p2_dark": int((drop & dark).sum()),
           "n_dark": int(dark.sum()), "n_bright": int(bright.sum()),
           "dark_auc": [round(float(v), 4) for v in a[dark].mean(axis=0)],
           "bright_auc": [round(float(v), 4) for v in a[bright].mean(axis=0)],
           "mask_width_px": round(wid, 1),
           "core_auc": [round(float(v), 4) for v in ac.mean(axis=0)],
           "core_auc_ci": [[round(float(v), 4) for v in cci[0]], [round(float(v), 4) for v in cci[1]]],
           "core_lowcut_minus_notch": round(float(dcore.mean()), 4),
           "core_lowcut_minus_notch_ci": [round(float(dcci[0]), 4), round(float(dcci[1]), 4)],
           "core_n_lowcut_worse": int((dcore < 0).sum()),
           "zero_flipped_core": round(float(1.0 - ac[:, 0].mean()), 4)}
    _real_defect_figures(base, rows, res)
    print("  所要 %.1f 秒" % (time.perf_counter() - t0))
    return res


#: RECORDED_REAL に必ず在る鍵(CI 経路の門が中身を検査する)。
RECORDED_KEYS = ("n_grounds", "alpha", "keep_ratio", "mura_notch", "mura_lowcut",
                 "mura_lowcut_max_over_alpha", "pooled_notch", "pooled_lowcut",
                 "defects_n", "defects_images", "defects_auc", "auc_ci", "lowcut_minus_notch",
                 "lowcut_minus_notch_ci", "n_lowcut_worse", "n_drop_gt_0p2", "n_drop_gt_0p2_dark",
                 "n_dark", "n_bright", "dark_auc",
                 "bright_auc", "mask_width_px", "core_auc", "core_auc_ci", "core_lowcut_minus_notch",
                 "core_lowcut_minus_notch_ci", "core_n_lowcut_worse", "zero_flipped_core")


def _flat_numbers(v) -> list[float]:
    if isinstance(v, (list, tuple)):
        return [x for e in v for x in _flat_numbers(e)]
    return [float(v)]


def check_recorded(measured: dict | None) -> None:
    """記録値の門。CI(データ無し)では中身、データありでは実測との一致を見る。

    * 中身: 鍵が全部在り、数が全部有限。見出しの数(本物の欠陥の個数・格子のみ / +低周波の AUC・
      差・下がった個数、描き足したムラの 2 つの AUC)が module docstring に**同じ書式で**載っている
      (記録値と本文の数が食い違えば鳴る)。
    * データあり: 実測を同じ丸めにして記録値と完全一致(実データは決定的に処理している)。
    """
    missing = [k for k in RECORDED_KEYS if k not in RECORDED_REAL]
    assert not missing, "RECORDED_REAL に鍵が無い: %s" % missing
    nums = [x for k in RECORDED_KEYS for x in _flat_numbers(RECORDED_REAL[k])]
    assert all(np.isfinite(nums)), "RECORDED_REAL に有限でない数"
    doc = __doc__ or ""
    r = RECORDED_REAL
    # ★短い数字の部分一致(「360」など)は別の文脈の数でも通るので、文脈つきの句で照合する。
    heads = ["欠陥マスク %d 個" % r["defects_n"],
             "太いマスクの画素で格子のみ %.3f" % r["defects_auc"][1],
             "芯で格子のみ %.3f" % r["core_auc"][1],
             "折り返し %.3f" % r["core_auc"][3],
             "符号を反転すれば %.3f" % r["zero_flipped_core"],
             "低周波除去を足すと芯で平均 %+.3f" % r["core_lowcut_minus_notch"],
             "太いマスクでは %+.3f" % r["lowcut_minus_notch"],
             "幅の中央値 %.0f px" % r["mask_width_px"],
             "格子のみ %.2f、低周波除去つき %.2f" % (r["mura_notch"], r["mura_lowcut"])]
    absent = [h for h in heads if h not in doc]
    assert not absent, "記録値の見出しの数が docstring に無い: %s" % absent
    if measured is not None:
        diff = {k: (RECORDED_REAL[k], measured[k]) for k in RECORDED_KEYS
                if not np.allclose(_flat_numbers(RECORDED_REAL[k]), _flat_numbers(measured[k]),
                                   rtol=0.0, atol=1e-9)}
        assert not diff, "実測と RECORDED_REAL が違う(記録を更新すること): %s" % diff


def section_real_fabric() -> dict | None:
    print("\n" + "=" * 78)
    print("9) 実写(RAW-FABRID): 9a 描き足したムラで機構を見る / 9b 本物の欠陥で採点する")
    print("=" * 78)
    import os

    base = _fabrid_dir()
    if (os.environ.get("CI") and not os.environ.get(REAL_DATA_ENV)) or base is None:
        print("  実データが無いので実データの章を飛ばす。取得は py -3.11 tools/fetch_realinsp_data.py raw_fabrid")
        print("  記録値(RECORDED_REAL, 2026-11-08): %s" % RECORDED_REAL)
        check_recorded(None)
        print("  記録値の門: 鍵 %d 個・有限・見出しの数が docstring と一致" % len(RECORDED_KEYS))
        return None
    t0 = time.perf_counter()
    good, bad = _fabrid_pick(base)
    print("  データ: %s" % REAL_CREDIT)
    print("  地 = 欠陥なしの実写、ロール(織物)ごとに最初の 1 枚 x 切り出し %d か所 = %d 面。"
          % (len(REAL_CROPS), len(good) * len(REAL_CROPS)))
    print("  ---- 9a) 機構の説明: 実写の地に欠陥 3 種を**描き足す**(本物の欠陥ではない) ----")
    print("  欠陥 3 種は合成と同じ位置・形で描き足すので、真値マスクは足した幾何で決まる。")
    print("  振幅の決め方: 合成の「振幅 / 検出器が見る残差 σ」(線 7・斑点 11・ムラ 4.5)を、")
    print("  実写の地をノッチに通した残差 σ_r に当てて α 倍する: 振幅 = α · 合成の振幅 · σ_r / %.3f。"
          % NOISE)

    names = list(DEFECTS)
    grounds = []
    for roll, fname in good:
        a = _gray(base / "images" / fname)
        flat = a - gaussian_filter(a, REAL_DETREND)       # 照明の傾きを抜いてから周期を推す
        per_x = estimate_period(flat)["fine"]
        per_y = estimate_period(flat.T)["fine"]
        h, w = a.shape
        for fy, fx in REAL_CROPS:
            r0, c0 = int(fy * (h - N)), int(fx * (w - N))
            g = a[r0:r0 + N, c0:c0 + N]
            g = 0.5 + (g - g.mean())
            sr = float(np.std(_notch_residual(g, per_y, per_x)))
            grounds.append({"roll": roll, "file": fname, "g": g, "py": per_y, "px": per_x,
                            "sr": sr, "sg": float(g.std())})
    realdata.mark_read(REAL_DATASET)

    print("\n   ロール     横の周期 px (本/cm)   縦の周期 px (本/cm)   地の σ   ノッチ後の σ_r")
    seen = set()
    for gr in grounds:
        if gr["roll"] in seen:
            continue
        seen.add(gr["roll"])
        print("   %-8s   %6.3f (%4.1f)          %6.3f (%4.1f)          %.3f    %.3f"
              % (gr["roll"], gr["px"], 10 * REAL_PX_PER_MM / gr["px"],
                 gr["py"], 10 * REAL_PX_PER_MM / gr["py"], gr["sg"], gr["sr"]))
    keep = float(np.mean([gr["sr"] / gr["sg"] for gr in grounds]))
    print("  ★格子除去で消えた地は σ の %.0f %% だけ(ノッチ後 / 前 = %.2f)。合成の地は"
          " 0.14 → 雑音 0.010 まで消えた。" % (100 * (1 - keep), keep))
    print("    実写の生機の地は**大半が周期でない**(糸むら・毛羽)—— 残差が地そのものになる。")

    def run(alpha: float, keep_maps: bool = False):
        per = {}
        maps = None
        for i, gr in enumerate(grounds):
            img = gr["g"].copy()
            masks = {}
            for nm in names:
                f, m = _defect_field(nm)
                img = img + alpha * gr["sr"] / NOISE * f
                masks[nm] = m
            anym = np.zeros((N, N), bool)
            for m in masks.values():
                anym |= m
            neg = ~anym
            for dn, fn in _real_detectors(gr["py"], gr["px"]).items():
                s = fn(img)
                per.setdefault(dn, []).append(
                    [auc(s, anym, neg)] + [auc(s, masks[n], neg) for n in names])
                if keep_maps and i == 0 and dn in ("ノッチ(格子のみ)", "ノッチ+低周波除去"):
                    maps = maps or {"img": img, "masks": masks, "g": gr["g"], "roll": gr["roll"]}
                    maps[dn] = s
        return {dn: np.mean(v, axis=0) for dn, v in per.items()}, maps

    print("\n  α を振る(%d 面の平均 AUC。列: まとめ / %s)" % (len(grounds), " / ".join(names)))
    sweep = {}
    for alpha in REAL_ALPHAS:
        tab, _ = run(alpha)
        sweep[alpha] = tab
        print("   α=%.2f  " % alpha + "  ".join(
            "%s %s" % (dn[:4], "/".join("%.2f" % v for v in tab[dn])) for dn in tab))

    tab, maps = run(REAL_ALPHA, keep_maps=True)
    i_sh = names.index("ムラ(輝度低下)")
    print("\n  α=%.2f の表(ムラの振幅 = 残差 σ_r の %.1f 倍)"
          % (REAL_ALPHA, REAL_ALPHA * abs(DEFECTS["ムラ(輝度低下)"]["amp"]) / NOISE))
    print("   検出器                まとめ    " + "  ".join("%-14s" % n for n in names))
    for dn, v in tab.items():
        print("   %-20s %.4f    " % (dn, v[0]) + "  ".join("%-14.4f" % x for x in v[1:]))
    a_notch, a_low = float(tab["ノッチ(格子のみ)"][1 + i_sh]), float(tab["ノッチ+低周波除去"][1 + i_sh])
    low_max = max(float(sweep[a]["ノッチ+低周波除去"][1 + i_sh]) for a in REAL_ALPHAS)
    print("  ★描き足したムラでは合成と同じ: ムラの AUC は格子のみ %.4f、低周波除去を足すと"
          " %.4f。" % (a_notch, a_low))
    print("    ただしこれは**ムラの形(なめらかなガウス)とフィルタの性質**で決まり、実写の地は"
          "ほとんど効かない。本物の欠陥では 9b。")
    print("     α を 0.1〜1.0 で振っても、低周波除去つきのムラは最大 %.3f(でたらめ = 0.5)。"
          "振幅を上げても戻らない。" % low_max)
    print("  ★合成と違ったところ: 合成の格子のみは地が消えたので AUC 1.00 だったが、実写では"
          " α=%.2f で %.2f。" % (REAL_ALPHA, float(tab["ノッチ(格子のみ)"][0])))
    print("     ノッチが消せるのは周期の部分だけで、糸むらは残る —— **検出の限界は地の周期でない部分**。")

    _real_figure(maps["g"], maps["img"], maps["masks"], maps["ノッチ(格子のみ)"],
                 maps["ノッチ+低周波除去"], a_notch, a_low, maps["roll"])
    dt = time.perf_counter() - t0
    print("  所要 %.1f 秒" % dt)
    out = {"n_grounds": len(grounds), "alpha": REAL_ALPHA, "keep_ratio": round(keep, 3),
           "mura_notch": round(a_notch, 4), "mura_lowcut": round(a_low, 4),
           "mura_lowcut_max_over_alpha": round(low_max, 4),
           "pooled_notch": round(float(tab["ノッチ(格子のみ)"][0]), 4),
           "pooled_lowcut": round(float(tab["ノッチ+低周波除去"][0]), 4),
           }
    out.update(section_real_defects(base))
    print("  RECORDED_REAL 用: %s" % out)
    # --- 所見を固定する(壊れたら鳴る) --------------------------------------- #
    # 描き足したムラ(機構の説明)。閾値は実データを見て置いた(合成の 0.9998 / 0.4746 と同じ向き)。
    assert a_notch > 0.9, a_notch
    assert a_low < 0.6, a_low
    assert low_max < 0.6, low_max
    # 本物の欠陥。閾値はどれも実データ(2026-11-08)を見て置いた —— 主張する向きだけを固定する:
    # 件数の下限、低周波除去で下がる(太いマスク・芯の両方の区間)、採点の仕方で数が変わる。
    # ★「どの手法も 0.65 未満」「ゼロ点 0.45 未満」は検出器が悪いことを固定する逆向きの門だったので
    #   外した(値は RECORDED_REAL の defects_auc / core_auc に記録として残る)。
    assert out["defects_n"] >= 300, out["defects_n"]
    assert out["lowcut_minus_notch_ci"][1] < 0.0, out["lowcut_minus_notch_ci"]
    assert out["core_lowcut_minus_notch_ci"][1] < 0.0, out["core_lowcut_minus_notch_ci"]
    assert out["core_auc"][1] - out["defects_auc"][1] > 0.05, (out["core_auc"], out["defects_auc"])
    assert out["n_lowcut_worse"] > out["defects_n"] // 2, out["n_lowcut_worse"]
    assert out["n_drop_gt_0p2_dark"] == out["n_drop_gt_0p2"] > 0, out          # 大きく下がるのは暗い欠陥だけ
    check_recorded(out)
    return out


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
    real = section_real_fabric()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    names = roc["names"]
    dn = "ノッチ+低周波除去"
    print("  * **%s** はまとめた AUC %.4f、しかし「%s」だけ %.4f。"
          % (dn, roc["table"][dn][0], names[2], roc["table"][dn][1][2]))
    print("    低周波を残すだけで %.4f に戻る —— 消していたのは照明ではなく欠陥。"
          % roc["table"]["ノッチ(格子のみ)"][1][2])
    print("  * ゼロ点は窓を %d〜%d px で振っても AUC %.3f〜%.3f。"
          "「周期の整数倍が良い」は符号が逆で、整数倍では地がそのまま残差になる"
          "(残差と |1-G| の相関 %.3f)。"
          % (min(win["k"]), max(win["k"]), min(win["auc"]), max(win["auc"]),
             win["corr"]))
    print("  * 周期: POC のピークは「基線 ÷ 周期の余り」しか返さない。位相の"
          "傾きなら誤差 %+.5f px(FFT の粗い値 %+.5f px の %.0f 倍の精度)。"
          % (per["est"]["fine"] - PERIOD_EST, per["est"]["coarse"] - PERIOD_EST,
             abs(per["est"]["coarse"] - PERIOD_EST)
             / max(abs(per["est"]["fine"] - PERIOD_EST), 1e-12)))
    print("  * 周期の誤差 1 %% では**何も起きない**(残差 %.1f 倍)。予測どおり "
          "ε=%.1f %% で最大次数の成分が外れて %.1f 倍へ跳ねる。"
          % (pe["rms"][3] / pe["base_rms"], pe["eps"][5],
             pe["rms"][5] / pe["base_rms"]))
    print("  * 折り返し平均は同じ ε=0.5 %% で既に %.1f 倍 —— 位相で畳む方式は"
          "周期の誤差に桁で弱い。" % (pe["fold"][2] / pe["fold"][0]))
    rec = real if real is not None else RECORDED_REAL
    print("  * 本物の欠陥(RAW-FABRID %d 個%s): 格子のみの AUC は太いマスクの画素で %.3f、芯で %.3f ——"
          " 採点の仕方で変わる。ゼロ点は符号が逆(結果を見てから反転して %.3f、順位には使わない)。低周波除去で 芯 %+.3f / 太いマスク %+.3f。"
          % (rec["defects_n"], "" if real is not None else "、記録値", rec["defects_auc"][1], rec["core_auc"][1],
             rec["zero_flipped_core"], rec["core_lowcut_minus_notch"], rec["lowcut_minus_notch"]))
    print("  * 描き足したムラ(機構の説明): 格子のみ %.4f、低周波除去つき %.4f。"
          % (rec["mura_notch"], rec["mura_lowcut"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
