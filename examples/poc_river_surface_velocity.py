# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""河川表面流速を斜め動画から測る(LSPIV)—— 速度の誤差と流量の誤差は別に数える。

    py -3.11 examples/poc_river_surface_velocity.py

岸に据えた監視カメラが川面を斜めに撮り、泡や浮遊物(トレーサ)の動きを窓ごとの
相互相関(PIV)で追って表面流速 u(y) を出し、既知の水深で流量 Q = h ∫u dy まで出す
—— LSPIV(Large-Scale Particle Image Velocimetry)の仕事です。**真値は川幅方向の
流速分布 u(y)**(岸で 0・最大 1.5 m/s のべき乗則)と、そこから閉形式で出る流量。

EXTEND: 実写に差し替えるなら :func:`build_frames` が返す辞書の ``obl``(斜め画像列)
を実動画に、:data:`H_TRUE` を地上基準点(GCP)4 点以上から解いたホモグラフィに、
:func:`profile` を ADCP や浮子で測った断面流速に置き換えます。**斜め画像そのものが
要ります** —— 正射化済みの動画だけでは、この PoC の主張の半分(ゼロ点がどこで
どれだけ外れるか、遠岸の解像度が正射化では戻らないこと)が測れません。
反射(空の映り込み)を消す時間中央値は、**カメラが固定**であることが前提です。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. ★★**ゼロ点(斜め画像のまま相関し、画像中央の 1 尺度で m/s に直す)は
   近岸で速く・遠岸で遅く出る**。窓ごとの速度誤差は近岸 +0.386 / 遠岸
   -0.401 m/s(RMS 0.351 m/s)。**流量は -14.3 %** —— 速度の誤差(符号が岸で
   逆)が積分で一部打ち消し、しかも**見かけの川幅が 5.1 m(真値 8 m)**なので、
   速度が合っている行も幅で外れる。速度の誤差と流量の誤差は別々に数えないと
   「速度は ±0.4 m/s 外れるのに流量は -14 %」の内訳が見えない。
2. ★**行ごとの尺度だけ直して歪めない中間案は、速度 RMS 0.103 m/s・流量
   -1.7 %** まで戻る。残るのは窓の足跡が台形で、窓の中で尺度が変わること。
3. **正射化してから PIV** すると速度 RMS 0.039 m/s・流量 -1.1 %。理想の
   真上カメラ(同じ画素で撮った対照群)は 0.010 m/s・流量 -1.1 %。★正射化で
   **遠岸の誤差は戻らない**(遠岸 RMS 0.070 / 近岸 0.029 m/s、理想は 0.010
   / 0.010)—— 遠岸の 1 画素は世界で 4.5 cm(近岸 1.9 cm)で、失った解像度は
   ワープでは作れない。**流量が理想と同じ -1.1 % なのは流量が幅の積分で
   遠岸の誤差が薄まるから**であって、速度が合っているからではない。
4. ★★**トレーサ密度の崖は「峰が立たない」ではなく「外れ値になる」**。密度
   0.05 % で 1 対あたりの nan は 0.0 % なのに外れ値検定の旗が 46.6 %。
   窓 32 px に粒子 0.5 個では相関は必ず**何かの**峰を返す —— 黙って外れる。
   20 対の平均でも RMS 0.30 px、アンサンブル相関(相関面を足す)なら
   0.06 px。密度 0.5 % 以上では 3 者とも 0.05 px 以下で差が消える。
5. ★**窓を広げると岸の勾配がなまる量は「窓の中の平均」で予測できる**。
   岸 1 m 以内の偏りは窓 16 → 64 px で -0.008 → -0.041 m/s、窓平均の予測は
   -0.006 → -0.045 m/s(相関 0.998)。予想していた「窓幅 × 勾配」の 1 次項は
   窓の左右で打ち消して 0 になり、効くのは **2 次項(窓² × 曲率 / 24)**。
6. ★★**反射(動かない模様)は流速を「なだらかに」ではなく「二段階で」ゼロへ
   引く**。コントラスト 0.10 で中央の速度比は 0.99、0.20 で 0.77、0.30 で
   0.26、0.60 で 0.00。内訳を数えると、部分的に引かれる窓(0.3〜1.9 px)は
   0.20 で 25 %・0.30 で 31 %、ゼロに張り付く窓は 0.20 で 22 %・0.30 で 66 %
   —— 静止ピークと移動ピークが**どちらか勝つ**ので、平均は 2 峰の混合比
   だった。★時間中央値(固定カメラの背景)を引くと 0.60 でも比 0.999。
   アンサンブル相関は静止ピークも一緒に積み上がるので**効かない**(0.30 で
   比 0.00、生の 0.26 より悪い)。
7. ★**dt を伸ばす崖は「1/4 則」の壁で、物理より先に来る**。1 コマ 2.5 px の
   中央部は k=4 コマ(10 px)で探索上限 8 px を超え、外れ窓の割合は
   k=3 で 2.6 % → k=4 で 46.8 % → k=5 で 58.2 %(予測: 真値が 8 px を超える
   窓の割合 0.0 / 42.9 / 55.4 %)。探索上限を外し補正も切った「物理だけ」の
   相関は k=5 でも 4.3 % しか外れず、k=8(20 px、窓の 5/8)で 30.0 %。
   **崖は道具の設定が作っていた**。ただし遅い岸の窓は k=8 でも生きている
   ので、崖は行ごとに来る。
8. **対照群(反射なし・波紋なし・雑音なし)**は速度 RMS 0.038 m/s・流量
   -1.1 %。反射 0.15 だけ足すと 0.041 / -1.0 %、波紋だけなら 0.040 /
   -1.1 %、雑音だけなら 0.039 / -1.1 %。★この設定の波紋(振幅 0.12、
   波速 0.35 m/s)は速度を **0.002 m/s** しか動かさない —— 周期模様は窓の
   平均引きと粒子の鋭い峰に負ける。効くのはコントラストが 0.2 を超えた反射
   だけで、**それは崖の向こう側で一気に来る**(6 節)。

【グラウンドトゥルース】
流速分布は閉形式 u(y) = U_max·η^(1/7)、η = 1 − |2y/B − 1|(岸で 0)。流量は
Q = h·U_max·B·7/8 = 12.600 m³/s(h = 1.2 m)。トレーサは連続座標を持つガウス輝点
で、毎コマ u(y)·dt だけ**動かしてから描く**(2 倍解像度で描いて 2×2 平均が
「真上カメラ」、ホモグラフィで逆ワープしたものが「斜めカメラ」)。斜め画像には
固定の反射模様(カメラ座標で静止)、世界座標で波速 0.35 m/s の周期模様、加法
ガウス雑音を**別々に**足すので、対照群はそれぞれを 0 にするだけで作れる。
ホモグラフィは既知(GCP 測量済みという前提)。

来歴(公開文献のみ): Fujita, Muste & Kruger, *J. Hydraul. Res.* 36 (1998) 397
—— LSPIV / Raffel et al., *Particle Image Velocimetry* 3rd ed.(2018)§5.4 の
1/4 則と対の消失 / Westerweel & Scarano, *Exp. Fluids* 39 (2005) 1096 ——
正規化中央値検定 / Hartley & Zisserman, *Multiple View Geometry* §2 ——
平面のホモグラフィ / Meinhart, Wereley & Santiago, *J. Fluids Eng.* 122 (2000)
285 —— アンサンブル相関。
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
import pivops                                                    # noqa: E402  (flow, info) が要る

