# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""年輪を数えて幅の時系列を取り出す —— 年数の誤差と幅の相関は別の量。

樹木の円板(横断面)の画像から**年輪を数え**(年数)、**各年の幅**(気候の代理記録)
を取り出す仕事です。年輪年代学では年数が 1 年ずれると年代照合が丸ごと外れ、
幅系列の相関が落ちると気候復元が効かなくなる —— この 2 つは**別の壊れ方**で、
別に数えないと「合っている」と言えません。

EXTEND: 実写に差し替えるなら :func:`make_scene` が返す辞書の ``img`` を円板の
撮影画像に、``ring``(画素ごとの年番号の真値地図)を人手の境界トレースから
作った年番号地図に、``widths`` をその平均幅に置き換えます。**髄の位置**は
:data:`PITH` の代わりに実測値を渡してください(髄推定の誤差がどう効くかは
4 節で測ってあります)。円板の外縁(樹皮 → 背景)は展開図の各行で自動検出し、
半径の正規化に使います(真値は使いません)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. ★**ゼロ点(髄から 1 本の放射線の輝度ピーク数)は方向しだい**: 24 方向で
   年数が合うのは 18 方向、最悪の方向は偽輪 3 本。★年数を間違えた 6 方向でも
   幅系列の相関は中央値 0.900(最小 0.841)—— **年数を間違えても幅の相関は
   高い**。相関は「隣り合う境界の間隔」で決まるので、偽輪や欠落が 1〜3 本
   入っても残りの境界は合っている。年数と幅の相関を別に数える理由がここにある。
2. **極座標展開(髄中心、`polar_unwrap`)→ 外縁で半径を正規化 → θ 方向メディアン
   (`median_rect` 9x3)→ 24 扇形の測定線(`measure_pos`、正極性)の合意(中央値)
   で 36 年ちょうど**、欠落 0 / 偽輪 0.0、幅の相関 0.996、幅の平均誤差 0.13 px
   (ゼロ点 θ=0 の 0.44 px の 1/3.4)。扇形単位で年数が合うのは 14 / 24 だけ ——
   **合意(中央値)が扇形 1 本の間違いを吸収する**。
3. **最も細い年輪の崖**: 年輪 24 の幅を 4 → 1 px と細めると、合意法は 2.5 px で
   落とし、ゼロ点は 3.0 px で過半数の方向が落とす(4.0 px で 19/24 → 2.5 px で
   3/24)。★閉形式の 1-D モデル(t^1.5 のプロファイル + ぼけ 0.8 ⊕ リサンプル
   0.3 ⊕ 平滑化 0.7 = 1.10 px)の予測はゼロ点 2.9 px(一致)、合意法 1.9 px
   (実測より 0.6 px 楽観)。モデルは木目と θ 方向メディアンの損失を含まない。
   素朴な目安 2σ_tot = 2.21 px は両者の間に落ちる。
4. ★**髄の推定誤差 0 → 20 px は幅系列を歪めない**(相関 0.996 → 0.994)。予想は
   「偏心は幅を cos で変調する」だったが、**cos で変調されるのは半径であって幅
   ではない**(幅は半径の差なので 1 次の項が打ち消す)。偏心成長もうねりも無い
   対照円板で d=15 px のとき、外周半径の cos 回帰の傾きは -14.9 px(予測 -15)、
   幅の傾きは -0.02 px(予測 0)。効くのは**髄の近く**: 半径 S_k < d の年輪は
   ずれた中心からの放射線が届かず、年数が 36 → 34(20 px で幾何の予測 2 年 /
   実測 2 年。15 px は予測 1 / 実測 2 で、うねりぶん早く届かなくなる)。
5. **割れ目(放射方向の暗い線、±3 px うねる)**: 放射線は割れ目と**並走**する
   ので効き方は弱い —— 割れ目 0 → 16 本でゼロ点の年数が合う方向は 19 → 16、
   偽輪の中央値 0.0 → 0.5(最悪 3 本は 0 本の時から 2 本出ている = 木目)。
   ★合意法は 16 本でも年数 36・偽輪 0.0 —— 展開図で割れ目は横線になり、
   θ 方向メディアン(9 行)が消す。
6. **撮像ぼけ σ 0.5 → 4 px**: 合意法の欠落は 0 / 0 / 11 / 25 / 36 / 36 年、
   モデルの予測は 0 / 0 / 5 / 31 / 36 / 36 —— 崖の位置(1.5〜2 px)は当たるが
   σ 1.5 px で実測のほうが早い(3 節と同じ向きのずれ)。★ゼロ点は σ 2 px 以上で
   **偽輪が増える**(中央値 0.0 → 13.0): 段が消えて平らになった所に雑音の山が
   立つ。欠落だけ数えると「ゼロ点はぼけに強い」と読み違える。
7. **対照群**(偏心・うねり / 割れ目 / 腐朽 を 1 つずつ止める): ゼロ点で年数が
   合う方向は 全部あり 18 / 偏心なし 20 / 割れ目なし 19 / 腐朽なし 18 /
   全部なし 22(24 中)—— どれか 1 つが犯人ではなく、**木目の上に小さな要因が
   積み上がる**。合意法は 5 条件すべてで 36 年・偽輪 0.0。

作りながら踏んだ穴(コード内コメントにも残した): 半径 1 px 刻みの展開で幅 4 px の
年輪 19〜24 が丸ごと消えた(2 回のリサンプルでコントラストが半減)→ 2 倍に細かく
取る / 扇形 15° 全体の外縁半径で px に戻すと偏心成長で外側の年輪が全部ずれた →
測った行の半径で戻す / 幅の鍵を 1 年ずらして相関が落ちた → 境界 i は「年輪 k_i に
入る」位置(数字はいずれも試作中の値なのでここには書かない)。

【グラウンドトゥルース】
年輪の幅系列は**閉形式で仕込む**(AR(1) の気候信号 + 周期 11.3 年の成分、
対数正規で 4〜10 px に切り詰め、36 年)。年輪境界の半径は「累積幅 × 偏心成長の
係数(1 + 0.20 cos θ)+ 周方向のうねり(3 次・5 次)」、年輪内の明暗は
早材 0.80 から晩材 0.35 へ t^1.5 で暗くなる閉形式のプロファイル。
髄は画像中心から (-13.5, +18.5) px ずらしてある。割れ目・腐朽の暗斑・木目・
ぼけ・雑音を上に載せる。髄からの放射線の真値は閉形式、ずれた中心からの放射線は
画素ごとの年番号地図を読んで**その放射線が実際に横切る境界**を真値にする
(髄近くの年輪に届かないことも真値側で数える)。

来歴(公開文献のみ): Fritts, *Tree Rings and Climate* (Academic Press, 1976) /
Cook & Kairiukstis (eds.), *Methods of Dendrochronology* (Kluwer, 1990) /
Conover, Rock & Hanks, *Tree-Ring Research* 61 (2005) —— 画像による年輪計測。
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

# --- 場面の諸元 -------------------------------------------------------------- #
N_PIX = 640                      # 視野 [px]
PITH = (306.0, 338.0)            # 髄 (行, 列)。画像中心 (319.5, 319.5) から (-13.5, +18.5) px
R_PITH = 2.5                     # 髄の半径 [px]
N_RINGS = 36                     # 年数(真値)
W_MEAN, W_LO, W_HI = 6.0, 4.0, 10.0   # 年輪幅 [px] の中央値と切り詰め
CLIMATE_AMP = 0.28               # 気候信号の振幅(対数尺度)
E_GROWTH, PHI_GROWTH = 0.20, 0.6      # 偏心成長(あて材): 幅 ×(1 + E cos(θ-φ))
WOBBLE = ((2.0, 3, 0.4), (1.2, 5, 1.7))   # 周方向のうねり (振幅 px, 次数, 位相)
I_EW, I_LW, P_LATE = 0.80, 0.35, 1.5      # 早材 / 晩材の輝度、暗くなる冪
I_PITH, I_BARK, I_BG, BARK_W = 0.30, 0.22, 0.92, 6.0
BLUR = 0.8                       # 撮像ぼけ σ [px]
NOISE = 0.02                     # 撮像雑音 σ
TEXTURE = 0.05                   # 木目(乗算テクスチャ)の振幅
N_CRACK = 3                      # 割れ目の本数(放射方向・うねりつき)
CRACK_HALF, CRACK_WANDER, CRACK_LAMBDA = 1.6, 3.0, 55.0
DECAY = ((0.55, 120.0, 1.1, 9.0), (0.50, 175.0, 3.9, 7.0), (0.45, 80.0, 5.2, 6.0))
SEED = 7
K_THIN = 24                      # 3 節で細くする年輪の番号(1 始まり)

