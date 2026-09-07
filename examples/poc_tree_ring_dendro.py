# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""年輪を数えて幅の時系列を取り出す —— 年数の誤差と幅の相関は別の量。

樹木の円板(横断面)の画像から**年輪を数え**(年数)、**各年の幅**(気候の代理記録)
を取り出す仕事です。年輪年代学では年数が 1 年ずれると年代照合が丸ごと外れ、
幅系列の相関が落ちると気候復元が効かなくなる —— この 2 つは**別の壊れ方**で、
別に数えないと「合っている」と言えません。

EXTEND: 実写に差し替えるなら :func:`make_scene` が返る辞書の ``img`` を円板の
撮影画像に、``ring``(画素ごとの年番号の真値地図)を人手の境界トレースから
作った年番号地図に、``widths`` をその平均幅に置き換えます。**髄の位置**は
:data:`PITH` の代わりに実測値を渡してください(髄推定の誤差がどう効くかは
6 節で測ってあります)。円板の外縁(樹皮との境)は既知として扱っています。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. ★**ゼロ点(髄から 1 本の放射線の輝度ピーク数)は年数を 41 年と数える**
   (真値 40)。欠落 0 / 偽輪 1。24 方向で振ると当たるのは 24 本中 3 本。
   ★ただし幅系列の相関は 0.980 —— **年数を間違えても幅の相関は高い**。
   相関は「隣り合う境界の間隔」だけで決まるので、偽輪が 1 本入っても
   残りの 39 本は合っている。年数と幅の相関は別に数える理由がここにある。
2. **極座標展開(髄中心、`polar_unwrap`)+ θ 方向メディアン(`median_rect` 9x3)
   + 24 扇形ごとの測定線(`measure_pos`、正極性)の合意(中央値)で 40 年
   ちょうど**、欠落 0 / 偽輪 0(24 扇形の中央値)、幅の相関 0.997、
   幅の平均誤差 0.09 px。
3. **最も細い年輪の崖**: 1 本の年輪の幅を 4 → 1 px と細めると、合意法は
   **2.5 px** で落とし、ゼロ点は 3.0 px で落とす。予測は「2 つの段が
   分離できる条件 w > 2·σ_tot(σ_tot = sqrt(ぼけ² + 平滑化²) = 1.28 px)
   = 2.56 px」で、合意法の実測と一致。ゼロ点はメディアンの補助が無く、
   より早く(太いうちに)落ちる。
4. ★**髄の推定誤差 0 → 20 px は幅系列をほとんど歪めない**。予想は「偏心は幅
   を cos で変調する」だったが、**cos で変調されるのは半径であって幅ではない**
   (幅は半径の差なので 1 次の項が打ち消す)。偏心無しの対照円板で d=15 px の
   とき、外周半径の cos 回帰の傾きは -15.5 px(予測 -15)、幅の傾きは
   -0.04 px(予測 0)。効くのは**髄の近く**: 半径が d より小さい年輪は
   ずれた中心からの放射線が届かず、幅の相関はまだ 0.994 なのに年数が
   1 年減る —— 数え落としは幾何で予測できる(20 px で予測 3 年、実測 3 年)。
5. **割れ目(放射方向の暗い線、うねりつき)**: ゼロ点は割れ目 2 本で
   24 方向中最悪の放射線に 5 本の偽輪が出て、割れ目 16 本ではどの方向でも
   偽輪が増える(24 方向の中央値 1.0 → 2.5)。★合意法は 16 本でも偽輪 0
   —— θ 方向メディアン(9 行 = 9°)が割れ目の θ 幅より広い限り消える。
   割れ目が放射方向に沿うので、放射線に沿った測定はそれと**並走**する
   ことになり、割れ目のうねりが線を横切るたびに段が出る。
6. **撮像ぼけ σ 0.5 → 4 px で晩材の縁が消える点**: 合意法の欠落は
   0 / 0 / 0 / 1 / 7 / 15 年で、予測(幅 < 2σ_tot の年輪の数)は
   0 / 0 / 0 / 1 / 7 / 15 年 —— 一致。細い年輪から順に消える。
7. **対照群 2×2**(偏心・うねり ×/○ と 割れ目・腐朽 ×/○): ゼロ点の
   偽輪は割れ目・腐朽を止めるだけで 1 → 0 になる。合意法は 4 条件すべてで
   40 年・偽輪 0。**ゼロ点を壊していたのは偏心ではなく割れ目・木目**。