SEED = 20260907

# --- 川と流れ ---------------------------------------------------------------- #
B_WIDTH = 8.0            # 川幅 [m](y 方向)
L_REACH = 6.4            # 写す区間の長さ [m](x 方向 = 流下方向)
DEPTH = 1.2              # 水深 [m](既知・一様)
U_MAX = 1.5              # 最大表面流速 [m/s]
POWER = 1.0 / 7.0        # べき乗則の指数(対数則風)
Q_TRUE = DEPTH * U_MAX * B_WIDTH * (1.0 / (1.0 + POWER))   # 閉形式 = 12.6 m³/s

# --- 撮像 --------------------------------------------------------------------- #
S_PX = 0.02              # 正射画像の画素 [m/px]
DT = 1.0 / 30.0          # コマ間隔 [s]
N_FRAMES = 60
ORTHO_SHAPE = (int(round(B_WIDTH / S_PX)), int(round(L_REACH / S_PX)))   # (400, 320)
SS = 2                   # 描画の超解像倍率
OBL_SHAPE = (480, 640)   # 斜めカメラの画素
F_PIX = 520.0
CAM = np.array([L_REACH / 2, -6.0, 4.0])      # 近岸の 6 m 手前・高さ 4 m
TGT = np.array([L_REACH / 2, B_WIDTH / 2, 0.0])

# --- トレーサと妨害 ------------------------------------------------------------ #
DENSITY = 0.01           # 粒子 / 正射画素(窓 32 px に 10 個)
DIAM_PX = 3.0            # 粒子像の直径 [px](= 2σ)
BG = 0.05
REFL_C = 0.15            # 反射模様のコントラスト(基準条件)
WAVE_AMP = 0.12          # 波紋の振幅
WAVE_LAMBDA = 0.6        # 波紋の波長 [m]
WAVE_SPEED = 0.35        # 波紋の位相速度 [m/s](流速と違う)
WAVE_THETA = np.deg2rad(25.0)
NOISE = 0.03

WIN = 32
N_PAIRS = 20             # 基準条件で平均する対の数


# --------------------------------------------------------------------------- #
# 真値                                                                          #
# --------------------------------------------------------------------------- #
def profile(y):
    """表面流速 u(y) [m/s]。岸 (y=0, B) で 0。"""
    eta = 1.0 - np.abs(2.0 * np.asarray(y, np.float64) / B_WIDTH - 1.0)
    return U_MAX * np.clip(eta, 0.0, 1.0) ** POWER


def look_at(c, t):
    z = t - c
    z = z / np.linalg.norm(z)
    x = np.cross(z, np.array([0.0, 0.0, 1.0]))
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    return np.stack([x, y, z], axis=0)


_R = look_at(CAM, TGT)
_K = np.array([[F_PIX, 0, OBL_SHAPE[1] / 2.0], [0, F_PIX, OBL_SHAPE[0] / 2.0], [0, 0, 1]])
#: 世界 (X, Y, 1) [m] → 斜め画像 (u, v, 1) [px]。**真値の出どころ**(GCP 測量済み)。
H_TRUE = np.stack([_K @ _R[:, 0], _K @ _R[:, 1], -_K @ _R @ CAM], axis=1)
H_INV = np.linalg.inv(H_TRUE)
#: 正射画素 (col, row) → 世界 (X, Y):X = col·S, Y = row·S
_H_O2I = H_TRUE @ np.diag([S_PX, S_PX, 1.0])                 # 正射 px → 斜め px
_H_HI2I = H_TRUE @ np.diag([S_PX / SS, S_PX / SS, 1.0])      # 超解像 px → 斜め px
_H_I2HI = np.linalg.inv(_H_HI2I)


def img_to_world(u, v):
    p = H_INV @ np.stack([np.ravel(u), np.ravel(v), np.ones(np.size(u))])
    return (p[0] / p[2]).reshape(np.shape(u)), (p[1] / p[2]).reshape(np.shape(u))


def ground_scale(u, v):
    """斜め画像の (u, v) における流下方向の地上分解能 |dX/du| [m/px]。"""
    x0, _ = img_to_world(u, v)
    x1, _ = img_to_world(u + 1.0, v)
    return np.abs(x1 - x0)


# --------------------------------------------------------------------------- #
# 場面の生成                                                                    #
# --------------------------------------------------------------------------- #
def _splat(pos_y, pos_x, amp, shape, sigma):
    """連続座標のガウス輝点を bincount で描く(粒子を動かしてから描く)。"""
    h, w = shape
    r = int(np.ceil(3 * sigma))
    off = np.arange(-r, r + 1)
    cy = np.floor(pos_y).astype(np.int64)
    cx = np.floor(pos_x).astype(np.int64)
    iy = cy[:, None, None] + off[None, :, None]
    ix = cx[:, None, None] + off[None, None, :]
    g = amp[:, None, None] * np.exp(-((iy - pos_y[:, None, None]) ** 2
                                      + (ix - pos_x[:, None, None]) ** 2) / (2 * sigma ** 2))
    ok = (iy >= 0) & (iy < h) & (ix >= 0) & (ix < w)
    idx = (iy * w + ix)[ok]
    return np.bincount(idx, weights=g[ok], minlength=h * w).reshape(h, w)


def _reflection(rng, kind="smooth"):
    """カメラ座標で**動かない**映り込み。零平均・標準偏差 1(コントラスト = 標準偏差)。

    ``"smooth"`` = 空・雲(横に伸びた滑らかな模様、相関長 8〜30 px)。
    ``"fine"`` = 岸の樹木や構造物の映り込み(粒子と同じ 1〜2 px の細かい模様)。
    """
    n = rng.normal(size=OBL_SHAPE)
    if kind == "smooth":
        r = gaussian_filter(n, (8, 30)) + 0.5 * gaussian_filter(n, (3, 12))
    elif kind == "fine":
        r = gaussian_filter(n, 1.2)
    else:
        raise ValueError(kind)
    r = r - r.mean()
    return r / r.std()