# --- 測定の諸元 -------------------------------------------------------------- #
NTHETA = 360                     # 極座標展開の角度分割(1 行 = 1°)
OVS = 2                          # 半径方向の過剰標本化(1 列 = 1/OVS px)
N_SECT = 24                      # 扇形の数(1 扇形 = 15°)
SECT_ROWS = NTHETA // N_SECT
MEAS_ROWS = 5                    # 測定線の幅方向の平均化 [行 = 度](扇形の中心に置く)
SIG_M = 0.7                      # 測定線の平滑化 σ [px]
THR = 0.02                       # 段の強さ(平滑化後の勾配の山)のしきい値 [輝度/px]
RAY_STEP = 0.25                  # 真値地図を放射線に沿って読む刻み [px]


# --------------------------------------------------------------------------- #
# 場面を作る                                                                    #
# --------------------------------------------------------------------------- #
def make_widths(seed: int = SEED, n: int = N_RINGS) -> np.ndarray:
    """気候信号 = AR(1) + 周期 11.3 年。対数正規で幅にして切り詰める。"""
    rng = np.random.default_rng(seed)
    rho = 0.55
    c = np.zeros(n)
    eps = rng.standard_normal(n)
    for k in range(1, n):
        c[k] = rho * c[k - 1] + np.sqrt(1 - rho ** 2) * eps[k]
    c = c + 0.6 * np.sin(2 * np.pi * np.arange(n) / 11.3)
    c = (c - c.mean()) / c.std()
    return np.clip(W_MEAN * np.exp(CLIMATE_AMP * c), W_LO, W_HI)


def _growth(th, e_growth):
    return 1.0 + e_growth * np.cos(th - PHI_GROWTH)


def _wobble(th, wobble):
    out = np.zeros_like(th)
    for amp, m, psi in wobble:
        out = out + amp * np.sin(m * th + psi)
    return out


def make_scene(widths=None, pith=PITH, e_growth=E_GROWTH, wobble=WOBBLE,
               n_crack=N_CRACK, decay=DECAY, blur=BLUR, noise=NOISE,
               seed=SEED) -> dict:
    """円板の画像と、画素ごとの年番号の真値地図。

    年番号 ``ring``: 0 = 髄、1..N = 年輪、N+1 = 樹皮と外。境界の半径は
    「累積幅 × 偏心成長 + うねり」で、年輪内の輝度は t^P で暗くなる。
    """
    w = make_widths(seed) if widths is None else np.asarray(widths, np.float64)
    n = w.size
    S = R_PITH + np.concatenate([[0.0], np.cumsum(w)])        # S[k] = 年輪 k の外側半径
    yy, xx = np.mgrid[0:N_PIX, 0:N_PIX].astype(np.float64)
    dy, dx = yy - pith[0], xx - pith[1]
    r = np.hypot(dy, dx)
    th = np.arctan2(dy, dx)
    g = _growth(th, e_growth)
    wb = _wobble(th, wobble)
    u = (r - wb) / g                                          # 偏心・うねりを外した半径
    ring = np.searchsorted(S, u, side="right")                # 0..n+1
    inside = (ring >= 1) & (ring <= n)
    kk = np.clip(ring, 1, n)
    t = np.clip((u - S[kk - 1]) / w[kk - 1], 0.0, 1.0)
    img = I_EW - (I_EW - I_LW) * t ** P_LATE
    img[ring == 0] = I_PITH
    bark = (ring == n + 1) & (u < S[n] + BARK_W)
    img[ring == n + 1] = I_BG
    img[bark] = I_BARK

    rng = np.random.default_rng(seed + 1)
    tex = gaussian_filter(rng.standard_normal(img.shape), 1.2)
    tex /= tex.std()
    img = np.where(inside, img * (1.0 + TEXTURE * tex), img)

    # 割れ目: 放射方向だが横にうねる(実物の乾燥割れ)。角度は 16 本ぶんを
    # 先に引いておき、先頭 n_crack 本を使う(本数を振っても入れ子になる)。
    crng = np.random.default_rng(seed + 2)
    cang = crng.uniform(0, 2 * np.pi, 16)
    cph = crng.uniform(0, 2 * np.pi, 16)
    for c in range(int(n_crack)):
        dth = (th - cang[c] + np.pi) % (2 * np.pi) - np.pi
        lateral = r * np.sin(dth)
        off = CRACK_WANDER * np.sin(2 * np.pi * r / CRACK_LAMBDA + cph[c])
        d = np.abs(lateral - off)
        fac = 1.0 - 0.75 * np.clip(1.0 - (d / CRACK_HALF) ** 2, 0.0, 1.0)
        on = inside & (np.cos(dth) > 0.7) & (r > 6.0)
        img = np.where(on, img * fac, img)

    # 腐朽の暗斑
    for depth, r0, th0, sg in (decay or ()):
        cy, cx = pith[0] + r0 * np.sin(th0), pith[1] + r0 * np.cos(th0)
        rho2 = (yy - cy) ** 2 + (xx - cx) ** 2
        img = np.where(inside, img * (1.0 - depth * np.exp(-rho2 / (2 * sg ** 2))), img)

    if blur > 0:
        img = gaussian_filter(img, blur)
    img = np.clip(img + noise * rng.standard_normal(img.shape), 0.0, 1.0)
    return {"img": img, "ring": ring.astype(np.int32), "widths": w, "S": S,
            "pith": tuple(pith), "e_growth": e_growth, "wobble": wobble, "n": n}


# --------------------------------------------------------------------------- #
# 真値: ある中心からある方向の放射線が実際に横切る境界                          #
# --------------------------------------------------------------------------- #
def ray_truth(scene: dict, center, theta: float) -> dict:
    """年番号地図を放射線に沿って読み、番号が**増える**位置(正極性の境界)を返す。

    ずれた中心からの放射線は髄近くの年輪に届かないことがある(その年輪は
    「到達不能」として数え、検出器の欠落とは分ける)。
    """
    ring = scene["ring"]
    n = scene["n"]
    if abs(center[0] - scene["pith"][0]) < 1e-9 and abs(center[1] - scene["pith"][1]) < 1e-9:
        # 髄そのものからの放射線は閉形式: 年輪 k+1 に入る半径 = S_k·G(θ) + うねり(θ)
        g = float(_growth(np.asarray(theta), scene["e_growth"]))
        wb = float(_wobble(np.asarray(theta), scene["wobble"]))
        pos = scene["S"][:-1] * g + wb
        return {"pos": pos, "k": np.arange(1, n + 1), "rho_end": float(scene["S"][-1] * g + wb),
                "unreachable": 0, "double": 0}
    rho = np.arange(0.0, 0.75 * N_PIX, RAY_STEP)
    y = np.clip(np.round(center[0] + rho * np.sin(theta)).astype(int), 0, N_PIX - 1)
    x = np.clip(np.round(center[1] + rho * np.cos(theta)).astype(int), 0, N_PIX - 1)
    k = ring[y, x].copy()
    # ★画素地図を斜めに読むと境界で番号が k, k+1, k, k+1 と震える(最近傍の階段)。
    #   5 標本(1.25 px)未満の短い走りは直前の値に吸収する —— 放置すると真値の
    #   境界が 1〜2 本増え、「年数が合う方向 18 + 合わない 13 = 31 > 24」になった。
    i = 0
    while i < k.size:
        j = i
        while j < k.size and k[j] == k[i]:
            j += 1
        if j - i < 5 and i > 0:
            k[i:j] = k[i - 1]
        i = j
    last = np.nonzero(k <= n)[0]
    rho_end = float(rho[last[-1]]) + 0.5 * RAY_STEP if last.size else 0.0
    inc = np.nonzero((k[1:] > k[:-1]) & (k[1:] <= n))[0] + 1
    pos = 0.5 * (rho[inc - 1] + rho[inc])
    ks = k[inc]
    reached = set(int(v) for v in ks)
    return {"pos": pos, "k": ks.astype(int), "rho_end": rho_end,
            "unreachable": n - len(reached), "double": int(ks.size - len(reached))}