【グラウンドトゥルース】
年輪の幅系列は**閉形式で仕込む**(AR(1) の気候信号 + 周期 11.3 年の成分、
対数正規で 3〜10 px に切り詰め)。年輪境界の半径は「累積幅 × 偏心成長の係数
(1 + 0.20 cos θ)+ 周方向のうねり(3 次・5 次)」、年輪内の明暗は
早材 0.80 から晩材 0.35 へ t^2.5 で暗くなる閉形式のプロファイル。
髄は画像中心から (-13.5, +18.5) px ずらしてある。割れ目・腐朽の暗斑・木目・
ぼけ・雑音を上に載せる。画素ごとの年番号地図を真値として持つので、
**どの中心からどの方向に測っても、その放射線が実際に横切る境界**が真値
になる(ずれた中心では髄近くの年輪に届かない —— それも真値側で数える)。

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
THR = 0.08                       # 段の高さ(±2 px の上がり)のしきい値(輝度単位)
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
    rho = np.arange(0.0, 0.75 * N_PIX, RAY_STEP)
    y = np.clip(np.round(center[0] + rho * np.sin(theta)).astype(int), 0, N_PIX - 1)
    x = np.clip(np.round(center[1] + rho * np.cos(theta)).astype(int), 0, N_PIX - 1)
    k = ring[y, x]
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
        # ★px へ戻す外縁半径は**測った行**のもの。扇形 15° 全体の中央値を使うと
        #   偏心成長で外縁が扇形の中で 10 px 以上動くので外側の年輪が全部ずれる
        #   (最初そう書いて年輪 18〜35 を丸ごと落とした)。
        rd = float(np.median(r_disc[max(0, r0):r0 + MEAS_ROWS]))
        pos = []
        for e in edges:
            i = int(round(e["pos"]))
            rise = sm[min(nr - 1, i + 2 * OVS)] - sm[max(0, i - 2 * OVS)]
            if rise >= thr:
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
    widths = {}
    for i in range(pos.size - 1):
        if ks[i + 1] == ks[i] + 1 and np.isfinite(hit[i]) and np.isfinite(hit[i + 1]):
            widths[int(ks[i + 1])] = (float(hit[i + 1] - hit[i]), float(pos[i + 1] - pos[i]))
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
    assert float(ps["r_disc"].max()) < ps["avail"] - 2, (ps["r_disc"].max(), ps["avail"])
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

    # 合意法
    c = run_consensus(sc)
    cs = width_stats(c["w_est"], w)
    print("\n  合意法: 年数 %d(真値 %d)、欠落 %d 年、偽輪の中央値 %.1f、"
          "年数が合う扇形 %d / %d" % (c["n_est"], sc["n"], len(c["missing"]), c["false"],
                                   c["exact"], N_SECT))
    print("     幅の相関 %.3f(%d 年)、平均誤差 %.2f px、尺度 %.3f(θ 平均の真値に対して)"
          % (cs["corr"], cs["n"], cs["mae"], cs["scale"]))
    print("  ★ゼロ点は年数を %+d 年間違えても幅の相関は %.3f。"
          "年数の誤差と幅の相関は別の量。" % (z0["n_det"] - z0["n_true"], zs["corr"]))

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
            j = int(round(p))
            if 0 <= j < rgb.shape[1]:
                rgb[row - 6:row - 2, max(0, j - 1):j + 2] = (0.1, 0.3, 1.0)
        for p in c["dets"][s]:
            j = int(round(p))
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
    return {"sc": sc, "z0": z0, "zs": zs, "z24": zc, "c": c, "cs": cs}