def build_frames(density=DENSITY, n_frames=N_FRAMES, refl_c=REFL_C, wave_amp=WAVE_AMP,
                 noise=NOISE, seed=SEED, want_ortho=True, refl_fine_c=0.0):
    """斜め動画(と対照用の真上動画)を作る。返りは辞書。

    ``obl``: 斜めカメラのコマ列 / ``obl_clean``: 反射・雑音を足す前 /
    ``ortho``: 真上カメラ(2×2 平均)のコマ列 / ``truth_px``: 正射画素での
    真の変位 ``(2, H, W)`` [px/コマ]。
    """
    rng = np.random.default_rng(seed)
    hi_shape = (ORTHO_SHAPE[0] * SS, ORTHO_SHAPE[1] * SS)
    n_p = int(round(density * ORTHO_SHAPE[0] * ORTHO_SHAPE[1]))
    y_m = rng.uniform(0.0, B_WIDTH, n_p)
    x0_m = rng.uniform(0.0, L_REACH, n_p)
    amp = rng.uniform(0.6, 1.0, n_p)
    u_p = profile(y_m)
    sigma_hi = DIAM_PX / 2.0 * SS
    refl = _reflection(rng, "smooth")
    refl_fine = _reflection(rng, "fine")
    gy, gx = np.mgrid[0:hi_shape[0], 0:hi_shape[1]].astype(np.float64)
    phase0 = 2 * np.pi * ((gx * S_PX / SS) * np.cos(WAVE_THETA)
                          + (gy * S_PX / SS) * np.sin(WAVE_THETA)) / WAVE_LAMBDA
    obl, obl_clean, ortho = [], [], []
    for k in range(n_frames):
        t = k * DT
        x_m = np.mod(x0_m + u_p * t, L_REACH)          # 周期境界(上流で枯れない)
        hi = _splat(y_m / (S_PX / SS), x_m / (S_PX / SS), amp, hi_shape, sigma_hi) + BG
        if wave_amp > 0:
            hi = hi + wave_amp * np.sin(phase0 - 2 * np.pi * WAVE_SPEED * t / WAVE_LAMBDA)
        if want_ortho:
            o = hi.reshape(ORTHO_SHAPE[0], SS, ORTHO_SHAPE[1], SS).mean(axis=(1, 3))
            ortho.append(o + rng.normal(0.0, noise, o.shape) if noise > 0 else o)
        # 斜めカメラ:画素の足跡ぶん少しぼかしてから逆ワープ(素の標本化は
        # 遠岸で折り返しになる)。fullseye の warp_by_plane は出力 = 入力の形。
        blur = gaussian_filter(hi, 1.5)
        ob = fs.ledger.warp_by_plane(blur, _H_I2HI, order=1, cval=BG)[:OBL_SHAPE[0], :OBL_SHAPE[1]]
        obl_clean.append(ob)
        ob2 = ob + refl_c * refl + refl_fine_c * refl_fine
        if noise > 0:
            ob2 = ob2 + rng.normal(0.0, noise, ob2.shape)
        obl.append(ob2)
    ty = np.zeros(ORTHO_SHAPE)
    tx = profile(np.arange(ORTHO_SHAPE[0])[:, None] * S_PX) * DT / S_PX * np.ones((1, ORTHO_SHAPE[1]))
    return {"obl": obl, "obl_clean": obl_clean, "ortho": ortho, "refl": refl,
            "refl_fine": refl_fine, "truth_px": np.stack([ty, tx])}


def rectify(frame):
    """斜め画像 → 正射画像(既知ホモグラフィで逆ワープ)。"""
    return fs.ledger.warp_by_plane(frame, _H_O2I, order=1, cval=BG)[:ORTHO_SHAPE[0], :ORTHO_SHAPE[1]]


_COVER = None


def coverage():
    """正射画素ごとに「斜めカメラの視野に入っているか」。"""
    global _COVER
    if _COVER is None:
        ones = np.ones(OBL_SHAPE)
        c = fs.ledger.warp_by_plane(ones, _H_O2I, order=1, cval=0.0)[:ORTHO_SHAPE[0], :ORTHO_SHAPE[1]]
        _COVER = c > 0.999
    return _COVER


# --------------------------------------------------------------------------- #
# PIV の共通部品                                                                #
# --------------------------------------------------------------------------- #
def piv_pairs(frames, pairs, window=WIN, drop_outliers=True, **kw):
    """対の列で PIV して平均する。返りは ``(mean_flow, info, per_pair_nan, per_pair_outlier)``。

    ``drop_outliers`` は正規化中央値検定で旗の立った窓を**埋めずに欠測**にしてから平均する
    (現場の標準手順)。崖を「検定に救われずに」数えたいときは False。
    """
    flows, nan_f, out_f = [], [], []
    info = None
    for a, b in pairs:
        flow, info = pivops.piv_cross_correlate(frames[a], frames[b], window=window, **kw)
        nan_f.append(1.0 - info["valid_fraction"])
        mask = fs.ledger.piv_outlier_mask(flow) & np.isfinite(flow[0])
        out_f.append(float(np.mean(mask)))
        flows.append(fs.ledger.piv_replace_outliers(flow, mask, method="nan") if drop_outliers else flow)
    import warnings
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        mean = np.nanmean(np.stack(flows), axis=0)
    return mean, info, float(np.mean(nan_f)), float(np.mean(out_f))


def window_ok(info, window):
    """各窓の足跡が全部カメラの視野内か(正射格子用)。"""
    cov = coverage()
    r = np.rint(info["rows"]).astype(int)
    c = np.rint(info["cols"]).astype(int)
    hw = window // 2
    ok = np.zeros((len(r), len(c)), bool)
    for i, rr in enumerate(r):
        for j, cc in enumerate(c):
            ok[i, j] = cov[max(rr - hw, 0):rr + hw, max(cc - hw, 0):cc + hw].all()
    return ok


def profile_from_flow(flow, info, ok=None):
    """正射格子の流れ → 行ごとの u(y) [m/s]。返りは ``(y [m], u [m/s])``(nan あり)。"""
    vel = fs.ledger.piv_to_velocity(flow, S_PX, DT)
    ux = vel[1].copy()
    if ok is not None:
        ux[~ok] = np.nan
    import warnings
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        u_row = np.nanmean(ux, axis=1)
    return np.asarray(info["rows"]) * S_PX, u_row


def discharge(y, u):
    """Q = h ∫ u dy。岸で u = 0 を境界条件に、欠測行は y で線形補間。"""
    m = np.isfinite(u)
    if m.sum() < 2:
        return np.nan
    yy = np.concatenate([[0.0], y[m], [B_WIDTH]])
    uu = np.concatenate([[0.0], u[m], [0.0]])
    return DEPTH * np.trapezoid(uu, yy)


def speed_err(y, u):
    e = u - profile(y)
    m = np.isfinite(e)
    return float(np.sqrt(np.mean(e[m] ** 2)))