# --------------------------------------------------------------------------- #
# 検出器 2 つ                                                                    #
# --------------------------------------------------------------------------- #
def detect_ray_peaks(img, center, theta: float, rho_end: float,
                     sigma: float = SIG_M) -> np.ndarray:
    """ゼロ点: 髄から 1 本の放射線の輝度プロファイルのピーク(1 年 1 山)。"""
    n = int(round(rho_end)) + 1
    p1 = (center[0] + (n - 1) * np.sin(theta), center[1] + (n - 1) * np.cos(theta))
    prof = np.asarray(fs.line_profile(img, center, p1, num=n))
    sm = np.asarray(fs.smooth_funct_1d_gauss(prof, sigma))
    pk = np.asarray(fs.find_peaks(sm, distance=2), np.float64)
    return pk


def sector_row(s: int) -> int:
    """扇形 ``s`` の中心行(展開図の行 = 角度 [度])。"""
    return s * SECT_ROWS + SECT_ROWS // 2


def sector_theta(s: int) -> float:
    """扇形 ``s`` の中心角 [rad](展開図の行と同じ向き・同じ角度)。"""
    return 2.0 * np.pi * sector_row(s) / NTHETA


def disc_edge(pol: np.ndarray) -> np.ndarray:
    """展開図の行ごとに円板の外縁(暗い樹皮 → 明るい背景)の半径を返す。

    外から内へ見て最初に 0.5 を割る位置 = 樹皮の外側。θ 方向に循環メディアン
    (±4 行)を掛けて割れ目・雑音の飛びを落とす。真値は使わない。
    """
    nr = pol.shape[1]
    out = np.zeros(pol.shape[0])
    for i in range(pol.shape[0]):
        sm = np.asarray(fs.smooth_funct_1d_gauss(pol[i], 1.5 * OVS))
        dark = np.nonzero(sm < 0.5)[0]
        out[i] = dark[-1] + 0.5 if dark.size else nr - 1.0
    return np.median(np.stack([np.roll(out, s) for s in range(-4, 5)]), axis=0)


def polar_stack(img, center, med=(1.0, 0.0)) -> dict:
    """極座標展開(髄中心、1/OVS px/列、1°/行)→ 外縁で半径を正規化 → θ 方向メディアン。

    ★角度一定の展開図では θ 窓の接線方向の長さが半径に比例して伸びる。偏心成長
    (境界の傾き dR/dθ = S·E·sin)があると外側の年輪ほど θ 窓の中でにじむので、
    先に**外縁の形で各行の半径を正規化**して年輪を縦にそろえてから θ 方向に
    まとめる(年輪年代学の「外形で正規化する」作法)。正規化後の位置は扇形ごとに
    外縁の半径で px へ戻す。

    ★半径方向は OVS 倍に細かく取る。展開(双一次)と正規化(線形補間)で 2 回
    リサンプルするので、1 px 刻みだと 4 px の年輪のコントラストが半分に落ちた
    (最初そう書いて幅 4 px の年輪 19〜24 を丸ごと落とした)。
    列の単位は 1/OVS px。``r_disc`` / ``r_bar`` も列単位。
    """
    cy, cx = float(center[0]), float(center[1])
    avail = int(min(cy, cx, N_PIX - 1 - cy, N_PIX - 1 - cx)) - 1
    nr = OVS * avail + 1
    pol = np.asarray(fs.ledger.polar_unwrap(img, center=(cy, cx), r_in=0.0,
                                            r_out=float(avail), nr=nr, ntheta=NTHETA),
                     np.float64)
    pol = np.clip(pol, 0.0, 1.0)
    r_disc = disc_edge(pol)
    r_bar = float(np.median(r_disc))
    nr2 = int(np.ceil(r_bar)) + 4 * OVS
    grid = np.arange(nr2, dtype=np.float64)
    norm = np.empty((NTHETA, nr2))
    cols = np.arange(nr, dtype=np.float64)
    for i in range(NTHETA):
        norm[i] = np.interp(grid, cols * (r_bar / r_disc[i]), pol[i])
    fil = np.asarray(fs.apply(norm, "median_rect", a=med[0], b=med[1])) if med else norm
    return {"pol": pol, "norm": norm, "fil": fil, "r_disc": r_disc, "r_bar": r_bar,
            "avail": avail}


def detect_sectors(ps: dict, sigma: float = SIG_M, thr: float = THR) -> list[np.ndarray]:
    """扇形ごとに r 方向の測定線を置き、正極性(暗→明 = 晩材→早材)の段を拾う。

    位置は正規化した半径で出るので、扇形の外縁半径で px に戻す。樹皮 → 背景の
    段(正極性)は外縁の 2.5 px 内側で切って落とす。
    """
    fil, r_disc, r_bar = ps["fil"], ps["r_disc"], ps["r_bar"]
    nr = fil.shape[1]
    out = []
    for s in range(N_SECT):
        row_c = float(sector_row(s))
        m = fs.ledger.gen_measure_rectangle2(row_c, (nr - 1) / 2.0, 0.0,
                                             (nr - 1) / 2.0, MEAS_ROWS, fil.shape)
        # ★threshold=0 で全部取り、段の高さは自分で測る。measure_pos の amplitude
        #   (勾配ローブの両端差)は木目で勾配が単調でなくなると段の途中で止まり、
        #   0.14 の段を 0.05 と返す(8 節で数える)。
        edges = fs.ledger.measure_pos(fil, m, sigma=sigma * OVS, threshold=0.0,
                                      transition="positive")
        r0 = int(round(row_c)) - MEAS_ROWS // 2
        prof = fil[max(0, r0):r0 + MEAS_ROWS].mean(axis=0)
        sm = np.asarray(fs.smooth_funct_1d_gauss(prof, sigma * OVS))
        grad = np.asarray(fs.derivate_funct_1d(sm)) * OVS          # 輝度 / px
        # ★px へ戻す外縁半径は**測った行**のもの。扇形 15° 全体の中央値を使うと
        #   偏心成長で外縁が扇形の中で 10 px 以上動くので外側の年輪が全部ずれる
        #   (最初そう書いて年輪 18〜35 を丸ごと落とした)。
        rd = float(np.median(r_disc[max(0, r0):r0 + MEAS_ROWS]))
        pos = []
        for e in edges:
            i = min(nr - 1, max(0, int(round(e["pos"]))))
            # 段の強さは**勾配の山の高さ**(輝度/px)で判定する。「±2 px の上がり」
            # だと 4 px の年輪は窓が 1 周期ぶんになって上がりが 0 になる
            # (最初そう書いて幅 4 px の年輪をすべて落とした)。
            if float(grad[max(0, i - 1):i + 2].max()) >= thr:
                pos.append(e["pos"] * (rd / r_bar) / OVS)
        pos = np.asarray(pos, np.float64)
        out.append(pos[pos < rd / OVS - 2.5])
    return out