# --------------------------------------------------------------------------- #
# 3. 最も細い年輪の崖                                                            #
# --------------------------------------------------------------------------- #
def section_thin_ring() -> dict:
    print("\n" + "=" * 78)
    print("3) 最も細い年輪の崖 —— 年輪 %d の幅を 4 → 1 px に細める" % K_THIN)
    print("=" * 78)
    sig_tot = float(np.hypot(BLUR, SIG_M))
    pred = 2.0 * sig_tot
    print("  予測: 2 つの段が分離できる条件 w > 2σ_tot、σ_tot = sqrt(%.1f² + %.1f²) = %.2f px"
          " → 崖 %.2f px" % (BLUR, SIG_M, sig_tot, pred))
    print("\n   幅 [px]   ゼロ点(θ=0): 年数 / 年輪 %d   合意法: 年数 / 年輪 %d / 欠落"
          % (K_THIN, K_THIN))
    base = make_widths()
    rows, thin_w, z_found, c_found = [], [], [], []
    for wt in (4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0):
        w = base.copy()
        w[K_THIN - 1] = wt
        sc = make_scene(widths=w)
        z = run_zero(sc, thetas=[0.0])["per"][0]
        zf = K_THIN not in z["missed"] and K_THIN in [int(k) for k in
                                                     ray_truth(sc, sc["pith"], 0.0)["k"]]
        c = run_consensus(sc)
        cf = K_THIN not in c["missing"]
        thin_w.append(wt)
        z_found.append(zf)
        c_found.append(cf)
        rows.append(["%.1f" % wt, str(z["n_det"]), "○" if zf else "×",
                     str(c["n_est"]), "○" if cf else "×", str(len(c["missing"]))])
        print("   %5.1f       %3d / %s                 %3d / %s / %d"
              % (wt, z["n_det"], "○" if zf else "×", c["n_est"], "○" if cf else "×",
                 len(c["missing"])))
    z_cliff = next((wt for wt, f in zip(thin_w, z_found) if not f), None)
    c_cliff = next((wt for wt, f in zip(thin_w, c_found) if not f), None)
    print("\n  ★合意法が落とし始める幅 %.1f px(予測 %.2f px)、ゼロ点は %.1f px。"
          % (c_cliff, pred, z_cliff))
    print("     合意法は θ 方向メディアンが雑音を先に落とすので、境界の分離条件"
          "そのものまで粘る。ゼロ点は雑音の中で 2 つの段を分けられず早く落ちる。")
    figs.save_table("cliff_thin_ring",
                    ["幅 px", "ゼロ点 年数", "年輪 %d" % K_THIN, "合意法 年数",
                     "年輪 %d" % K_THIN, "欠落"],
                    rows, title="最も細い年輪の崖(予測 2σ_tot = %.2f px)" % pred)
    return {"pred": pred, "z_cliff": z_cliff, "c_cliff": c_cliff}


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
    print("   本数   ゼロ点 24 方向: 偽輪の中央値 / 最悪 / 年数が合う方向   合意法: 年数 / 偽輪")
    ns, z_med, z_max, c_false = [], [], [], []
    for nc in (0, 2, 4, 8, 16):
        sc = make_scene(n_crack=nc)
        z = run_zero(sc)["cons"]
        c = run_consensus(sc)
        ns.append(nc)
        z_med.append(z["false"])
        z_max.append(z["false_max"])
        c_false.append(c["false"])
        print("   %3d          %4.1f / %2d / %2d                          %3d / %.1f"
              % (nc, z["false"], z["false_max"], z["exact"], c["n_est"], c["false"]))
    print("\n  ★ゼロ点は割れ目 %d 本で最悪の方向に偽輪 %d 本、%d 本で中央値 %.1f。"
          "合意法は %d 本でも偽輪 %.1f。" % (ns[1], z_max[1], ns[-1], z_med[-1],
                                            ns[-1], c_false[-1]))
    print("     放射方向の割れ目は放射線と**並走**するので、うねりが線を横切るたびに"
          "段が出る。展開図では横線なので θ 方向メディアンが消す。")
    figs.save_plot("cliff_cracks",
                   [("ゼロ点 偽輪の中央値(24 方向)", ns, z_med),
                    ("ゼロ点 偽輪の最悪", ns, z_max),
                    ("合意法 偽輪", ns, c_false)],
                   xlabel="割れ目の本数", ylabel="偽輪 [年]",
                   title="割れ目が増えるとゼロ点は偽輪を数える")
    return {"n": ns, "z_med": z_med, "z_max": z_max, "c_false": c_false}


# --------------------------------------------------------------------------- #
# 6. 撮像ぼけ                                                                    #
# --------------------------------------------------------------------------- #
def section_blur() -> dict:
    print("\n" + "=" * 78)
    print("6) 撮像ぼけ σ 0.5 → 4 px —— 晩材の縁が消える点")
    print("=" * 78)
    print("   σ [px]   合意法: 年数 / 欠落   ゼロ点(θ=0): 年数 / 欠落   予測(幅 < 2σ_tot の年輪)")
    sig, c_miss, z_miss, pred = [], [], [], []
    w = make_widths()
    for b in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
        sc = make_scene(blur=b)
        c = run_consensus(sc)
        z = run_zero(sc, thetas=[0.0])["per"][0]
        p = int(np.sum(w < 2.0 * np.hypot(b, SIG_M)))
        sig.append(b)
        c_miss.append(len(c["missing"]))
        z_miss.append(len(z["missed"]))
        pred.append(p)
        print("   %4.1f        %3d / %2d               %3d / %2d                 %2d"
              % (b, c["n_est"], len(c["missing"]), z["n_det"], len(z["missed"]), p))
    print("\n  ★合意法の欠落 %s、予測 %s。" % (" / ".join(str(v) for v in c_miss),
                                              " / ".join(str(v) for v in pred)))
    figs.save_plot("cliff_blur",
                   [("合意法 欠落", sig, c_miss), ("ゼロ点 欠落", sig, z_miss),
                    ("予測 幅 < 2σ_tot", sig, pred)],
                   xlabel="撮像ぼけ σ [px]", ylabel="欠落 [年]",
                   title="ぼけると細い年輪から順に消える")
    return {"sig": sig, "c_miss": c_miss, "z_miss": z_miss, "pred": pred}