# --------------------------------------------------------------------------- #
# 1. 健全性                                                                     #
# --------------------------------------------------------------------------- #
def section_sanity(sc):
    print("\n" + "=" * 78)
    print("0) 健全性 —— 真値と道具の確認")
    print("=" * 78)
    # ホモグラフィの往復
    u, v = 300.0, 250.0
    X, Y = img_to_world(u, v)
    p = H_TRUE @ np.array([X.item(), Y.item(), 1.0])
    rt = np.hypot(p[0] / p[2] - u, p[1] / p[2] - v)
    print("  ホモグラフィの往復誤差 %.1e px" % rt)
    assert rt < 1e-9
    # 川の四隅が画像に入っているか
    for (X, Y) in [(0, 0), (L_REACH, 0), (0, B_WIDTH), (L_REACH, B_WIDTH)]:
        p = H_TRUE @ np.array([X, Y, 1.0])
        print("  世界 (%.1f, %.1f) m → 画像 (%.0f, %.0f) px" % (X, Y, p[0] / p[2], p[1] / p[2]))
    cov = coverage()
    print("  正射画素のうち視野内 %.1f %%" % (100 * cov.mean()))
    s_near = ground_scale(OBL_SHAPE[1] / 2.0, _v_of(0.3))
    s_far = ground_scale(OBL_SHAPE[1] / 2.0, _v_of(B_WIDTH - 0.3))
    s_mid = ground_scale(OBL_SHAPE[1] / 2.0, OBL_SHAPE[0] / 2.0)
    print("  地上分解能 近岸 %.1f cm/px / 中央 %.1f cm/px / 遠岸 %.1f cm/px"
          % (100 * s_near, 100 * s_mid, 100 * s_far))
    # 真上カメラで PIV → 真値に乗るか
    pairs = [(k, k + 1) for k in range(N_PAIRS)]
    flow, info, _, _ = piv_pairs(sc["ortho"], pairs)
    truth = fs.ledger.piv_sample_at_windows(sc["truth_px"], info)
    st = fs.ledger.piv_error_stats(flow, truth)
    print("  真上カメラ %d 対平均:偏り dx %+.4f px / RMS %.4f px / 中央絶対誤差 %.4f px(最大変位 %.2f px/コマ)"
          % (N_PAIRS, st["bias_dx"], st["rms"], st["median_abs"], sc["truth_px"][1].max()))
    print("  閉形式の流量 Q = %.3f m³/s" % Q_TRUE)
    assert st["median_abs"] < 0.1 and st["rms"] < 0.3
    return {"s_near": s_near, "s_far": s_far, "s_mid": s_mid}


def _v_of(Y, X=L_REACH / 2):
    p = H_TRUE @ np.array([X, Y, 1.0])
    return p[1] / p[2]


# --------------------------------------------------------------------------- #
# 2. ゼロ点 —— 斜め画像のまま相関                                                 #
# --------------------------------------------------------------------------- #
def section_zero_point(sc):
    print("\n" + "=" * 78)
    print("1) ゼロ点 —— 斜め画像のまま PIV、画像中央の 1 尺度で m/s に直す")
    print("=" * 78)
    pairs = [(k, k + 1) for k in range(N_PAIRS)]
    flow, info, _, _ = piv_pairs(sc["obl"], pairs)
    uu, vv = np.meshgrid(info["cols"], info["rows"])
    X, Y = img_to_world(uu, vv)
    # 窓の中心が水面に乗っている窓だけ(現場で水域マスクを引くのと同じ)
    on_water = (Y > 0) & (Y < B_WIDTH) & (X > 0) & (X < L_REACH) & np.isfinite(flow[1])
    speed_px = np.hypot(flow[0], flow[1])
    s0 = ground_scale(OBL_SHAPE[1] / 2.0, OBL_SHAPE[0] / 2.0)
    truth = profile(Y)

    # (a) 1 尺度
    v_naive = speed_px * s0 / DT
    err = np.where(on_water, v_naive - truth, np.nan)
    near = np.nanmean(err[(Y < 2.0) & on_water])
    far = np.nanmean(err[(Y > B_WIDTH - 2.0) & on_water])
    rms = np.sqrt(np.nanmean(err ** 2))
    # 流量:行ごとの平均速度 × 「行間隔 × 1 尺度」
    import warnings
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        row_u = np.nanmean(np.where(on_water, v_naive, np.nan), axis=1)
    rows_ok = np.isfinite(row_u)
    width_app = rows_ok.sum() * info["step"] * s0
    q_naive = DEPTH * np.nansum(row_u) * info["step"] * s0
    print("  画像中央の地上分解能 %.2f cm/px を全画面に当てる" % (100 * s0))
    print("  窓ごとの速度誤差:近岸(2 m 以内)%+.3f / 遠岸(2 m 以内)%+.3f m/s、RMS %.3f m/s"
          % (near, far, rms))
    print("  見かけの川幅 %.1f m(真値 %.1f)→ 流量 %.2f m³/s(%+.1f %%)"
          % (width_app, B_WIDTH, q_naive, 100 * (q_naive / Q_TRUE - 1)))
    assert near > 0.1 and far < -0.1, "近岸は速く・遠岸は遅く出るはず"

    # (b) 行ごとの尺度(歪めない)
    s_row = ground_scale(np.full(vv.shape, OBL_SHAPE[1] / 2.0), vv)
    v_row = speed_px * s_row / DT
    err_b = np.where(on_water, v_row - truth, np.nan)
    rms_b = np.sqrt(np.nanmean(err_b ** 2))
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        row_ub = np.nanmean(np.where(on_water, v_row, np.nan), axis=1)
    _, Yrow = img_to_world(np.full(len(info["rows"]), OBL_SHAPE[1] / 2.0), np.asarray(info["rows"]))
    order = np.argsort(Yrow)
    q_b = discharge(Yrow[order], row_ub[order])
    print("  中間案(行ごとの尺度、歪めない):速度 RMS %.3f m/s / 流量 %.2f m³/s(%+.1f %%)"
          % (rms_b, q_b, 100 * (q_b / Q_TRUE - 1)))
    return {"rms": rms, "near": near, "far": far, "q": q_naive, "width": width_app,
            "rms_b": rms_b, "q_b": q_b, "Y": Y, "v_naive": v_naive, "on_water": on_water,
            "truth": truth, "Yrow": Yrow[order], "row_u": row_u[order], "row_ub": row_ub[order]}


# --------------------------------------------------------------------------- #
# 3. 正射化してから PIV                                                          #
# --------------------------------------------------------------------------- #
def run_rectified(frames, pairs, window=WIN, **kw):
    rec = {}
    for a, b in pairs:
        for k in (a, b):
            if k not in rec:
                rec[k] = rectify(frames[k])
    flow, info, nan_f, out_f = piv_pairs(rec, pairs, window=window, **kw)
    ok = window_ok(info, window)
    y, u = profile_from_flow(flow, info, ok)
    return {"flow": flow, "info": info, "ok": ok, "y": y, "u": u, "nan": nan_f, "out": out_f,
            "rec0": rec[pairs[0][0]]}