# --------------------------------------------------------------------------- #
# 評価: 欠落と偽輪を分けて数え、幅は境界の対で出す                              #
# --------------------------------------------------------------------------- #
def match_ray(dets: np.ndarray, truth: dict) -> dict:
    """検出位置を真値の境界へ最近傍で対応づける(許容 = 局所幅の 45 %、下限 1 px)。"""
    pos, ks, rho_end = truth["pos"], truth["k"], truth["rho_end"]
    dets = np.sort(dets[(dets >= 0.0) & (dets < rho_end + 2.0)])
    used = np.zeros(dets.size, bool)
    hit = np.full(pos.size, np.nan)
    for i in range(pos.size):
        nxt = pos[i + 1] if i + 1 < pos.size else rho_end
        tol = max(1.0, 0.45 * (nxt - pos[i]))
        if dets.size == 0:
            break
        d = np.abs(dets - pos[i])
        d[used] = np.inf
        j = int(np.argmin(d))
        if d[j] <= tol:
            hit[i] = dets[j]
            used[j] = True
    # 境界 i は「年輪 ks[i] に入る」位置なので、年輪 ks[i] の幅 = pos[i+1] - pos[i]。
    # (最初 ks[i+1] を鍵にして 1 年ずれ、合意法の幅の相関が 0.62 に落ちた。)
    # 最後の年輪の外側は樹皮(負極性の段)なので、正極性の段だけでは幅が出ない。
    widths = {}
    for i in range(pos.size - 1):
        if ks[i + 1] == ks[i] + 1 and np.isfinite(hit[i]) and np.isfinite(hit[i + 1]):
            widths[int(ks[i])] = (float(hit[i + 1] - hit[i]), float(pos[i + 1] - pos[i]))
    missed = sorted(int(ks[i]) for i in range(pos.size) if not np.isfinite(hit[i]))
    return {"n_det": int(dets.size), "n_true": int(pos.size), "missed": missed,
            "false": int((~used).sum()), "widths": widths, "hit": hit}