# --------------------------------------------------------------------------- #
# 7. 対照群 2×2                                                                  #
# --------------------------------------------------------------------------- #
def section_controls() -> dict:
    print("\n" + "=" * 78)
    print("7) 対照群 2×2 —— 偏心・うねり と 割れ目・腐朽 を別々に止める")
    print("=" * 78)
    print("   偏心   割れ目   ゼロ点(θ=0): 年数 / 欠落 / 偽輪 / 相関    合意法: 年数 / 偽輪 / 相関")
    rows, out = [], {}
    for ecc in (True, False):
        for crack in (True, False):
            kw = {}
            if not ecc:
                kw.update(e_growth=0.0, wobble=(), pith=((N_PIX - 1) / 2, (N_PIX - 1) / 2))
            if not crack:
                kw.update(n_crack=0, decay=())
            sc = make_scene(**kw)
            z = run_zero(sc, thetas=[0.0])["per"][0]
            zw = np.full(sc["n"], np.nan)
            zt = np.full(sc["n"], np.nan)
            for k, (e, t) in z["widths"].items():
                zw[k - 1], zt[k - 1] = e, t
            zs = width_stats(zw, zt)
            c = run_consensus(sc)
            cs = width_stats(c["w_est"], sc["widths"])
            key = (ecc, crack)
            out[key] = {"z": z, "zs": zs, "c": c, "cs": cs}
            lab = ("○" if ecc else "×", "○" if crack else "×")
            rows.append([lab[0], lab[1], str(z["n_det"]), str(len(z["missed"])),
                         str(z["false"]), "%.3f" % zs["corr"], str(c["n_est"]),
                         "%.1f" % c["false"], "%.3f" % cs["corr"]])
            print("    %s       %s        %3d / %d / %d / %.3f              %3d / %.1f / %.3f"
                  % (lab[0], lab[1], z["n_det"], len(z["missed"]), z["false"], zs["corr"],
                     c["n_est"], c["false"], cs["corr"]))
    a, b = out[(True, True)]["z"], out[(True, False)]["z"]
    print("\n  ★ゼロ点の偽輪は割れ目・腐朽を止めるだけで %d → %d。偏心を止めても %d → %d。"
          % (a["false"], b["false"], a["false"], out[(False, True)]["z"]["false"]))
    figs.save_table("controls",
                    ["偏心", "割れ目", "ゼロ点 年数", "欠落", "偽輪", "相関",
                     "合意法 年数", "偽輪", "相関"], rows,
                    title="対照群 2×2(真値 %d 年)" % N_RINGS)
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
    print("  * ゼロ点は年数 %d(真値 %d、偽輪 %d)でも幅の相関 %.3f —— 年数と幅の相関は"
          "別に数える。" % (b["z0"]["n_det"], N_RINGS, b["z0"]["false"], b["zs"]["corr"]))
    print("  * 合意法は年数 %d、欠落 %d、偽輪 %.1f、幅の相関 %.3f、平均誤差 %.2f px。"
          % (b["c"]["n_est"], len(b["c"]["missing"]), b["c"]["false"], b["cs"]["corr"],
             b["cs"]["mae"]))
    print("  * 細い年輪の崖: 合意法 %.1f px(予測 %.2f)、ゼロ点 %.1f px。"
          % (th["c_cliff"], th["pred"], th["z_cliff"]))
    print("  * 髄の誤差 %.0f px で幅の相関 %.3f、年数 %d(到達不能 予測 %d / 実測 %d)。"
          "cos で変調されるのは半径(傾き %+.1f px)で幅(%+.2f px)ではない。"
          % (pe["d"][-1], pe["corr"][-1], pe["n_est"][-1], pe["lost_pred"][-1],
             pe["lost_meas"][-1], pe["slope_r"], pe["slope_w"]))
    print("  * 割れ目 %d 本でゼロ点の偽輪は中央値 %.1f(最悪 %d)、合意法 %.1f。"
          % (cr["n"][-1], cr["z_med"][-1], cr["z_max"][-1], cr["c_false"][-1]))
    print("  * ぼけ σ %.1f px で合意法の欠落 %d 年(予測 %d)。"
          % (bl["sig"][-1], bl["c_miss"][-1], bl["pred"][-1]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    sys.exit(main())