def section_rectified(sc, scales):
    print("\n" + "=" * 78)
    print("2) 正射化してから PIV —— 対照群は真上カメラ")
    print("=" * 78)
    pairs = [(k, k + 1) for k in range(N_PAIRS)]
    r = run_rectified(sc["obl"], pairs)
    q_r = discharge(r["y"], r["u"])
    e_r = speed_err(r["y"], r["u"])
    flow_o, info_o, _, _ = piv_pairs(sc["ortho"], pairs)
    y_o, u_o = profile_from_flow(flow_o, info_o)
    q_o = discharge(y_o, u_o)
    e_o = speed_err(y_o, u_o)

    def zone(y, u, lo, hi):
        m = (y > lo) & (y < hi) & np.isfinite(u)
        return float(np.sqrt(np.mean((u[m] - profile(y[m])) ** 2)))
    near_r, far_r = zone(r["y"], r["u"], 0, 2), zone(r["y"], r["u"], B_WIDTH - 2, B_WIDTH)
    near_o, far_o = zone(y_o, u_o, 0, 2), zone(y_o, u_o, B_WIDTH - 2, B_WIDTH)
    print("  正射化 → PIV:速度 RMS %.3f m/s / 流量 %.2f m³/s(%+.1f %%)"
          % (e_r, q_r, 100 * (q_r / Q_TRUE - 1)))
    print("  真上カメラ  :速度 RMS %.3f m/s / 流量 %.2f m³/s(%+.1f %%)"
          % (e_o, q_o, 100 * (q_o / Q_TRUE - 1)))
    print("  岸から 2 m の RMS:正射化 近岸 %.3f / 遠岸 %.3f m/s、真上 近岸 %.3f / 遠岸 %.3f m/s"
          % (near_r, far_r, near_o, far_o))
    print("  遠岸の 1 画素は世界で %.1f cm、近岸は %.1f cm —— 正射化は失った解像度を作れない"
          % (100 * scales["s_far"], 100 * scales["s_near"]))
    print("  視野外の窓 %d / %d" % ((~r["ok"]).sum(), r["ok"].size))
    q_rule = discharge(y_o, profile(y_o))
    print("  ★積分則だけの誤差(真値を窓の行で標本化して岸 0 で台形):%+.2f %% —— 流量の誤差の"
          "うちこの分は速度と無関係" % (100 * (q_rule / Q_TRUE - 1)))
    print("    岸の 1 行目(y = %.2f m)まで u は y^(1/7) で立ち上がるので、台形は %.0f %% 取りこぼす。"
          % (y_o[0], 100 * (1 - 0.5 / (1 / (1 + POWER)))))
    assert far_r > 1.5 * far_o, "遠岸は正射化しても真上カメラより悪いはず"
    assert e_r < 0.1
    return {"rect": r, "q_r": q_r, "e_r": e_r, "y_o": y_o, "u_o": u_o, "q_o": q_o, "e_o": e_o,
            "near_r": near_r, "far_r": far_r, "near_o": near_o, "far_o": far_o, "q_rule": q_rule}


# --------------------------------------------------------------------------- #
# 4. 対照群 —— 妨害を 1 つずつ止める                                               #
# --------------------------------------------------------------------------- #
def section_controls():
    print("\n" + "=" * 78)
    print("3) 対照群 —— 反射・波紋・雑音を 1 つずつ")
    print("=" * 78)
    conds = [("すべて無し(対照群)", dict(refl_c=0, wave_amp=0, noise=0)),
             ("反射(空)だけ", dict(refl_c=REFL_C, wave_amp=0, noise=0)),
             ("反射(細かい)だけ", dict(refl_c=0, refl_fine_c=REFL_C, wave_amp=0, noise=0)),
             ("波紋だけ", dict(refl_c=0, wave_amp=WAVE_AMP, noise=0)),
             ("雑音だけ", dict(refl_c=0, wave_amp=0, noise=NOISE)),
             ("すべて有り(基準)", dict(refl_c=REFL_C, wave_amp=WAVE_AMP, noise=NOISE))]
    pairs = [(k, k + 1) for k in range(10)]
    out = []
    for name, kw in conds:
        sc = build_frames(n_frames=11, want_ortho=False, **kw)
        r = run_rectified(sc["obl"], pairs)
        q = discharge(r["y"], r["u"])
        e = speed_err(r["y"], r["u"])
        out.append((name, e, q))
        print("  %-22s 速度 RMS %.3f m/s / 流量 %+.1f %%" % (name, e, 100 * (q / Q_TRUE - 1)))
    # 波紋の対処:周期模様(波長 30 px)は空間ハイパスで落ちる(粒子 3 px は残る)
    sc = build_frames(n_frames=11, want_ortho=False, **conds[-1][1])
    hp = [fs.apply(f, "highpass_image", a=0.1) for f in sc["obl"]]
    r = run_rectified(hp, pairs)
    q = discharge(r["y"], r["u"])
    e = speed_err(r["y"], r["u"])
    out.append(("基準 + 空間ハイパス", e, q))
    print("  %-22s 速度 RMS %.3f m/s / 流量 %+.1f %%" % (out[-1][0], e, 100 * (q / Q_TRUE - 1)))
    byname = {n: e for n, e, _ in out}
    d_wave = byname["波紋だけ"] - byname["すべて無し(対照群)"]
    print("  波紋(振幅 %.2f・波速 %.2f m/s = %.2f px/コマ)が速度 RMS を動かす量 %+.3f m/s、"
          "ハイパスで基準 %.3f → %.3f m/s" % (WAVE_AMP, WAVE_SPEED, WAVE_SPEED * DT / S_PX, d_wave,
                                              byname["すべて有り(基準)"], byname["基準 + 空間ハイパス"]))
    print("  ★同じコントラスト %.2f でも、空の映り込みは %.3f、細かい映り込みは %.3f m/s(%.0f 倍)。"
          % (REFL_C, byname["反射(空)だけ"], byname["反射(細かい)だけ"],
             byname["反射(細かい)だけ"] / byname["反射(空)だけ"]))
    assert byname["反射(細かい)だけ"] > 10 * byname["反射(空)だけ"]
    assert d_wave > 0.03
    return out


# --------------------------------------------------------------------------- #
# 5. 崖 (a) トレーサ密度                                                          #
# --------------------------------------------------------------------------- #
def section_density():
    print("\n" + "=" * 78)
    print("4) 崖 (a) トレーサ密度 0.05 → 2 % —— 欠測は種類ごとに数える")
    print("=" * 78)
    dens = [0.0005, 0.001, 0.002, 0.005, 0.01, 0.02]
    pairs = [(k, k + 1) for k in range(N_PAIRS)]
    rows = []
    print("  密度 [%]  粒子/窓  nan/対 [%]  外れ値旗/対 [%] | 20 対平均: 外れ窓(>1 px) [%]  中央絶対誤差 [px]  全対欠測の窓 [%]"
          " | アンサンブル: 外れ窓 [%]  中央絶対誤差 [px] | 流量 [%]")
    for d in dens:
        sc = build_frames(density=d, n_frames=N_PAIRS + 1, refl_c=0, wave_amp=0, want_ortho=False)
        r = run_rectified(sc["obl"], pairs)
        truth = fs.ledger.piv_sample_at_windows(sc["truth_px"], r["info"])
        ok = r["ok"]
        e = (r["flow"][1] - truth[1])[ok]
        lost = float(np.mean(~np.isfinite(e)))
        ev = e[np.isfinite(e)]
        bad_avg = float(np.mean(np.abs(ev) > 1.0))
        med_avg = float(np.median(np.abs(ev)))
        rec = [rectify(sc["obl"][k]) for k in range(N_PAIRS + 1)]
        flow_e, _ = pivops.piv_ensemble_correlate(rec, window=WIN)
        e2 = (flow_e[1] - truth[1])[ok]
        e2 = e2[np.isfinite(e2)]
        bad_ens = float(np.mean(np.abs(e2) > 1.0))
        med_ens = float(np.median(np.abs(e2)))
        q = discharge(r["y"], r["u"])
        rows.append((d, r["nan"], r["out"], bad_avg, med_avg, lost, bad_ens, med_ens, 100 * (q / Q_TRUE - 1)))
        print("  %6.2f   %6.1f   %8.1f    %12.1f   | %18.1f  %16.3f  %14.1f | %14.1f  %16.3f | %+6.1f"
              % (100 * d, d * WIN * WIN, 100 * r["nan"], 100 * r["out"], 100 * bad_avg, med_avg, 100 * lost,
                 100 * bad_ens, med_ens, 100 * (q / Q_TRUE - 1)))
    r0 = rows[0]
    print("  密度 %.2f %%(窓 32 px に粒子 %.1f 個):nan %.1f %% なのに外れ値旗 %.1f %% —— "
          "峰は**必ず**立つ、黙って外れる" % (100 * r0[0], r0[0] * WIN * WIN, 100 * r0[1], 100 * r0[2]))
    print("  ★予想は「アンサンブル相関が薄い密度を救う」だったが、外れ窓の割合は %.0f %% → %.0f %% と"
          "救わず、典型窓(中央絶対誤差)だけ %.3f → %.3f px と良くなる。" % (100 * r0[3], 100 * r0[6], r0[4], r0[7]))
    print("  外れ窓は「粒子が一度も通らない窓」で、相関面を何枚足しても真の峰は積み上がらない。")
    assert rows[0][2] > 0.2 and rows[0][1] < 0.05
    assert rows[0][3] > 0.2 and rows[-1][3] < 0.02
    return rows