def consensus(results: list[dict], n: int) -> dict:
    """方向ごとの結果を中央値でまとめる。年数・欠落・偽輪・幅系列を別に返す。"""
    counts = np.array([r["n_det"] for r in results])
    n_est = int(round(float(np.median(counts))))
    W = np.full((len(results), n), np.nan)
    T = np.full((len(results), n), np.nan)
    for i, r in enumerate(results):
        for k, (e, t) in r["widths"].items():
            W[i, k - 1], T[i, k - 1] = e, t
    n_dir = np.sum(np.isfinite(W), axis=0)
    w_est = np.full(n, np.nan)
    for k in range(n):
        if n_dir[k] >= max(1, len(results) // 8):
            w_est[k] = float(np.median(W[np.isfinite(W[:, k]), k]))
    miss_frac = np.zeros(n)
    for r in results:
        for k in r["missed"]:
            miss_frac[k - 1] += 1.0 / len(results)
    missing = [k + 1 for k in range(n) if miss_frac[k] > 0.5]
    false_med = float(np.median([r["false"] for r in results]))
    return {"n_est": n_est, "counts": counts, "w_est": w_est, "missing": missing,
            "false": false_med, "false_max": int(max(r["false"] for r in results)),
            "exact": int(np.sum(counts == n))}


def width_stats(w_est: np.ndarray, w_true: np.ndarray) -> dict:
    ok = np.isfinite(w_est) & np.isfinite(w_true)
    if ok.sum() < 3:
        return {"corr": np.nan, "mae": np.nan, "scale": np.nan, "n": int(ok.sum())}
    a, b = w_est[ok], w_true[ok]
    return {"corr": float(np.corrcoef(a, b)[0, 1]), "mae": float(np.mean(np.abs(a - b))),
            "scale": float(a.mean() / b.mean()), "n": int(ok.sum())}


def run_zero(scene: dict, center=None, thetas=None) -> dict:
    """ゼロ点を方向ごとに走らせて集計(既定は 24 方向、報告は θ=0 と分布)。"""
    center = scene["pith"] if center is None else center
    thetas = [sector_theta(s) for s in range(N_SECT)] if thetas is None else thetas
    res = []
    for th in thetas:
        tr = ray_truth(scene, center, th)
        res.append(match_ray(detect_ray_peaks(scene["img"], center, th, tr["rho_end"]), tr))
    return {"per": res, "cons": consensus(res, scene["n"])}


def run_consensus(scene: dict, center=None, sigma=SIG_M, thr=THR, med=(1.0, 0.0)) -> dict:
    center = scene["pith"] if center is None else center
    ps = polar_stack(scene["img"], center, med=med)
    # 円板が展開図に収まっていること(収まらないと外縁の検出が嘘になる)
    assert float(ps["r_disc"].max()) / OVS < ps["avail"] - 2, (ps["r_disc"].max(), ps["avail"])
    dets = detect_sectors(ps, sigma=sigma, thr=thr)
    res, truths = [], []
    for s in range(N_SECT):
        th = sector_theta(s)
        tr = ray_truth(scene, center, th)
        truths.append(tr)
        res.append(match_ray(dets[s], tr))
    out = consensus(res, scene["n"])
    out.update({"per": res, "pol": ps["pol"], "fil": ps["fil"], "norm": ps["norm"],
                "r_disc": ps["r_disc"], "r_bar": ps["r_bar"], "dets": dets,
                "truths": truths,
                "unreachable": int(np.median([t["unreachable"] for t in truths])),
                "double": int(np.median([t["double"] for t in truths]))})
    return out


# --------------------------------------------------------------------------- #
# 崖の予測 —— 閉形式の 1-D モデル(年輪内の t^P プロファイル + ぼけ + 検出器)      #
# --------------------------------------------------------------------------- #
RESAMPLE_SIG = 0.3     # 双一次リサンプル 1 回ぶんのぼけの近似 [px](幅 1 px の箱 ≈ σ 0.29)


def model_profile(w: float, blur: float, step: float = 0.05, w_nb: float = 6.0):
    """幅 ``w`` の年輪を幅 ``w_nb`` の年輪 3 本ずつで挟んだ放射方向の輝度(ぼけ後)。"""
    edges = [-3 * w_nb, -2 * w_nb, -w_nb, 0.0, w, w + w_nb, w + 2 * w_nb, w + 3 * w_nb]
    x = np.arange(edges[0] - 4.0, edges[-1] + 4.0, step)
    prof = np.full_like(x, I_EW)
    for a, b in zip(edges[:-1], edges[1:]):
        m = (x >= a) & (x < b)
        t = (x[m] - a) / (b - a)
        prof[m] = I_EW - (I_EW - I_LW) * t ** P_LATE
    sig = float(np.hypot(blur, RESAMPLE_SIG)) / step
    return x, gaussian_filter(prof, sig)


def predict_detectable(w: float, blur: float, mode: str) -> bool:
    """閉形式モデルで、幅 ``w`` の年輪が検出できるかを予測する。

    ``mode="consensus"``: その年輪の外側の境界(次の年輪へ入る段)で、平滑化後の
    勾配の山が :data:`THR` 以上。``mode="zero"``: 1 px 刻みの平滑化プロファイルで、
    その年輪と次の年輪の輝度の山が**別々に**立つ(2 山)。
    """
    x, prof = model_profile(w, blur)
    if mode == "zero":
        xs = np.arange(x[0], x[-1], 1.0)
        sm = np.asarray(fs.smooth_funct_1d_gauss(np.interp(xs, x, prof), SIG_M))
        pk = np.asarray(fs.find_peaks(sm, distance=2), int)
        return int(np.sum((xs[pk] >= -1.0) & (xs[pk] < w + 3.0))) >= 2
    xs = np.arange(x[0], x[-1], 1.0 / OVS)
    sm = np.asarray(fs.smooth_funct_1d_gauss(np.interp(xs, x, prof), SIG_M * OVS))
    g = np.asarray(fs.derivate_funct_1d(sm)) * OVS
    # 年輪の両側の境界(x=0 と x=w)が**別々の**勾配の山として THR 以上で立つこと
    pk = np.asarray(fs.find_peaks(g, height=THR, distance=1), int)
    return int(np.sum((xs[pk] >= -1.5) & (xs[pk] < w + 1.5))) >= 2


def model_cliff(blur: float, mode: str) -> float:
    """幅を 6 → 0.5 px と 0.1 px 刻みで細めて、モデルが最初に落とす幅。"""
    for w in np.arange(6.0, 0.4, -0.1):
        if not predict_detectable(float(w), blur, mode):
            return float(round(w, 1))
    return 0.0


def thin_found(results: list[dict], k: int) -> bool:
    """年輪 ``k`` の幅(両側の境界)が過半数の方向で取れたか。"""
    return sum(k in r["widths"] for r in results) * 2 > len(results)


# --------------------------------------------------------------------------- #
# 1-2. ゼロ点と合意法                                                           #
# --------------------------------------------------------------------------- #
def section_baseline() -> dict:
    print("\n" + "=" * 78)
    print("1-2) ゼロ点(1 本の放射線)と 合意法(極座標展開 + 24 扇形の中央値)")
    print("=" * 78)
    sc = make_scene()
    w = sc["widths"]
    print("  真値: %d 年、幅 %.2f〜%.2f px(平均 %.2f)、髄 (%.1f, %.1f)、偏心成長 ±%.0f %%"
          % (sc["n"], w.min(), w.max(), w.mean(), sc["pith"][0], sc["pith"][1],
             100 * E_GROWTH))

    # ゼロ点: θ = 0(東向き)の 1 本
    z = run_zero(sc, thetas=[0.0])
    z0 = z["per"][0]
    zw = np.full(sc["n"], np.nan)
    zt = np.full(sc["n"], np.nan)
    for k, (e, t) in z0["widths"].items():
        zw[k - 1], zt[k - 1] = e, t
    zs = width_stats(zw, zt)
    print("\n  ゼロ点(θ=0 の放射線、ピーク数): 年数 %d(真値 %d)、欠落 %d、偽輪 %d"
          % (z0["n_det"], z0["n_true"], len(z0["missed"]), z0["false"]))
    print("     幅の相関 %.3f(対応づけできた %d 年)、平均誤差 %.2f px、"
          "尺度 %.3f(この方向の真値に対して)" % (zs["corr"], zs["n"], zs["mae"], zs["scale"]))
    z24 = run_zero(sc)
    zc = z24["cons"]
    print("  ゼロ点を 24 方向で: 年数が合う方向 %d / %d、年数の中央値 %d、"
          "偽輪の中央値 %.1f(最悪 %d)"
          % (zc["exact"], N_SECT, zc["n_est"], zc["false"], zc["false_max"]))
    # ★年数を間違えた方向でも幅の相関は高いか —— 年数と幅の相関は別の量
    wrong = []
    for r in z24["per"]:
        if r["n_det"] != r["n_true"]:
            e = np.array([v[0] for v in r["widths"].values()])
            t = np.array([v[1] for v in r["widths"].values()])
            if e.size >= 3:
                wrong.append(float(np.corrcoef(e, t)[0, 1]))
    wrong_med = float(np.median(wrong)) if wrong else float("nan")
    print("  ★年数を間違えた %d 方向の幅の相関は 中央値 %.3f(最小 %.3f)—— "
          "偽輪や欠落が 1〜%d 本入っても、残りの境界の間隔は合っている。"
          % (len(wrong), wrong_med, min(wrong) if wrong else float("nan"),
             zc["false_max"]))

    # 合意法
    c = run_consensus(sc)
    cs = width_stats(c["w_est"], w)
    print("\n  合意法: 年数 %d(真値 %d)、欠落 %d 年、偽輪の中央値 %.1f、"
          "年数が合う扇形 %d / %d" % (c["n_est"], sc["n"], len(c["missing"]), c["false"],
                                   c["exact"], N_SECT))
    print("     幅の相関 %.3f(%d 年)、平均誤差 %.2f px、尺度 %.3f(θ 平均の真値に対して)"
          % (cs["corr"], cs["n"], cs["mae"], cs["scale"]))
    print("  ゼロ点(θ=0)の幅の平均誤差 %.2f px は合意法の %.1f 倍 —— 1 本の放射線の"
          "境界位置は木目で ±0.5 px 揺れる。" % (zs["mae"], zs["mae"] / cs["mae"]))

    # 図: 場面 / 真値地図 / 極座標展開(生・メディアン後)
    figs.save_grid("scene",
                   [sc["img"], sc["ring"].astype(np.float64) / (sc["n"] + 1)],
                   ["円板の画像(%d 年、割れ目 %d 本、腐朽 %d 個)" % (sc["n"], N_CRACK, len(DECAY)),
                    "真値: 画素ごとの年番号"],
                   ncols=2, title="年輪の円板 —— 髄は中心から (%+.1f, %+.1f) px"
                                  % (PITH[0] - (N_PIX - 1) / 2, PITH[1] - (N_PIX - 1) / 2),
                   caption="幅系列は AR(1) の気候信号、偏心成長 ±%.0f %%、周方向のうねり、"
                           "割れ目、腐朽、木目、ぼけ、雑音を仕込んである。" % (100 * E_GROWTH))
    figs.save_grid("polar_stages",
                   [c["pol"].T, c["norm"].T, c["fil"].T],
                   ["極座標展開(縦 = 半径 px、横 = 角度 1°/列)",
                    "外縁で半径を正規化(年輪が横にそろう)",
                    "θ 方向メディアン 9x3 の後(割れ目の縦線が消える)"],
                   ncols=3, title="合意法の 3 段階(髄を中心に展開)",
                   caption="偏心成長で境界が θ とともに斜めに走るので、正規化しないと"
                           "θ 窓の中で外側の年輪がにじむ。")
    # 図: 展開図に検出(赤)と真値(青)を重ねる
    rgb = np.repeat(c["pol"][..., None], 3, axis=2)
    for s in range(N_SECT):
        row = sector_row(s)
        for p in c["truths"][s]["pos"]:
            j = int(round(p * OVS))
            if 0 <= j < rgb.shape[1]:
                rgb[row - 6:row - 2, max(0, j - 1):j + 2] = (0.1, 0.3, 1.0)
        for p in c["dets"][s]:
            j = int(round(p * OVS))
            if 0 <= j < rgb.shape[1]:
                rgb[row + 2:row + 6, max(0, j - 1):j + 2] = (1.0, 0.15, 0.1)
    figs.save("polar_edges_map", rgb,
              "展開図(横 = 半径 px、縦 = 角度)に、扇形ごとの測定線が拾った境界(赤、下)と"
              "真値(青、上)を重ねた。")
    # 図: 幅の時系列
    yrs = np.arange(1, sc["n"] + 1, dtype=float)
    okz = np.isfinite(zw)
    okc = np.isfinite(c["w_est"])
    figs.save_plot("ring_widths",
                   [("真値(θ 平均)", yrs, w),
                    ("合意法 r=%.3f" % cs["corr"], yrs[okc], c["w_est"][okc]),
                    ("ゼロ点 θ=0 r=%.3f" % zs["corr"], yrs[okz], zw[okz])],
                   xlabel="年(髄から数えて)", ylabel="年輪幅 [px]",
                   title="年輪幅の時系列(気候の代理記録)",
                   caption="ゼロ点は θ=0 方向の局所幅なので偏心成長ぶん尺度がずれる。")
    return {"sc": sc, "z0": z0, "zs": zs, "z24": zc, "c": c, "cs": cs,
            "wrong_n": len(wrong), "wrong_med": wrong_med}


# --------------------------------------------------------------------------- #
# 3. 最も細い年輪の崖                                                            #
# --------------------------------------------------------------------------- #
def section_thin_ring() -> dict:
    print("\n" + "=" * 78)
    print("3) 最も細い年輪の崖 —— 年輪 %d の幅を 4 → 1 px に細める" % K_THIN)
    print("=" * 78)
    sig_tot = float(np.hypot(BLUR, np.hypot(SIG_M, RESAMPLE_SIG)))
    pred_c = model_cliff(BLUR, "consensus")
    pred_z = model_cliff(BLUR, "zero")
    print("  予測(閉形式の 1-D モデル: t^%.1f のプロファイル + ぼけ σ %.1f ⊕ リサンプル %.1f"
          " ⊕ 平滑化 %.1f = %.2f px):" % (P_LATE, BLUR, RESAMPLE_SIG, SIG_M, sig_tot))
    print("     合意法(境界の勾配 ≥ %.2f /px)は %.1f px から、ゼロ点(輝度の山が 2 つ"
          "立つ)は %.1f px から落ちる。" % (THR, pred_c, pred_z))
    print("     素朴な目安「2 つの段の分離 w > 2σ_tot = %.2f px」も併記。" % (2 * sig_tot))
    print("\n   幅 [px]   ゼロ点 24 方向: 年輪 %d が取れた方向   合意法: 年数 / 年輪 %d / 欠落"
          % (K_THIN, K_THIN))
    base = make_widths()
    rows, thin_w, z_frac, c_found = [], [], [], []
    for wt in (4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0):
        w = base.copy()
        w[K_THIN - 1] = wt
        sc = make_scene(widths=w)
        z = run_zero(sc)["per"]
        zf = sum(K_THIN in r["widths"] for r in z)
        c = run_consensus(sc)
        cf = thin_found(c["per"], K_THIN)
        thin_w.append(wt)
        z_frac.append(zf)
        c_found.append(cf)
        rows.append(["%.1f" % wt, "%d / %d" % (zf, N_SECT), str(c["n_est"]),
                     "○" if cf else "×", str(len(c["missing"]))])
        print("   %5.1f            %2d / %d                        %3d / %s / %d"
              % (wt, zf, N_SECT, c["n_est"], "○" if cf else "×", len(c["missing"])))
    z_cliff = next((wt for wt, f in zip(thin_w, z_frac) if 2 * f <= N_SECT), None)
    c_cliff = next((wt for wt, f in zip(thin_w, c_found) if not f), None)
    print("\n  ★合意法が落とす幅 %.1f px(モデルの予測 %.1f px)、ゼロ点(過半数の方向で"
          "落ちる幅)%.1f px(予測 %.1f px)。" % (c_cliff, pred_c, z_cliff, pred_z))
    figs.save_table("cliff_thin_ring",
                    ["幅 px", "ゼロ点: 取れた方向", "合意法 年数", "年輪 %d" % K_THIN, "欠落"],
                    rows, title="最も細い年輪の崖(モデル予測: 合意法 %.1f px / ゼロ点 %.1f px)"
                                % (pred_c, pred_z))
    return {"pred_c": pred_c, "pred_z": pred_z, "z_cliff": z_cliff, "c_cliff": c_cliff,
            "sig_tot": sig_tot}


# --------------------------------------------------------------------------- #
# 4. 髄の推定誤差                                                                #
# --------------------------------------------------------------------------- #
def section_pith_error() -> dict:
    print("\n" + "=" * 78)
    print("4) 髄の推定誤差 0 → 20 px —— 予想は「偏心は幅を cos で変調する」")
    print("=" * 78)
    sc = make_scene()
    w = sc["widths"]
    # ずらす向きは画像中心へ向かう向き(円板が展開図に収まる側)
    th_d = float(np.arctan2((N_PIX - 1) / 2 - PITH[0], (N_PIX - 1) / 2 - PITH[1]))
    print("  ずらす向き %.0f°。予測: 半径 S_k < d の年輪はずれた中心からの放射線が"
          "届かない(合意法で欠落)。" % np.rad2deg(th_d))
    print("\n   d [px]   合意法: 年数  欠落  偽輪   幅の相関   平均誤差   到達不能(予測/実測)")
    ds, n_est, corr, lost_pred, lost_meas = [], [], [], [], []
    for d in (0.0, 2.0, 5.0, 10.0, 15.0, 20.0):
        ctr = (sc["pith"][0] + d * np.sin(th_d), sc["pith"][1] + d * np.cos(th_d))
        c = run_consensus(sc, center=ctr)
        st = width_stats(c["w_est"], w)
        lp = int(np.sum(sc["S"][1:] < d))
        ds.append(d)
        n_est.append(c["n_est"])
        corr.append(st["corr"])
        lost_pred.append(lp)
        lost_meas.append(c["unreachable"])
        print("   %4.0f        %3d      %2d    %.1f     %.3f      %.2f px      %d / %d"
              % (d, c["n_est"], len(c["missing"]), c["false"], st["corr"], st["mae"],
                 lp, c["unreachable"]))
    print("\n  ★幅の相関は d=%.0f px でも %.3f。年数は %d → %d(到達不能 予測 %d / 実測 %d)。"
          % (ds[-1], corr[-1], n_est[0], n_est[-1], lost_pred[-1], lost_meas[-1]))

    # cos 変調の検証は偏心成長もうねりも無い対照円板で(成長の cos と混ざらないため)
    sc0 = make_scene(e_growth=0.0, wobble=(), pith=((N_PIX - 1) / 2, (N_PIX - 1) / 2))
    d = 15.0
    ctr = (sc0["pith"][0] + d * np.sin(th_d), sc0["pith"][1] + d * np.cos(th_d))
    c0 = run_consensus(sc0, center=ctr)
    cosv, r_out, w_mean = [], [], []
    for s in range(N_SECT):
        th = sector_theta(s)
        tr = c0["truths"][s]
        ws = [e for k, (e, t) in c0["per"][s]["widths"].items() if k > 5]
        if len(ws) >= 5:
            cosv.append(np.cos(th - th_d))
            r_out.append(tr["rho_end"])
            w_mean.append(float(np.mean(ws)))
    if len(cosv) >= 5:
        slope_r = float(np.polyfit(cosv, r_out, 1)[0])
        slope_w = float(np.polyfit(cosv, w_mean, 1)[0])
    else:
        slope_r = slope_w = float("nan")
    print("  ★対照円板(偏心成長・うねり無し)で d=%.0f px: 外周半径の cos 回帰の傾き "
          "%+.1f px(予測 %+.0f)、\n     幅の傾き %+.2f px(予測 0)。"
          "**cos で変調されるのは半径で、幅は 1 次で打ち消す**。" % (d, slope_r, -d, slope_w))
    figs.save_plot("cliff_pith_error",
                   [("年数(合意法)", ds, n_est),
                    ("真値 %d" % sc["n"], ds, [float(sc["n"])] * len(ds)),
                    ("到達不能の予測(年)", ds, [float(sc["n"] - v) for v in lost_pred])],
                   xlabel="髄の推定誤差 d [px]", ylabel="年数",
                   title="髄がずれると髄近くの年輪に届かなくなる(幅の相関 %.3f〜%.3f)"
                         % (min(corr), max(corr)),
                   caption="幅系列の相関はほぼ動かない。減るのは年数で、幾何で予測できる。")
    return {"d": ds, "n_est": n_est, "corr": corr, "lost_pred": lost_pred,
            "lost_meas": lost_meas, "slope_r": slope_r, "slope_w": slope_w}


# --------------------------------------------------------------------------- #
# 5. 割れ目の本数                                                                #
# --------------------------------------------------------------------------- #
def section_cracks() -> dict:
    print("\n" + "=" * 78)
    print("5) 割れ目の本数 0 → 16 —— 偽輪はどこから増えるか")
    print("=" * 78)
    print("  割れ目は放射方向に走り ±%.0f px うねる。放射線は割れ目と**並走**するので、"
          "うねりが線を横切る方向だけが段を拾う。" % CRACK_WANDER)
    print("\n   本数   ゼロ点 24 方向: 偽輪の中央値 / 最悪 / 年数が合う方向   "
          "合意法: 年数 / 偽輪 / 年数が合う扇形")
    ns, z_med, z_max, z_ok, c_false = [], [], [], [], []
    for nc in (0, 2, 4, 8, 16):
        sc = make_scene(n_crack=nc, decay=())      # 腐朽は止めて割れ目だけの効きを見る
        z = run_zero(sc)["cons"]
        c = run_consensus(sc)
        ns.append(nc)
        z_med.append(z["false"])
        z_max.append(z["false_max"])
        z_ok.append(z["exact"])
        c_false.append(c["false"])
        print("   %3d          %4.1f / %2d / %2d                          %3d / %.1f / %2d"
              % (nc, z["false"], z["false_max"], z["exact"], c["n_est"], c["false"],
                 c["exact"]))
    print("\n  ★ゼロ点で年数が合う方向は %d 本 → %d 本で %d → %d(24 方向中)、"
          "偽輪の中央値 %.1f → %.1f。" % (ns[0], ns[-1], z_ok[0], z_ok[-1], z_med[0], z_med[-1]))
    print("     合意法は %d 本でも年数 %d・偽輪 %.1f —— 展開図で割れ目は横線になり、"
          "θ 方向メディアン(9 行)が消す。" % (ns[-1], N_RINGS, c_false[-1]))
    figs.save_plot("cliff_cracks",
                   [("ゼロ点 偽輪の中央値(24 方向)", ns, z_med),
                    ("ゼロ点 偽輪の最悪", ns, z_max),
                    ("合意法 偽輪", ns, c_false)],
                   xlabel="割れ目の本数", ylabel="偽輪 [年]",
                   title="割れ目が増えるとゼロ点は偽輪を数える(腐朽なし)")
    return {"n": ns, "z_med": z_med, "z_max": z_max, "z_ok": z_ok, "c_false": c_false}


# --------------------------------------------------------------------------- #
# 6. 撮像ぼけ                                                                    #
# --------------------------------------------------------------------------- #
def section_blur() -> dict:
    print("\n" + "=" * 78)
    print("6) 撮像ぼけ σ 0.5 → 4 px —— 晩材の縁が消える点")
    print("=" * 78)
    print("  予測は 3 節と同じ閉形式モデルを年輪ごとの幅で評価する(合意法: 境界の勾配 < %.2f"
          " /px なら欠落)。" % THR)
    print("\n   σ [px]   合意法: 年数 / 欠落(過半数) / 扇形平均   ゼロ点 24 方向: 年数の中央値"
          " / 欠落 / 偽輪   予測: 合意法 / ゼロ点")
    sig, c_miss, c_mean, z_miss, z_false, pred_c, pred_z = [], [], [], [], [], [], []
    w = make_widths()
    for b in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
        sc = make_scene(blur=b)
        c = run_consensus(sc)
        z = run_zero(sc)
        zm = float(np.median([len(r["missed"]) for r in z["per"]]))
        pc = int(sum(not predict_detectable(float(v), b, "consensus") for v in w))
        pz = int(sum(not predict_detectable(float(v), b, "zero") for v in w))
        sig.append(b)
        c_miss.append(len(c["missing"]))
        c_mean.append(float(np.mean([len(r["missed"]) for r in c["per"]])))
        z_miss.append(zm)
        z_false.append(z["cons"]["false"])
        pred_c.append(pc)
        pred_z.append(pz)
        print("   %4.1f        %3d / %2d / %5.1f                     %3d / %4.1f / %4.1f"
              "          %2d / %2d"
              % (b, c["n_est"], len(c["missing"]), c_mean[-1], z["cons"]["n_est"], zm,
                 z["cons"]["false"], pc, pz))
    print("\n  ★合意法の欠落(過半数)%s、モデルの予測 %s。"
          % (" / ".join(str(v) for v in c_miss), " / ".join(str(v) for v in pred_c)))
    print("     ゼロ点は σ %.0f px 以上で偽輪が増える(中央値 %.1f → %.1f)—— 段が消えて"
          "平らになった所に雑音の山が立つ。欠落だけ数えると「ぼけに強い」と読み違える。"
          % (sig[3], z_false[0], z_false[-1]))
    figs.save_plot("cliff_blur",
                   [("合意法 欠落(過半数の扇形)", sig, c_miss),
                    ("合意法 欠落(扇形平均)", sig, c_mean),
                    ("モデル予測(合意法)", sig, pred_c),
                    ("ゼロ点 偽輪の中央値", sig, z_false)],
                   xlabel="撮像ぼけ σ [px]", ylabel="年",
                   title="ぼけると細い年輪から順に消える")
    return {"sig": sig, "c_miss": c_miss, "c_mean": c_mean, "z_miss": z_miss,
            "z_false": z_false, "pred_c": pred_c, "pred_z": pred_z}


# --------------------------------------------------------------------------- #
# 7. 対照群 2×2                                                                  #
# --------------------------------------------------------------------------- #
def section_controls() -> dict:
    print("\n" + "=" * 78)
    print("7) 対照群 —— 偏心・うねり / 割れ目 / 腐朽 を 1 つずつ止める")
    print("=" * 78)
    print("   偏心  割れ目  腐朽   ゼロ点 24 方向: 年数が合う方向 / 偽輪の中央値 / 最悪"
          "   合意法: 年数 / 偽輪 / 幅の相関")
    conds = [("全部あり", True, True, True), ("偏心なし", False, True, True),
             ("割れ目なし", True, False, True), ("腐朽なし", True, True, False),
             ("全部なし", False, False, False)]
    rows, out = [], {}
    for name, ecc, crack, decay in conds:
        kw = {}
        if not ecc:
            kw.update(e_growth=0.0, wobble=(), pith=((N_PIX - 1) / 2, (N_PIX - 1) / 2))
        if not crack:
            kw.update(n_crack=0)
        if not decay:
            kw.update(decay=())
        sc = make_scene(**kw)
        z = run_zero(sc)["cons"]
        c = run_consensus(sc)
        cs = width_stats(c["w_est"], sc["widths"])
        out[name] = {"z": z, "c": c, "cs": cs}
        lab = tuple("○" if v else "×" for v in (ecc, crack, decay))
        rows.append([name, lab[0], lab[1], lab[2], "%d / %d" % (z["exact"], N_SECT),
                     "%.1f" % z["false"], str(z["false_max"]), str(c["n_est"]),
                     "%.1f" % c["false"], "%.3f" % cs["corr"]])
        print("    %s     %s      %s        %2d / %d / %4.1f / %d"
              "                      %3d / %.1f / %.3f"
              % (lab[0], lab[1], lab[2], z["exact"], N_SECT, z["false"], z["false_max"],
                 c["n_est"], c["false"], cs["corr"]))
    a = out["全部あり"]["z"]
    print("\n  ★ゼロ点で年数が合う方向(24 中): 全部あり %d / 偏心なし %d / 割れ目なし %d / "
          "腐朽なし %d / 全部なし %d。" % (a["exact"], out["偏心なし"]["z"]["exact"],
                                          out["割れ目なし"]["z"]["exact"],
                                          out["腐朽なし"]["z"]["exact"],
                                          out["全部なし"]["z"]["exact"]))
    print("     合意法はどの条件でも年数 %d・偽輪 %.1f。" % (
        out["全部あり"]["c"]["n_est"], max(v["c"]["false"] for v in out.values())))
    figs.save_table("controls",
                    ["条件", "偏心", "割れ目", "腐朽", "ゼロ点 合う方向", "偽輪 中央値",
                     "最悪", "合意法 年数", "偽輪", "幅の相関"], rows,
                    title="対照群(真値 %d 年、ゼロ点は 24 方向)" % N_RINGS)
    return out


# --------------------------------------------------------------------------- #
# 8. 道具の穴                                                                    #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)
    # (a) 極座標展開: 進化 op は中心固定、台帳 polar_unwrap は中心を渡せる
    assert hasattr(fs.ledger, "polar_unwrap") and not hasattr(fs, "polar_unwrap")
    print("  (a) 進化 op の polar_trans_image は中心が画像中心に固定で髄中心に"
          "取れない。台帳の polar_unwrap は center を渡せるが 1 行ファサードには"
          "出ていない(3-D 台帳 curvilinear に居る)。")
    # (b) 1-D 測定は在る(measure_pos)が、放射線の束を一度に置く口が無い
    assert hasattr(fs.ledger, "gen_measure_rectangle2") and hasattr(fs.ledger, "measure_pos")
    print("  (b) measure_pos は 1 本ずつ。扇形 %d 本ぶんを for で回した。"
          "測定線の束(放射・平行)を 1 口で置き、結果を表で返す op があると年輪・"
          "歯車・ラベルの検査が同じ形になる。" % N_SECT)
    # (c) 多方向の合意(境界の対応づけ + 中央値)は自前
    assert not hasattr(fs, "ring_consensus") and not hasattr(fs.ledger, "ring_consensus")
    print("  (c) 方向ごとの境界列を対応づけて中央値で 1 本にする処理は自前"
          "(match_ray / consensus)。欠落と偽輪を分けて数える評価器も自前。")
    # (d) find_peaks に prominence が無い(ゼロ点の偽輪の多くは低い山)
    assert not hasattr(fs, "find_peaks_prominence")
    print("  (d) fs.find_peaks は height / distance だけで prominence を渡せない。"
          "木目の低い山を落とすつまみが無いので、ゼロ点は素の scipy より不利。")

    # (e) measure_pos の amplitude は木目で勾配が単調でなくなると段の途中で止まる
    sc = make_scene()
    ps = polar_stack(sc["img"], sc["pith"])
    fil = ps["fil"]
    nr = fil.shape[1]
    row_c = float(sector_row(0))
    m = fs.ledger.gen_measure_rectangle2(row_c, (nr - 1) / 2.0, 0.0, (nr - 1) / 2.0,
                                         MEAS_ROWS, fil.shape)
    edges = fs.ledger.measure_pos(fil, m, sigma=SIG_M * OVS, threshold=0.0,
                                  transition="positive")
    r0 = int(round(row_c)) - MEAS_ROWS // 2
    sm = np.asarray(fs.smooth_funct_1d_gauss(fil[r0:r0 + MEAS_ROWS].mean(axis=0),
                                             SIG_M * OVS))
    under, total = 0, 0
    for e in edges:
        i = int(round(e["pos"]))
        lo, hi = max(0, i - 3 * OVS), min(nr, i + 3 * OVS + 1)
        rise = float(sm[lo:hi].max() - sm[lo:hi].min())
        if rise >= 0.10:
            total += 1
            if e["amplitude"] < 0.5 * rise:
                under += 1
    assert total > 0
    print("  (e) 疑って数えたが穴ではなかった: measure_pos の amplitude(勾配ローブの"
          "両端差)が実際の段の半分未満に出るのは、±3 px で %.2f 以上上がる段 %d 本のうち "
          "%d 本(1 px 刻みで試作していた時は木目で途中で切れて見えたが、半径方向を "
          "%d 倍に細かく取ると再現しない)。" % (0.10, total, under, OVS))


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("年輪を数えて幅の時系列を取り出す —— 年数の誤差と幅の相関は別の量")
    print("%d x %d px / %d 年 / 幅 %.0f〜%.0f px / ぼけ σ %.1f / 雑音 σ %.2f"
          % (N_PIX, N_PIX, N_RINGS, W_LO, W_HI, BLUR, NOISE))
    print("=" * 78)

    b = section_baseline()
    th = section_thin_ring()
    pe = section_pith_error()
    cr = section_cracks()
    bl = section_blur()
    ct = section_controls()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * ゼロ点(1 本の放射線)は 24 方向中 %d 方向で年数が合う。合わない %d 方向でも"
          "幅の相関は中央値 %.3f —— 年数と幅の相関は別に数える。"
          % (b["z24"]["exact"], b["wrong_n"], b["wrong_med"]))
    print("  * 合意法は年数 %d、欠落 %d、偽輪 %.1f、幅の相関 %.3f、平均誤差 %.2f px。"
          % (b["c"]["n_est"], len(b["c"]["missing"]), b["c"]["false"], b["cs"]["corr"],
             b["cs"]["mae"]))
    print("  * 細い年輪の崖: 合意法 %.1f px(モデル予測 %.1f)、ゼロ点 %.1f px(予測 %.1f)。"
          % (th["c_cliff"], th["pred_c"], th["z_cliff"], th["pred_z"]))
    print("  * 髄の誤差 %.0f px で幅の相関 %.3f、年数 %d(到達不能 予測 %d / 実測 %d)。"
          "cos で変調されるのは半径(傾き %+.1f px)で幅(%+.2f px)ではない。"
          % (pe["d"][-1], pe["corr"][-1], pe["n_est"][-1], pe["lost_pred"][-1],
             pe["lost_meas"][-1], pe["slope_r"], pe["slope_w"]))
    print("  * 割れ目 %d 本でゼロ点の年数が合う方向 %d → %d、偽輪の中央値 %.1f → %.1f"
          "(最悪 %d)。合意法は偽輪 %.1f。"
          % (cr["n"][-1], cr["z_ok"][0], cr["z_ok"][-1], cr["z_med"][0], cr["z_med"][-1],
             cr["z_max"][-1], cr["c_false"][-1]))
    print("  * ぼけ σ %.1f px で合意法の欠落 %d 年(モデル予測 %d)、σ %.1f px で %d 年"
          "(予測 %d)。" % (bl["sig"][2], bl["c_miss"][2], bl["pred_c"][2],
                            bl["sig"][-1], bl["c_miss"][-1], bl["pred_c"][-1]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    # --- 所見を固定する(壊れたら鳴る) ------------------------------------ #
    assert b["c"]["n_est"] == N_RINGS and not b["c"]["missing"], b["c"]["n_est"]
    assert b["cs"]["corr"] > 0.99 and b["cs"]["mae"] < 0.25, (b["cs"]["corr"], b["cs"]["mae"])
    assert b["z24"]["exact"] < N_SECT and b["wrong_n"] >= 3, b["z24"]["exact"]
    assert b["wrong_med"] > 0.85, b["wrong_med"]             # 年数を間違えても幅は合う
    assert th["c_cliff"] is not None and 2.0 <= th["c_cliff"] <= 3.0, th["c_cliff"]
    assert th["z_cliff"] is not None and th["z_cliff"] >= th["c_cliff"], th["z_cliff"]
    assert pe["corr"][-1] > 0.98, pe["corr"][-1]             # 髄 20 px ずれても幅は歪まない
    assert pe["lost_meas"][-1] == pe["lost_pred"][-1] == 2, (pe["lost_pred"], pe["lost_meas"])
    assert abs(pe["slope_r"] + 15.0) < 1.5 and abs(pe["slope_w"]) < 0.3, (pe["slope_r"], pe["slope_w"])
    assert max(cr["c_false"]) == 0.0, cr["c_false"]           # 割れ目 16 本でも合意法は偽輪 0
    assert bl["c_miss"][0] == 0 and bl["c_miss"][-1] == N_RINGS, bl["c_miss"]
    assert bl["z_false"][-1] > bl["z_false"][0] + 5, bl["z_false"]
    assert all(v["c"]["n_est"] == N_RINGS for v in ct.values())

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    sys.exit(main())