# --------------------------------------------------------------------------- #
# 6. 崖 (b) 問い合わせ窓 —— 岸の勾配がなまる                                        #
# --------------------------------------------------------------------------- #
def section_window():
    print("\n" + "=" * 78)
    print("5) 崖 (b) 窓 16 → 64 px —— 岸の勾配がなまる量を窓平均で予測する")
    print("=" * 78)
    sc = build_frames(density=0.02, n_frames=11, refl_c=0, wave_amp=0, noise=0.0)
    pairs = [(k, k + 1) for k in range(10)]
    rows = []
    print("  窓 [px]  岸 1 m 以内の偏り 実測 / 窓平均の予測 [m/s]  岸に最も近い行 実測 / 予測 [m/s]  "
          "「窓幅×勾配」 [m/s]  未測定の岸帯 [m]  流量 実測 / 積分則だけ [%]")
    for w in (16, 24, 32, 48, 64):
        flow, info, _, _ = piv_pairs(sc["ortho"], pairs, window=w)
        y, u = profile_from_flow(flow, info)
        # 予測:窓の中の真値の Hann 重み平均 − 中心の真値
        pred = np.empty_like(y)
        grad1 = np.empty_like(y)
        hann = np.hanning(w + 2)[1:-1]
        for i, yc in enumerate(y):
            ys = yc + (np.arange(w) - (w - 1) / 2) * S_PX
            pred[i] = np.sum(hann * profile(ys)) / hann.sum() - profile(yc)
            grad1[i] = (profile(yc + S_PX) - profile(yc - S_PX)) / (2 * S_PX) * w * S_PX
        bank = ((y < 1.0) | (y > B_WIDTH - 1.0)) & np.isfinite(u)
        meas = u - profile(y)
        b_meas, b_pred = float(np.mean(meas[bank])), float(np.mean(pred[bank]))
        first = float(np.mean([meas[0], meas[-1]])) if np.isfinite(meas[0]) and np.isfinite(meas[-1]) else np.nan
        first_p = float(np.mean([pred[0], pred[-1]]))
        strip = float(y[0])
        q = discharge(y, u)
        q_rule = discharge(y, profile(y))
        rows.append((w, b_meas, b_pred, first, first_p, float(np.mean(np.abs(grad1[bank]))), strip,
                     100 * (q / Q_TRUE - 1), 100 * (q_rule / Q_TRUE - 1)))
        print("  %5d   %+21.3f / %+.3f   %+22.3f / %+.3f   %14.3f   %12.2f   %+9.1f / %+.1f"
              % (w, b_meas, b_pred, first, first_p, rows[-1][5], strip, rows[-1][7], rows[-1][8]))
    print("  ★予想は「偏り ≈ 窓幅 × 勾配」(%.2f〜%.2f m/s)だったが、実測は %.3f〜%.3f m/s と桁で小さい。"
          % (rows[0][5], rows[-1][5], min(r[1] for r in rows[1:]), max(r[1] for r in rows[1:])))
    print("  1 次項は窓の左右で打ち消し、残るのは 2 次項(窓² × 曲率 / 24、Hann で更に 0.4 倍)。")
    print("  窓 16 px の実測 %+.3f が予測 %+.3f から外れるのは粒子 %.0f 個/窓の散らばりで、なまりではない。"
          % (rows[0][1], rows[0][2], 0.02 * 16 * 16))
    print("  ★窓の崖は速度ではなく**流量**に出る:窓 w の 1 行目は岸から w/2 px で、その帯を岸 0 との台形で")
    print("    埋めるので、積分則だけの誤差が %+.1f → %+.1f %% と窓に比例して増える。" % (rows[0][8], rows[-1][8]))
    for r in rows[1:]:
        assert abs(r[1] - r[2]) < 0.02, r
        assert abs(r[1]) < 0.1 * r[5], "窓幅×勾配より桁で小さい"
    assert rows[-1][8] < rows[0][8] - 2.0
    return rows


# --------------------------------------------------------------------------- #
# 7. 崖 (c) 反射のコントラスト                                                     #
# --------------------------------------------------------------------------- #
def section_reflection():
    print("\n" + "=" * 78)
    print("6) 崖 (c) 反射(動かない模様)のコントラスト —— なだらかに引かれるのか")
    print("=" * 78)
    n = 13
    sc = build_frames(n_frames=n, refl_c=0, wave_amp=0, noise=0.0, want_ortho=False)
    pairs = [(k, k + 1) for k in range(n - 1)]
    out = {}
    for kind, pat in (("smooth", sc["refl"]), ("fine", sc["refl_fine"])):
        print("  --- %s ---" % ("空・雲の映り込み(滑らか、相関長 8〜30 px)" if kind == "smooth"
                                else "岸の樹木の映り込み(細かい、相関長 1.2 px)"))
        rows = []
        for c in (0.0, 0.10, 0.20, 0.30, 0.45, 0.60):
            rng = np.random.default_rng(SEED + 7)
            obl = [f + c * pat + rng.normal(0.0, NOISE, f.shape) for f in sc["obl_clean"]]
            r = run_rectified(obl, pairs)
            truth = fs.ledger.piv_sample_at_windows(sc["truth_px"], r["info"])
            yy = np.asarray(r["info"]["rows"])[:, None] * S_PX * np.ones((1, len(r["info"]["cols"])))
            mid = r["ok"] & (yy > 2.0) & (yy < B_WIDTH - 2.0) & np.isfinite(r["flow"][1])
            ratio = float(np.mean(r["flow"][1][mid]) / np.mean(truth[1][mid]))
            dxm = r["flow"][1][mid]
            snapped = float(np.mean(np.abs(dxm) < 0.3))
            pulled = float(np.mean((np.abs(dxm) >= 0.3) & (dxm < truth[1][mid] - 0.3)))
            if kind == "smooth":
                rows.append((c, ratio, pulled, snapped, np.nan, np.nan))
                print("  コントラスト %.2f:速度比 生 %.3f(部分的に引かれた窓 %2.0f %% / ゼロに張り付いた窓 %2.0f %%)"
                      % (c, ratio, 100 * pulled, 100 * snapped))
                continue
            # 時間中央値(固定カメラの背景)を引く
            bg = fs.ledger.sigma_clip_stack(list(obl), mode="median")
            r2 = run_rectified([f - bg for f in obl], pairs)
            ratio_med = float(np.mean(r2["flow"][1][mid]) / np.mean(truth[1][mid]))
            # アンサンブル相関
            rec = [rectify(f) for f in obl]
            fe, _ = pivops.piv_ensemble_correlate(rec, window=WIN)
            ratio_ens = float(np.mean(fe[1][mid]) / np.mean(truth[1][mid]))
            rows.append((c, ratio, pulled, snapped, ratio_med, ratio_ens))
            print("  コントラスト %.2f:速度比 生 %.3f(部分的に引かれた窓 %2.0f %% / ゼロに張り付いた窓 %2.0f %%)"
                  " / 中央値引き %.3f / アンサンブル %.3f"
                  % (c, ratio, 100 * pulled, 100 * snapped, ratio_med, ratio_ens))
        out[kind] = rows
    sm, fi = out["smooth"], out["fine"]
    print("  ★予想は「動かない模様は流速をゼロへ引く」。空の映り込みは %.2f でも速度比 %.3f までしか"
          "引かない(細かい模様は %.3f)。" % (sm[-1][0], sm[-1][1], fi[-1][1]))
    print("    滑らかな模様は窓の平均引きでほぼ消え、残る相関ピークは幅が広くて粒子の鋭い峰に負ける。")
    print("  ★細かい映り込みは 2 段で効く:%.2f〜%.2f では静止ピークと移動ピークが重なって**引かれ**"
          "(部分的 %.0f / %.0f %%)、" % (fi[1][0], fi[2][0], 100 * fi[1][2], 100 * fi[2][2]))
    print("    %.2f 以上では**どちらかが勝って**ゼロに張り付く(%.0f → %.0f %%)。平均は混合比で、傾きは 2 回変わる。"
          % (fi[3][0], 100 * fi[3][3], 100 * fi[-1][3]))
    print("  中央値引きは %.2f でも比 %.3f。アンサンブルは静止ピークも積み上げるので効かない(%.3f)。"
          % (fi[-1][0], fi[-1][4], fi[-1][5]))
    assert sm[-1][1] > 0.9, "空の映り込みはほとんど効かない"
    assert fi[-1][1] < 0.2 and fi[-1][4] > 0.95
    assert fi[1][2] > 0.5 and fi[-1][3] > 0.9, "先に引かれ、後で張り付く"
    return out


# --------------------------------------------------------------------------- #
# 8. 崖 (d) コマ間隔 dt                                                           #
# --------------------------------------------------------------------------- #
def section_dt():
    print("\n" + "=" * 78)
    print("7) 崖 (d) dt を伸ばす —— 相関ピークはどこで消えるか")
    print("=" * 78)
    n = 16
    sc = build_frames(n_frames=n, refl_c=0, wave_amp=0, want_ortho=False)
    rec = [rectify(f) for f in sc["obl"]]
    rows = []
    limit = 0.25 * WIN
    for k in range(1, 9):
        pairs = [(a, a + k) for a in range(0, n - k, max(1, (n - k) // 6))][:6]
        flow, info, nan_f, _ = piv_pairs(rec, pairs)
        flow_p, _, nan_p, _ = piv_pairs(rec, pairs, normalize="none", search_limit=None)
        ok = window_ok(info, WIN)
        truth = fs.ledger.piv_sample_at_windows(sc["truth_px"], info) * k
        bad = np.abs(flow[1] - truth[1]) > 1.0
        bad_p = np.abs(flow_p[1] - truth[1]) > 1.0
        m = ok & np.isfinite(flow[1])
        pred = float(np.mean(truth[1][ok] > limit))
        f_bad = float(np.mean(bad[m]))
        f_bad_p = float(np.mean(bad_p[ok & np.isfinite(flow_p[1])]))
        rows.append((k, k * 2.5, f_bad, pred, f_bad_p, nan_f))
        print("  k=%d(中央 %.1f px):外れ窓 既定 %5.1f %% / 予測(真値 > %.0f px)%5.1f %% / "
              "探索無制限・補正なし %5.1f %%" % (k, k * 2.5, 100 * f_bad, limit, 100 * pred, 100 * f_bad_p))
    print("  既定(1/4 則)の崖は予測どおり k=4 に立つ。物理(対の消失)だけなら k=8 でも半分残る。")
    assert rows[2][2] < 0.1 and rows[3][2] > 0.3
    assert rows[4][4] < rows[4][2]
    return rows


# --------------------------------------------------------------------------- #
# 9. 図                                                                          #
# --------------------------------------------------------------------------- #
def section_figures(sc, zp, rc, ctrl, dens, wins, refl, dts):
    if not figs.enabled():
        return
    obl0 = sc["obl"][0]
    bg = fs.ledger.sigma_clip_stack(list(sc["obl"][:20]), mode="median")
    figs.save_grid("scene", [sc["ortho"][0], obl0, rc["rect"]["rec0"], bg],
                   ["真上カメラ(対照群)", "斜めカメラ(反射・波紋・雑音)", "正射化した斜め画像", "時間中央値 = 反射だけ残る"],
                   title="川面のトレーサを斜めから撮る(幅 8 m・最大 1.5 m/s・30 fps)", ncols=2)
    frames = [sc["obl"][k] for k in (0, 5, 10)]
    figs.save_grid("frames_oblique", frames, ["t = 0 s", "t = %.2f s" % (5 * DT), "t = %.2f s" % (10 * DT)],
                   title="斜め動画のコマ(泡が右へ流れ、空の映り込みは動かない)", ncols=3)
    vel = fs.ledger.piv_to_velocity(rc["rect"]["flow"], S_PX, DT)[1]
    vel = np.where(rc["rect"]["ok"], vel, np.nan)
    tr = profile(np.asarray(rc["rect"]["info"]["rows"])[:, None] * S_PX) * np.ones((1, vel.shape[1]))
    figs.save_grid("map_speed", [np.nan_to_num(tr), np.nan_to_num(vel), np.nan_to_num(vel - tr)],
                   ["真値 u(y) [m/s]", "正射化 → PIV [m/s]", "差 [m/s](視野外は 0)"],
                   title="表面流速の場(窓 32 px、20 対平均)", ncols=3, signed=[False, False, True])
    yy = np.linspace(0, B_WIDTH, 200)
    figs.save_plot("profile",
                   [("真値", yy, profile(yy)),
                    ("ゼロ点(1 尺度)", zp["Yrow"], zp["row_u"]),
                    ("行ごとの尺度", zp["Yrow"], zp["row_ub"]),
                    ("正射化 → PIV", rc["rect"]["y"], rc["rect"]["u"]),
                    ("真上カメラ", rc["y_o"], rc["u_o"])],
                   xlabel="岸からの距離 y [m](近岸 → 遠岸)", ylabel="表面流速 u [m/s]",
                   title="流速分布:ゼロ点は近岸で速く遠岸で遅い")
    d = np.array([r[0] * 100 for r in dens])
    figs.save_plot("density_cliff",
                   [("nan / 対", d, np.array([100 * r[1] for r in dens])),
                    ("外れ値 / 対", d, np.array([100 * r[2] for r in dens])),
                    ("視野外", d, np.array([100 * r[3] for r in dens]))],
                   xlabel="トレーサ密度 [% of px]", ylabel="窓の割合 [%]",
                   title="欠測の種類ごとの割合(密度の崖は外れ値で来る)")
    figs.save_plot("density_rms",
                   [("20 対の平均", d, np.array([r[4] for r in dens])),
                    ("アンサンブル相関", d, np.array([r[5] for r in dens]))],
                   xlabel="トレーサ密度 [% of px]", ylabel="変位の RMS 誤差 [px]",
                   title="密度が薄いときはアンサンブル相関")
    w = np.array([r[0] for r in wins])
    figs.save_plot("window_bank_bias",
                   [("実測(岸 1 m 以内)", w, np.array([r[1] for r in wins])),
                    ("窓平均の予測", w, np.array([r[2] for r in wins])),
                    ("予想していた「窓幅×勾配」(符号は負)", w, -np.array([r[5] for r in wins])),
                    ("誤差ゼロ", w, np.zeros_like(w, float))],
                   xlabel="問い合わせ窓 [px]", ylabel="岸 1 m 以内の速度の偏り [m/s]",
                   title="窓を広げても岸の速度は桁でなまらない(1 次項は打ち消す)")
    figs.save_plot("window_discharge",
                   [("流量の誤差(実測)", w, np.array([r[7] for r in wins])),
                    ("積分則だけの誤差", w, np.array([r[8] for r in wins]))],
                   xlabel="問い合わせ窓 [px]", ylabel="流量の誤差 [%]",
                   title="窓の崖は流量に出る(岸の未測定帯 = w/2)")
    fi, sm = refl["fine"], refl["smooth"]
    c = np.array([r[0] for r in fi])
    figs.save_plot("reflection_cliff",
                   [("細かい映り込み・生", c, np.array([r[1] for r in fi])),
                    ("細かい・時間中央値を引く", c, np.array([r[4] for r in fi])),
                    ("細かい・アンサンブル相関", c, np.array([r[5] for r in fi])),
                    ("空の映り込み・生", np.array([r[0] for r in sm]), np.array([r[1] for r in sm]))],
                   xlabel="反射のコントラスト(標準偏差 / トレーサ輝度)", ylabel="中央部の速度比(推定 / 真値)",
                   title="動かない模様が速度をゼロへ引くのは細かいときだけ", ylim=(-0.05, 1.1))
    figs.save_plot("reflection_modes",
                   [("部分的に引かれた窓", c, np.array([100 * r[2] for r in fi])),
                    ("ゼロに張り付いた窓", c, np.array([100 * r[3] for r in fi]))],
                   xlabel="細かい映り込みのコントラスト", ylabel="窓の割合 [%]",
                   title="平均は 2 峰の混合比だった")
    k = np.array([r[0] for r in dts])
    figs.save_plot("dt_cliff",
                   [("既定(1/4 則)", k, np.array([100 * r[2] for r in dts])),
                    ("予測(真値 > 8 px)", k, np.array([100 * r[3] for r in dts])),
                    ("探索無制限・補正なし", k, np.array([100 * r[4] for r in dts]))],
                   xlabel="コマ間隔 k [コマ](中央の変位 2.5k px)", ylabel="外れ窓(> 1 px)の割合 [%]",
                   title="dt の崖は道具の設定が作る")
    rows = [["ゼロ点(1 尺度)", "%.3f" % zp["rms"], "%+.1f" % (100 * (zp["q"] / Q_TRUE - 1))],
            ["行ごとの尺度", "%.3f" % zp["rms_b"], "%+.1f" % (100 * (zp["q_b"] / Q_TRUE - 1))],
            ["正射化 → PIV", "%.3f" % rc["e_r"], "%+.1f" % (100 * (rc["q_r"] / Q_TRUE - 1))],
            ["真上カメラ", "%.3f" % rc["e_o"], "%+.1f" % (100 * (rc["q_o"] / Q_TRUE - 1))]]
    rows += [[n, "%.3f" % e, "%+.1f" % (100 * (q / Q_TRUE - 1))] for n, e, q in ctrl]
    figs.save_table("discharge", ["条件", "速度 RMS [m/s]", "流量の誤差 [%]"], rows,
                    title="速度の誤差と流量の誤差は別に数える(Q 真値 %.2f m³/s)" % Q_TRUE)


# --------------------------------------------------------------------------- #
# 10. 道具の穴                                                                    #
# --------------------------------------------------------------------------- #
def section_tool_gaps():
    print("\n" + "=" * 78)
    print("8) 道具の穴")
    print("=" * 78)
    print("  (a) `fs.ledger.piv_cross_correlate` は flow だけを返し、窓中心・valid_fraction・")
    print("      peak_ratio の info を落とす。格子が要る本 PoC は `pivops` を直接 import した。")
    assert not isinstance(fs.ledger.piv_cross_correlate(np.random.rand(64, 64), np.random.rand(64, 64)), tuple)
    print("  (b) 4 点対応からホモグラフィを**解く**口が無い(warp_by_plane は使う口)。")
    assert not hasattr(fs.ledger, "vector_to_proj_hom_mat2d")
    print("  (c) `piv_synth_sequence` は粒子が流れ出ても補充しない(周期境界も無い)。")
    print("      60 コマ × 2.5 px なら上流 150 px が枯れる。本 PoC は自前で周期境界にした。")
    print("  (d) 正射化の出力形が入力と同じ(warp_by_plane)なので、形の違う地図は切り出しが要る。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("河川表面流速を斜め動画から測る(LSPIV)—— 速度の誤差と流量の誤差は別に数える")
    print("川幅 %.0f m / 最大 %.1f m/s / 水深 %.1f m / %d fps × %d コマ / 正射 %.0f cm/px"
          % (B_WIDTH, U_MAX, DEPTH, round(1 / DT), N_FRAMES, 100 * S_PX))
    print("=" * 78)
    sc = build_frames()
    scales = section_sanity(sc)
    zp = section_zero_point(sc)
    rc = section_rectified(sc, scales)
    ctrl = section_controls()
    dens = section_density()
    wins = section_window()
    refl = section_reflection()
    dts = section_dt()
    section_figures(sc, zp, rc, ctrl, dens, wins, refl, dts)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * ゼロ点:速度は近岸 %+.2f / 遠岸 %+.2f m/s と符号が逆、流量 %+.1f %%(幅 %.1f m に見える)。"
          % (zp["near"], zp["far"], 100 * (zp["q"] / Q_TRUE - 1), zp["width"]))
    print("  * 正射化:速度 RMS %.3f m/s、流量 %+.1f %%。遠岸の解像度は戻らない(%.3f vs 真上 %.3f m/s)。"
          % (rc["e_r"], 100 * (rc["q_r"] / Q_TRUE - 1), rc["far_r"], rc["far_o"]))
    print("  * 密度の崖は外れ値で来る(%.2f %% で %.0f %%)。窓の崖は 2 次項。反射は二段階。dt は 1/4 則。"
          % (100 * dens[0][0], 100 * dens[0][2]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    sys.exit(main())
