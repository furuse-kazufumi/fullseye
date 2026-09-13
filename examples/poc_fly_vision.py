# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ハエの視覚前段は、閉じた式で検査できる op の連鎖で書ける —— 合成の空を歩く/回ると、何が読めて何が読めないか。

    py -3.11 examples/poc_fly_vision.py

ハエの視葉(optic lobe)は、六角格子の個眼 → 受容野で平滑 → 隣接個眼対の相関器
(Hassenstein-Reichardt EMD)→ 広視野の対向和(HS 細胞)という、数個の閉じた式で
書ける経路で「自分が回っているか」を読む。並行して、拡大する物体の見込み角
θ(t) から η = θ'·exp(−αθ)(LGMD)と τ = 2tan(θ/2)/θ'(衝突余裕)で「ぶつかるか」を読む。
この PoC は :mod:`flyvision` の 8 op をその順に**繋いで 1 匹の眼にし**、合成の
空を回る/前進する/球が迫る/縞が流れる、の 4 場面で何が読めるかを測る。

この PoC が測る唯一の主張:

    **ハエの視覚前段は、閉じた式で検査できる op の連鎖で書ける —— 合成の空を
    歩く/回ると、何が読めて(自己回転の向きと時間波形、衝突までの時間、方向選択性)
    何が読めないか(前進の混入は上半視野に限らないと回転に化ける、対向比の読み出しは
    速さの大小を落とす)。**

EXTEND: 実データに差し替えるなら :func:`render_view` だけを差し替える。以降は
「ピンホール像 (H, W) の時系列」しか見ていない(全天カメラの等距円筒フレームなら
:func:`sample_pano` の代わりに実フレームを引く)。ルーミング章は θ(t) の 1-D 系列、
方向選択性章は個眼ごとの (az, el) に置いた縞だけを見る。

**データはこのリポジトリに同梱しない。** 空は :func:`flyvision.fly_sky_1f`(1/f の
帯つき等距円筒)、床は同型の 2-D 1/f タイル、球の接近は閉じた式で、外部データは要らない。

この PoC が使う物理:

    個眼格子 n = 3R(R+1)+1(R=15 → 721)。受容野は FWHM Δρ のガウス。
    ラミナ段: 個眼輝度から一次低域(τ 0.25 s)を引いて DC を落とす(L1/L2 の帯域通過)。
    EMD: R(t) = LP(a)·b − a·LP(b)。右向き(方位が減る向き)を好む対は
    a = 左隣、b = 右の個眼。対向比 (Σ⁺ − Σ⁻)/(Σ⁺ + Σ⁻) は**符号の一致度**であって
    速さではない(→ 第 3 章の「読めないもの」)。
    LGMD: η のピークは衝突の α·l/|v| 前、そのとき θ = 2atan(1/α)(α=4.7 → 24.0°)。
    これは tan 形の見込み角(正面の円板)で厳密。球の 2asin(l/d) では 4 次式の根
    x* = 4.699 で d = x*·l、θ = 2asin(1/x*) = 24.6°。
    τ: 球なら 2tan(θ/2)/θ' = d/|v| が厳密、円板の式 sin θ/θ' を球に使うと
    cos²(θ/2) 倍(θ=60° で 0.75 倍)に読み違える。

実測(2026-09-13、R=15・Δφ=2.6°・Δρ=4.6°・fov 90°・dt 10 ms・3 s、seed 固定):

    量                                              実測
    回転: HS 読み出し vs 真の角速度(LP 0.1 s)       相関 +0.785(膜 LP 0.1 s つき +0.880、符号一致 0.92)
    回転: 帯なし(amp=0)の対照                       EMD 応答の最大 5.9e-32(= 0、何も動かない)
    回転: ★ラミナ段(DC 落とし)を省くと              相関 +0.504(DC × 高域通過の揺れが平均の 10 倍)
    前進: 全視野 / 上半 el>0 / 上半 el>2Δρ の偏り   −0.689 / −0.221 / +0.000(空は無限遠、床 0.10 m)
    前進: 上半 el>2Δρ・空を 20 m のドームに          −0.612(1.4°/s の流れが床の 100°/s 台と同じ大きさに)
    ルーミング: η ピーク時刻 / 予測 α·l/|v|          −0.1570 s / −0.1567 s、θ_peak 23.97°(予測 24.02°)
    ルーミング: 球の厳密な θ での η ピーク           θ 24.52°(予測 2asin(1/x*) = 24.58°)
    ルーミング: τ(球式) vs 真値 d/|v|                RMS 1e-5 s、円板式は θ=59.7° で 0.7525 倍(cos²(θ/2))
    方向選択性 DSI / 好む向き                        0.798 / −0.0°(12 方位、右向き = 0°)

読めるもの: 自己回転の向きと波形(相関 0.79–0.88)、衝突までの時間(τ は真値に厳密)、
η のピーク時刻と角、方向選択性。読めないもの: (1) 前進は上半視野に限らないと回転に化け、
限っても受容野が地平線をまたぐぶん(el < 2Δρ)床が漏れる、(2) 対向比は速さを落とすので
1°/s の遠景の流れも 100°/s の床の流れも同じ大きさに読む、(3) ラミナ段の DC 落としを
省くと相関器は DC × 高域通過の揺れを出し、運動の平均応答が埋もれる。

参考: B. Hassenstein & W. Reichardt, *Z. Naturforsch.* 11b:513 (1956);
K. Hausen, *Biol. Cybern.* 45:143 (1982); F. Gabbiani, H. G. Krapp & G. Laurent,
*J. Neurosci.* 19:1122 (1999); D. N. Lee, *Perception* 5:437 (1976);
H. G. Krapp & R. Hengstenberg, *Nature* 384:463 (1996).
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import flyvision as FV  # noqa: E402

# ---------------------------------------------------------------------------- #
#  眼と像の寸法                                                                  #
# ---------------------------------------------------------------------------- #
RADIUS = 15            # 六角格子の半径 → 3*15*16+1 = 721 個眼
# 個眼間角。既定 4.63° だと半径 15 の眼は光軸から ±69° に広がり、fov 90° の
# ピンホール像(±45°)に収まらない(fly_hex_resample が視野外で拒否する)。
# 2.6° なら ±39°(方位)/ ±34°(仰角)で像の中に入る。
DPHI_DEG = 2.6
DRHO_DEG = 4.6         # 受容野 FWHM。Δρ/Δφ ≈ 1.8 はショウジョウバエの比(8.2/4.6)
AZ0_DEG = 45.0         # 眼の光軸: 左前方 45°(ハエの眼は横を向いている)
EL0_DEG = 10.0         # やや上向き(上半視野が 1/f の帯 20–60° に届くように)
FOV_DEG = 90.0         # ピンホール像の縦の全視野
IMG = 128              # ピンホール像 (IMG, IMG)。721 × 16384 = 1.18e7 < 2^24 の上限
PANO_W, PANO_H = 720, 360

DT = 0.010             # 10 ms
T_END = 3.0            # 3 s
TAU_EMD = 0.05         # 相関器の低域 τ
TAU_HP = 0.25          # ラミナ段(L1/L2)の高域通過 τ: 個眼輝度の DC を落としてから相関器へ
TAU_HS = 0.10          # HS の膜時定数の代理(読み出しに掛ける低域)
TAU_TRUTH = 0.10       # 真の角速度に掛ける低域 τ(相関器の遅れと同程度)
T_SKIP = 0.3           # 立ち上がりを捨てる長さ

H_EYE = 0.10           # 前進章: 眼の床からの高さ [m]
V_FWD = 0.5            # 前進章: 速さ [m/s]
FLOOR_TILE_M = 2.0     # 床テクスチャの周期タイル [m]
DOME_R_M = 20.0        # 「遠景を有限距離にすると」の空ドーム半径 [m]


# ---------------------------------------------------------------------------- #
#  小道具                                                                        #
# ---------------------------------------------------------------------------- #
def lowpass(x, tau_s, dt_s):
    """一次低域(τ y' + y = x)を厳密な指数平滑で。"""
    x = np.asarray(x, float)
    alpha = 1.0 - np.exp(-dt_s / tau_s)
    y = np.empty_like(x)
    acc = x[0]
    for i in range(x.size):
        acc = acc + alpha * (x[i] - acc)
        y[i] = acc
    return y


def corr(x, y):
    """ピアソン相関。どちらかが定数なら **0.0 と置く**(NaN を印字しない。
    「帯なし」の対照は応答が厳密に 0 になり、相関が定義できないため)。"""
    x = np.asarray(x, float) - np.mean(x)
    y = np.asarray(y, float) - np.mean(y)
    sx = float(np.sqrt(np.sum(x * x)))
    sy = float(np.sqrt(np.sum(y * y)))
    if sx <= 0.0 or sy <= 0.0:
        return 0.0
    return float(np.sum(x * y) / (sx * sy))


def sample_pano(pano, az_rad, el_rad):
    """等距円筒パノラマ(行 = 仰角 +90→−90、列 = 方位 0→360)を双一次で引く。"""
    H, W = pano.shape
    col = (np.degrees(az_rad) % 360.0) / 360.0 * W - 0.5
    row = (90.0 - np.degrees(el_rad)) / 180.0 * H - 0.5
    c0 = np.floor(col).astype(int)
    r0 = np.floor(row).astype(int)
    fc = col - c0
    fr = row - r0
    c1 = (c0 + 1) % W
    c0 = c0 % W
    r0c = np.clip(r0, 0, H - 1)
    r1 = np.clip(r0 + 1, 0, H - 1)
    return (pano[r0c, c0] * (1 - fr) * (1 - fc) + pano[r0c, c1] * (1 - fr) * fc
            + pano[r1, c0] * fr * (1 - fc) + pano[r1, c1] * fr * fc)


def floor_texture_1f(n=256, seed=3):
    """周期タイルの 2-D 1/f テクスチャ(振幅 1/|k|、|k| < 2 cycle/tile は落とす)。
    :func:`flyvision.fly_sky_1f` の方位ノイズと同じ作法を 2-D にしたもの。"""
    rng = np.random.default_rng(seed)
    ky = np.fft.fftfreq(n, d=1.0 / n)[:, None]
    kx = np.fft.rfftfreq(n, d=1.0 / n)[None, :]
    k = np.hypot(ky, kx)
    amp = np.where(k >= 2.0, 1.0 / np.maximum(k, 1e-9), 0.0)
    phase = rng.uniform(0.0, 2.0 * np.pi, size=k.shape)
    x = np.fft.irfft2(amp * np.exp(1j * phase), s=(n, n))
    x = x / float(x.std())
    return np.clip(x, -2.0, 2.0)


def sample_floor(tex, X, Y):
    """床タイル(周期 FLOOR_TILE_M)を世界座標 (X, Y) [m] で双一次に引く(両軸で巻く)。"""
    n = tex.shape[0]
    u = (X / FLOOR_TILE_M) * n - 0.5
    v = (Y / FLOOR_TILE_M) * n - 0.5
    u0 = np.floor(u).astype(int)
    v0 = np.floor(v).astype(int)
    fu = u - u0
    fv = v - v0
    u1 = (u0 + 1) % n
    v1 = (v0 + 1) % n
    u0 = u0 % n
    v0 = v0 % n
    return (tex[v0, u0] * (1 - fv) * (1 - fu) + tex[v0, u1] * (1 - fv) * fu
            + tex[v1, u0] * fv * (1 - fu) + tex[v1, u1] * fv * fu)


def pinhole_dirs(lattice):
    """ピンホール画素の視線方向 (IMG, IMG, 3)(眼座標)。
    **fly_hex_resample と同じ規約**(光軸 = 格子中心、列が増える向き = 左、
    行が増える向き = 下、fov は縦の全視野)で作る —— ここがずれると眼は別の絵を見る。"""
    uv = lattice["uv"]
    centre = int(np.where((uv[:, 0] == 0) & (uv[:, 1] == 0))[0][0])
    axis = lattice["dirs"][centre]
    f = (IMG / 2.0) / np.tan(np.deg2rad(FOV_DEG) / 2.0)
    yy, xx = np.mgrid[0:IMG, 0:IMG].astype(float)
    xc = (xx + 0.5 - IMG / 2.0) / f
    yc = -(yy + 0.5 - IMG / 2.0) / f
    el0 = float(np.arcsin(np.clip(axis[2], -1.0, 1.0)))
    az0 = float(np.arctan2(axis[1], axis[0]))
    left = np.array([-np.sin(az0), np.cos(az0), 0.0])
    up = np.array([-np.cos(az0) * np.sin(el0), -np.sin(az0) * np.sin(el0), np.cos(el0)])
    d = axis[None, None, :] + left[None, None, :] * xc[..., None] + up[None, None, :] * yc[..., None]
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


# ---------------------------------------------------------------------------- #
#  場面(差し替え点)                                                              #
# ---------------------------------------------------------------------------- #
def render_view(scene, dirs_eye, yaw_rad=0.0, pos=(0.0, 0.0, 0.0)):
    """眼(ヨー角 *yaw_rad*、位置 *pos* [m])から見たピンホール像 (IMG, IMG)。

    ``scene = {"sky": パノラマ, "dome_r": None(無限遠)か半径 [m],
    "floor": None か 2-D テクスチャ, "floor_z": 床の高さ [m]}``。
    空は等距円筒パノラマ(無限遠なら方向で、ドームなら光線とドームの交点の方向で引く)、
    床は水平面との交点を世界座標でテクスチャから引く。"""
    c, s = np.cos(yaw_rad), np.sin(yaw_rad)
    dx = c * dirs_eye[..., 0] - s * dirs_eye[..., 1]
    dy = s * dirs_eye[..., 0] + c * dirs_eye[..., 1]
    dz = dirs_eye[..., 2]
    p = np.asarray(pos, float)
    R = scene.get("dome_r")
    if R is None:
        az, el = np.arctan2(dy, dx), np.arcsin(np.clip(dz, -1.0, 1.0))
    else:
        pd = p[0] * dx + p[1] * dy + p[2] * dz
        t = -pd + np.sqrt(pd * pd - float(p @ p) + R * R)
        hx, hy, hz = p[0] + t * dx, p[1] + t * dy, p[2] + t * dz
        az, el = np.arctan2(hy, hx), np.arcsin(np.clip(hz / R, -1.0, 1.0))
    img = sample_pano(scene["sky"], az, el)
    tex = scene.get("floor")
    if tex is not None:
        below = dz < 0.0
        t = (scene["floor_z"] - p[2]) / dz[below]
        X = p[0] + t * dx[below]
        Y = p[1] + t * dy[below]
        img[below] = 0.90 * (1.0 + 0.12 * sample_floor(tex, X, Y))
    return img


def see(scene, lattice, dirs_eye, yaws_rad, positions):
    """時系列の各時刻でレンダリングし、眼に写す。返り値 (T, n) の個眼輝度。"""
    out = []
    for yaw, pos in zip(yaws_rad, positions):
        img = render_view(scene, dirs_eye, yaw, pos)
        out.append(FV.fly_hex_resample(img, lattice, drho_deg=DRHO_DEG, fov_deg=FOV_DEG))
    return np.asarray(out)


# ---------------------------------------------------------------------------- #
#  眼の配線: 隣接対 → EMD → HS                                                    #
# ---------------------------------------------------------------------------- #
def horizontal_pairs(lattice):
    """同じ仰角行(同じ u)で隣り合う個眼対 ``(i, j)``。j は i の左隣(方位が Δφ 大きい)。"""
    uv = lattice["uv"]
    lut = {(int(u), int(v)): k for k, (u, v) in enumerate(uv)}
    pairs = []
    for k, (u, v) in enumerate(uv):
        j = lut.get((int(u), int(v) + 1))
        if j is not None:
            pairs.append((k, j))
    return pairs


def lamina_highpass(signals, tau_s=TAU_HP, dt_s=DT):
    """ラミナ段: 個眼ごとの輝度から一次低域(τ)を引いて DC を落とす (T, n) → (T, n)。

    ★これを省くと相関器は DC × 高域通過 の項 ``D·(b − LP b)`` を出す。輝度 0.8 に
    コントラスト 0.1 の縞なら、その揺れは運動の平均応答の **10 倍**(実測: 純正弦でも
    R の std 2.1e-2 対 平均 3.6e-3)。回転の相関は 0.50 に落ち、前進の偏りは 0.02 に
    埋もれる。ハエでは L1/L2 が帯域通過なのでこの項は最初から無い。
    """
    return signals - np.apply_along_axis(lowpass, 0, signals, tau_s, dt_s)


def emd_map(signals, pairs, n, highpass=True):
    """各対に EMD を当て、右向きを好む応答を対の右側の個眼の列に置く (T, n)。
    右向き = 方位が減る向き。左隣 j を先に通るので a = 左隣、b = 右(自分)。"""
    T = signals.shape[0]
    s = lamina_highpass(signals) if highpass else signals
    R = np.zeros((T, n))
    for i, j in pairs:
        R[:, i] = FV.fly_emd_response(s[:, j], s[:, i], tau_s=TAU_EMD, dt_s=DT)
    return R


def hs_series(R, lattice, el_min_deg):
    """各時刻で (2, n) —— 先頭行が好む向き、2 行目はその逆 —— を HS に読ませる。"""
    out = np.empty(R.shape[0])
    for t in range(R.shape[0]):
        resp = np.stack([R[t], -R[t]])
        out[t] = FV.fly_hs_readout(resp, lattice, n_pref=1, el_min_deg=el_min_deg)
    return out


def hex_raster(lattice, values, step_deg=0.25):
    """個眼ごとの値を (仰角, 方位) 平面の六角セルに塗った画像にする(図のため)。
    軸座標へ立方丸めで最近傍セルを引く。列は**左が方位大**(世界の左が画の左)。"""
    az = np.degrees(lattice["az_rad"])
    el = np.degrees(lattice["el_rad"])
    dphi = float(np.degrees(lattice["dphi_rad"]))
    Rr = int(np.max(np.abs(lattice["uv"])))
    tbl = np.full((2 * Rr + 1, 2 * Rr + 1), np.nan)
    for k, (u, v) in enumerate(lattice["uv"]):
        tbl[int(u) + Rr, int(v) + Rr] = values[k]
    A = np.arange(az.max() + dphi, az.min() - dphi, -step_deg)
    E = np.arange(el.max() + dphi, el.min() - dphi, -step_deg)
    AZ, EL = np.meshgrid(A, E)
    uf = (EL - EL0_DEG) / (dphi * np.sqrt(3.0) / 2.0)
    vf = (AZ - AZ0_DEG) / dphi - uf / 2.0
    x, z = vf, uf
    y = -x - z
    rx, ry, rz = np.round(x), np.round(y), np.round(z)
    ddx, ddy, ddz = np.abs(rx - x), np.abs(ry - y), np.abs(rz - z)
    fix_x = (ddx > ddy) & (ddx > ddz)
    fix_z = ~fix_x & (ddz > ddy)
    rx[fix_x] = -ry[fix_x] - rz[fix_x]
    rz[fix_z] = -rx[fix_z] - ry[fix_z]
    u = rz.astype(int)
    v = rx.astype(int)
    ok = (np.abs(u) <= Rr) & (np.abs(v) <= Rr) & (np.abs(u + v) <= Rr)
    out = np.full(AZ.shape, float(np.nanmin(values)))
    out[ok] = tbl[u[ok] + Rr, v[ok] + Rr]
    out = np.where(np.isfinite(out), out, float(np.nanmin(values)))
    return out


def pano_window(pano, az_c_deg, half_w_deg=60.0, el_lo=-40.0, el_hi=80.0):
    """パノラマの、眼の周りの窓(左が方位大 = 世界の左が画の左)。"""
    H, W = pano.shape
    az = np.linspace(az_c_deg + half_w_deg, az_c_deg - half_w_deg, int(2 * half_w_deg * 2))
    el = np.linspace(el_hi, el_lo, int((el_hi - el_lo) * 2))
    AZ, EL = np.meshgrid(np.deg2rad(az), np.deg2rad(el))
    return sample_pano(pano, AZ, EL)


# ---------------------------------------------------------------------------- #
#  第 1 章 —— 空を眼に写す                                                          #
# ---------------------------------------------------------------------------- #
def chapter_eye_sees_the_sky(lattice, dirs_eye, sky):
    """1/f の帯つき空を 721 個眼で見る。像 → 眼の縮約が視野内で閉じることを確かめる。"""
    scene = {"sky": sky, "dome_r": None, "floor": None}
    img = render_view(scene, dirs_eye, 0.0)
    sig = FV.fly_hex_resample(img, lattice, drho_deg=DRHO_DEG, fov_deg=FOV_DEG)
    el = np.degrees(lattice["el_rad"])
    in_band = (el >= 25.0) & (el <= 40.0)
    out_band = (el <= 5.0)
    ratio = float(sig[in_band].std() / max(sig[out_band].std(), 1e-12))
    print("== 第1章: 空を眼に写す ==")
    print("  個眼数 n=%d(R=%d)、Δφ=%.1f°、Δρ=%.1f°、眼の光軸 az=%.0f° el=%.0f°"
          % (sig.size, RADIUS, DPHI_DEG, DRHO_DEG, AZ0_DEG, EL0_DEG))
    print("  眼の仰角範囲 %.1f°〜%.1f°、方位範囲 %.1f°〜%.1f°"
          % (el.min(), el.max(), np.degrees(lattice["az_rad"]).min(),
             np.degrees(lattice["az_rad"]).max()))
    print("  個眼輝度の帯内(25–40°)/帯外(≤5°)の方位ばらつき比 : %.1f 倍" % ratio)
    figs.save_grid(
        "fly_vision_scene",
        # ピンホール像は 128 px なので最近傍で 2 倍(値は作らない)にして他の 2 枚と並べる。
        [pano_window(sky, AZ0_DEG), np.repeat(np.repeat(img[:, ::-1], 2, axis=0), 2, axis=1),
         hex_raster(lattice, sig)],
        captions=["1/f の帯つき空(眼の周り ±60°)", "眼が見るピンホール像(fov 90°)",
                  "721 個眼に写した輝度(六角格子)"],
        title="空 → ピンホール像 → 個眼格子", gray=True, ncols=3)
    return ratio


# ---------------------------------------------------------------------------- #
#  第 2 章 —— 回転を読む                                                            #
# ---------------------------------------------------------------------------- #
FREQS_HZ = (0.3, 0.7, 1.3, 2.1)
AMPS_DEG = (20.0, 8.0, 4.0, 2.0)
PHASES = (0.0, 1.1, 2.3, 4.0)


def yaw_trajectory(t):
    """4 本の正弦の和(角 [deg] と角速度 [deg/s]、角速度は解析微分)。"""
    yaw = np.zeros_like(t)
    rate = np.zeros_like(t)
    for f, A, ph in zip(FREQS_HZ, AMPS_DEG, PHASES):
        yaw += A * np.sin(2 * np.pi * f * t + ph)
        rate += A * 2 * np.pi * f * np.cos(2 * np.pi * f * t + ph)
    return yaw, rate


def chapter_rotation(lattice, dirs_eye, pairs, sky, sky_flat):
    """回りながら空を見ると、EMD → HS は自己回転の向きと波形を読む(速さの尺度は失う)。"""
    t = np.arange(int(round(T_END / DT))) * DT
    yaw_deg, rate = yaw_trajectory(t)
    truth = lowpass(rate, TAU_TRUTH, DT)
    n = lattice["dirs"].shape[0]
    still = [(0.0, 0.0, 0.0)] * t.size
    keep = t >= T_SKIP
    sig = see({"sky": sky, "dome_r": None, "floor": None}, lattice, dirs_eye,
              np.deg2rad(yaw_deg), still)
    sig_flat = see({"sky": sky_flat, "dome_r": None, "floor": None}, lattice, dirs_eye,
                   np.deg2rad(yaw_deg), still)
    R = emd_map(sig, pairs, n)
    R_flat = emd_map(sig_flat, pairs, n)
    R_dc = emd_map(sig, pairs, n, highpass=False)          # ラミナ段を省いた対照
    est = hs_series(R, lattice, el_min_deg=0.0)
    est_hs = lowpass(est, TAU_HS, DT)
    est_flat = hs_series(R_flat, lattice, el_min_deg=0.0)
    est_dc = hs_series(R_dc, lattice, el_min_deg=0.0)
    c_band = corr(est[keep], truth[keep])
    c_hs = corr(est_hs[keep], truth[keep])
    c_flat = corr(est_flat[keep], truth[keep])
    c_dc = corr(est_dc[keep], truth[keep])
    r_flat_max = float(np.abs(R_flat).max())
    agree = float(np.mean(np.sign(est[keep]) == np.sign(truth[keep])))
    gain = float(np.sum(est_hs[keep] * truth[keep]) / max(np.sum(est_hs[keep] ** 2), 1e-12))
    print("\n== 第2章: 回転を読む(ヨー = %s Hz の正弦 4 本、最大 %.0f°/s)=="
          % ("/".join("%.1f" % f for f in FREQS_HZ), np.abs(rate).max()))
    print("  HS 読み出し vs 真の角速度(LP %.2f s)の相関      : %+.3f" % (TAU_TRUTH, c_band))
    print("  同、読み出しに HS の膜 LP %.2f s を掛けて         : %+.3f" % (TAU_HS, c_hs))
    print("  符号の一致率                                     : %.3f" % agree)
    print("  帯なし(amp=0)の対照: EMD 応答の最大絶対値 %.1e → 読み出し %.1e、相関 %+.3f"
          % (r_flat_max, float(np.abs(est_flat).max()), c_flat))
    print("  ★ラミナ段(DC 落とし)を省くと相関                : %+.3f(DC × 高域通過の揺れが平均を埋める)" % c_dc)
    print("  最小二乗の尺度 k(真値 ≈ k × 読み出し)              : %.1f °/s(対向比は速さを落とす)" % gain)
    figs.save_plot(
        "fly_vision_rotation",
        [("真のヨー角速度(LP 0.1 s)[°/s]", t, truth),
         ("HS 読み出し(膜 LP 0.1 s)× k", t, est_hs * gain),
         ("ラミナ段なし × k", t, est_dc * gain)],
        xlabel="時間 [s]", ylabel="角速度 [°/s]",
        title="回転: EMD → HS の読み出しは向きと波形を追う",
        caption="相関 %+.3f(膜 LP つき %+.3f、ラミナ段なし %+.3f)。対向比は符号の一致度なので、"
                "尺度 k は最小二乗で合わせてある。" % (c_band, c_hs, c_dc))
    return c_band, c_hs, c_flat, c_dc, r_flat_max, agree, gain


# ---------------------------------------------------------------------------- #
#  第 3 章 —— 前進の混入                                                            #
# ---------------------------------------------------------------------------- #
def chapter_forward(lattice, dirs_eye, pairs, sky):
    """回転せずに前進すると、床の流れは HS に「回転」と読まれる —— 上半視野に限れば消える。"""
    t = np.arange(int(round(T_END / DT))) * DT
    n = lattice["dirs"].shape[0]
    tex = floor_texture_1f()
    pos = [(V_FWD * ti, 0.0, 0.0) for ti in t]
    yaws = np.zeros(t.size)
    keep = t >= T_SKIP
    out = {}
    el_clear = 2.0 * DRHO_DEG                        # 受容野の裾(2Δρ)が地平線をまたがない高さ
    scene_inf = {"sky": sky, "dome_r": None, "floor": tex, "floor_z": -H_EYE}
    sig = see(scene_inf, lattice, dirs_eye, yaws, pos)
    R = emd_map(sig, pairs, n)
    out["upper"] = hs_series(R, lattice, el_min_deg=0.0)
    out["upper_clear"] = hs_series(R, lattice, el_min_deg=el_clear)
    out["full"] = hs_series(R, lattice, el_min_deg=-90.0)
    scene_dome = {"sky": sky, "dome_r": DOME_R_M, "floor": tex, "floor_z": -H_EYE}
    sig_d = see(scene_dome, lattice, dirs_eye, yaws, pos)
    R_d = emd_map(sig_d, pairs, n)
    out["upper_dome"] = hs_series(R_d, lattice, el_min_deg=el_clear)
    bias = {k: float(lowpass(v, TAU_HS, DT)[keep].mean()) for k, v in out.items()}
    dome_flow = np.degrees(V_FWD / DOME_R_M)
    print("\n== 第3章: 前進の混入(%.1f m/s、眼の高さ %.2f m、回転なし)==" % (V_FWD, H_EYE))
    print("  全視野(el>−90)の読み出しの平均                  : %+.3f(床の前→後の流れが「右回り」に化ける)"
          % bias["full"])
    print("  上半視野だけ(el>0、空は無限遠)                  : %+.3f(受容野が地平線をまたぐぶん床が漏れる)"
          % bias["upper"])
    print("  上半視野・受容野の裾まで上(el>2Δρ=%.1f°)         : %+.3f" % (el_clear, bias["upper_clear"]))
    print("  同・空を %.0f m のドームに(流れ ≤ %.1f°/s)         : %+.3f(対向比は速さを落とす: "
          "1°/s 台の流れが床の 100°/s 台と同じ大きさに読める)"
          % (DOME_R_M, dome_flow, bias["upper_dome"]))
    figs.save_plot(
        "fly_vision_forward",
        [("全視野(床が入る)", t, lowpass(out["full"], TAU_HS, DT)),
         ("上半視野 el>0(空は無限遠)", t, lowpass(out["upper"], TAU_HS, DT)),
         ("上半視野 el>2Δρ", t, lowpass(out["upper_clear"], TAU_HS, DT)),
         ("上半視野 el>2Δρ・空を 20 m のドームに", t, lowpass(out["upper_dome"], TAU_HS, DT))],
        xlabel="時間 [s]", ylabel="HS 読み出し(対向比、膜 LP 0.1 s)",
        title="前進: 床の流れは回転に化ける、上半視野に限れば消える",
        caption="偏り: 全視野 %+.3f / 上半 el>0 %+.3f / el>2Δρ %+.3f / ドーム %+.3f"
                % (bias["full"], bias["upper"], bias["upper_clear"], bias["upper_dome"]))
    return bias


# ---------------------------------------------------------------------------- #
#  第 4 章 —— ルーミング                                                            #
# ---------------------------------------------------------------------------- #
L_SPHERE = 0.01        # 球の半径 [m]
V_APPROACH = 0.30      # 接近速度 [m/s]
ALPHA = 4.7
DT_LOOM = 0.001


def sphere_eta_peak_ratio(alpha):
    """球の厳密な見込み角 θ = 2asin(l/d) で η = θ'·exp(−αθ) が最大になる d/l(閉じた式)。

    d ln η/dd = 0 は ``2x² − 1 = 2α√(x²−1)``(x = d/l)、両辺を 2 乗して x² の 2 次式
    ``4x⁴ − (4+4α²)x² + (1+4α²) = 0`` → 大きい根。α=4.7 で x = 4.699(≈ α だが厳密には違う)。
    円板の tan 形 θ = 2atan(l/d) なら d = αl が厳密(Gabbiani et al. 1999, Eq. 5)。"""
    A = 4.0 + 4.0 * alpha * alpha
    B = 1.0 + 4.0 * alpha * alpha
    x2 = (A + np.sqrt(A * A - 16.0 * B)) / 8.0
    return float(np.sqrt(x2))


def chapter_looming():
    """半径 1 cm の球が 30 cm/s で迫る θ(t) に η と τ を当て、閉じた式と突き合わせる。

    η は Gabbiani の幾何(半幅 l の正面物体、θ = 2atan(l/d))で 2atan(1/α) = 24.0° が
    厳密。球の見込み角 2asin(l/d) では 4 次式の根 x* で θ = 2asin(1/x*) = 24.6°。両方測る。"""
    t = np.arange(-1.0, -0.05 + 0.5 * DT_LOOM, DT_LOOM)      # 衝突 t=0、d=1.5 cm で止める
    d = -V_APPROACH * t
    theta_disk = 2.0 * np.arctan(L_SPHERE / d)
    theta_sph = 2.0 * np.arcsin(L_SPHERE / d)
    t_pred = -ALPHA * L_SPHERE / V_APPROACH
    th_pred = float(np.degrees(2.0 * np.arctan(1.0 / ALPHA)))
    xs = sphere_eta_peak_ratio(ALPHA)
    t_pred_s = -xs * L_SPHERE / V_APPROACH
    th_pred_s = float(np.degrees(2.0 * np.arcsin(1.0 / xs)))
    eta = FV.fly_lgmd_eta(theta_disk, DT_LOOM, alpha=ALPHA)
    eta_s = FV.fly_lgmd_eta(theta_sph, DT_LOOM, alpha=ALPHA)
    k = int(np.argmax(eta))
    ks = int(np.argmax(eta_s))
    t_peak, th_peak = float(t[k]), float(np.degrees(theta_disk[k]))
    t_peak_s, th_peak_s = float(t[ks]), float(np.degrees(theta_sph[ks]))
    tau_s = FV.fly_tau_from_expansion(theta_sph, DT_LOOM, shape="sphere")
    tau_d = FV.fly_tau_from_expansion(theta_sph, DT_LOOM, shape="disk")
    truth = d / V_APPROACH
    inner = slice(2, -2)                                       # 端の片側差分は除く
    rms_s = float(np.sqrt(np.mean((tau_s[inner] - truth[inner]) ** 2)))
    k60 = int(np.argmin(np.abs(np.degrees(theta_sph) - 60.0)))
    ratio60 = float(tau_d[k60] / tau_s[k60])
    ratio60_pred = float(np.cos(theta_sph[k60] / 2) ** 2)
    print("\n== 第4章: ルーミング(球 r=%.0f cm、%.0f cm/s、α=%.1f、dt %.0f ms)=="
          % (100 * L_SPHERE, 100 * V_APPROACH, ALPHA, 1000 * DT_LOOM))
    print("  η のピーク時刻(tan 形 θ)  : %+.4f s(予測 α·l/|v| = %+.4f s)" % (t_peak, t_pred))
    print("  η ピークの θ(tan 形 θ)    : %.2f°(予測 2atan(1/α) = %.2f°)" % (th_peak, th_pred))
    print("  同、球の厳密な θ=2asin(l/d) : ピーク %+.4f s(予測 x*·l/|v|、x*=%.3f → %+.4f s)、"
          "θ %.2f°(予測 2asin(1/x*) = %.2f°)" % (t_peak_s, xs, t_pred_s, th_peak_s, th_pred_s))
    print("  τ(球式) vs d/|v| の RMS     : %.5f s" % rms_s)
    print("  θ=%.1f° で 円板式/球式      : %.4f(予測 cos²(θ/2) = %.4f)"
          % (np.degrees(theta_sph[k60]), ratio60, ratio60_pred))
    figs.save_plot(
        "fly_vision_looming_eta",
        [("η(t) / max(tan 形 θ)", t, eta / eta.max()), ("θ(t) / 180°", t, np.degrees(theta_disk) / 180.0),
         ("予測ピーク α·l/|v|", np.array([t_pred]), np.array([1.0]))],
        xlabel="衝突までの時間 [s](衝突 = 0)", ylabel="正規化",
        title="LGMD η は衝突の α·l/|v| 前、θ = 24.0° で最大",
        kinds=["line", "line", "scatter"], ylim=(0.0, 1.6),      # 凡例の下にピークを出す
        caption="ピーク %+.3f s(予測 %+.3f s)、θ_peak %.1f°(予測 %.1f°)。球の厳密な θ なら %.1f°。"
                % (t_peak, t_pred, th_peak, th_pred, th_peak_s))
    figs.save_plot(
        "fly_vision_looming_tau",
        [("真値 d/|v|", t[inner], truth[inner]), ("τ 球式 2tan(θ/2)/θ'", t[inner], tau_s[inner]),
         ("τ 円板式 sin θ/θ'(球に誤用)", t[inner], tau_d[inner])],
        xlabel="衝突までの時間 [s]", ylabel="衝突余裕 τ [s]",
        title="τ: 物体モデルを取り違えると θ=60° で 0.75 倍",
        caption="球式は RMS %.5f s で真値に乗る。円板式は cos²(θ/2) 倍に縮む。" % rms_s)
    return {"t_peak": t_peak, "t_pred": t_pred, "th_peak": th_peak, "th_pred": th_pred,
            "t_peak_s": t_peak_s, "t_pred_s": t_pred_s, "th_peak_s": th_peak_s,
            "th_pred_s": th_pred_s, "rms_tau": rms_s, "ratio60": ratio60,
            "ratio60_pred": ratio60_pred}


# ---------------------------------------------------------------------------- #
#  第 5 章 —— 方向選択性                                                            #
# ---------------------------------------------------------------------------- #
LAMBDA_DEG = 20.0
F_GRATING_HZ = 3.0
CONTRAST = 0.3
DT_GRAT = 0.005
T_GRAT = 1.0


def chapter_dsi(lattice, pairs):
    """12 方位に流れる縞への EMD 応答の和から DSI と好む向きを出す(右向き = 0°)。"""
    n = lattice["dirs"].shape[0]
    x = -(np.degrees(lattice["az_rad"]) - AZ0_DEG)     # 画の右 = 方位が減る向き
    y = np.degrees(lattice["el_rad"]) - EL0_DEG
    t = np.arange(int(round(T_GRAT / DT_GRAT))) * DT_GRAT
    angles = np.arange(0.0, 360.0, 30.0)
    resp = []
    half = t.size // 2
    for th in angles:
        u = np.deg2rad(th)
        phase = 2 * np.pi * (x * np.cos(u) + y * np.sin(u)) / LAMBDA_DEG
        sig = 0.5 + CONTRAST * np.cos(phase[None, :] - 2 * np.pi * F_GRATING_HZ * t[:, None])
        R = np.zeros((t.size, n))
        for i, j in pairs:
            R[:, i] = FV.fly_emd_response(sig[:, j], sig[:, i], tau_s=TAU_EMD, dt_s=DT_GRAT)
        resp.append(float(R[half:].sum(axis=1).mean()))
    resp = np.asarray(resp)
    d = FV.fly_dsi(resp, angles)
    print("\n== 第5章: 方向選択性(縞 λ=%.0f°、%.0f Hz、12 方位)==" % (LAMBDA_DEG, F_GRATING_HZ))
    for th, r in zip(angles, resp):
        print("   %3.0f° : %+.4f" % (th, r))
    print("  DSI = %.3f、好む向き = %+.1f°(右向き = 0°)" % (d["dsi"], d["pref_deg"]))
    figs.save_plot(
        "fly_vision_dsi",
        [("EMD 応答の和(定常平均)", angles, resp)],
        xlabel="縞の進む向き [°](0 = 右)", ylabel="応答",
        title="方向選択性: DSI %.2f、好む向き %+.0f°" % (d["dsi"], d["pref_deg"]),
        kinds=["bar"],
        caption="負の応答(逆向き)は fly_dsi が 0 に切る。")
    return d, resp, angles


def main():
    with warnings.catch_warnings():
        warnings.simplefilter("error")     # 黙ったゼロ割・NaN を出させない
        lattice = FV.fly_hex_lattice(radius=RADIUS, dphi_deg=DPHI_DEG,
                                     az0_deg=AZ0_DEG, el0_deg=EL0_DEG)
        dirs_eye = pinhole_dirs(lattice)
        pairs = horizontal_pairs(lattice)
        sky = FV.fly_sky_1f(PANO_W, PANO_H, band_lo_deg=20.0, band_hi_deg=60.0, amp=0.12, seed=0)
        sky_flat = FV.fly_sky_1f(PANO_W, PANO_H, band_lo_deg=20.0, band_hi_deg=60.0, amp=0.0, seed=0)

        band_ratio = chapter_eye_sees_the_sky(lattice, dirs_eye, sky)
        c_band, c_hs, c_flat, c_dc, r_flat_max, agree, gain = \
            chapter_rotation(lattice, dirs_eye, pairs, sky, sky_flat)
        bias = chapter_forward(lattice, dirs_eye, pairs, sky)
        loom = chapter_looming()
        dsi, _resp, _angles = chapter_dsi(lattice, pairs)

    # ---- 自己検査 ---------------------------------------------------------- #
    # 第1章: 721 個眼が全部像の中(fly_hex_resample が視野外で拒否しなかった)、帯は帯として写る。
    assert len(pairs) == 3 * RADIUS * (RADIUS + 1) + 1 - (2 * RADIUS + 1), "隣接対の数が格子と合わない"
    assert band_ratio > 3.0, "1/f の帯が個眼輝度に写っていない"

    # 第2章: 相関は正(左回り → 眼の像は右へ → 右向き検出器が鳴る)、帯なしより高い。
    #         値そのもの(0.8 台)は主張しない —— 実測をそのまま報告する。
    assert c_band > 0.0, "回転の向きが読めていない(相関の符号が負)"
    assert c_band > c_flat, "帯ありが帯なし(応答 0)より高くない"
    assert r_flat_max < 1e-6, "帯なしの空で EMD 応答が出た(何かが動いている)"
    # ★ラミナ段(DC 落とし)を省くと相関が落ちる、を固定する。落ちなくなったら
    #   fly_emd_response の側で DC が消えている(仕様変更)なので、この対照を見直す。
    assert c_dc < c_band - 0.1, "ラミナ段を省いても相関が落ちない(EMD が DC を落とすようになった?)"

    # 第3章: 上半視野に限ると前進の混入は減り、全視野では「回転」に化ける。
    assert abs(bias["upper"]) < abs(bias["full"]), "上半視野に限っても前進の混入が減らない"
    assert abs(bias["upper_clear"]) < abs(bias["upper"]), \
        "受容野の裾まで上げても地平線の漏れが減らない"
    assert bias["full"] < 0.0, "左眼の前進の流れは前→後(=右回り、負)のはず"
    assert abs(bias["upper_dome"]) > abs(bias["upper_clear"]), \
        "有限距離のドームの流れ(≈1.4°/s)が読み出しに出ない"

    # 第4章: 閉じた式との一致(η のピーク時刻・角、球の 4 次式、τ 球式、円板式の cos²(θ/2))。
    assert abs(loom["t_peak"] - loom["t_pred"]) <= 2 * DT_LOOM, "η のピーク時刻が α·l/|v| と合わない"
    assert abs(loom["th_peak"] - loom["th_pred"]) < 0.1, "η ピークの θ が 2atan(1/α) と合わない"
    assert abs(loom["t_peak_s"] - loom["t_pred_s"]) <= 2 * DT_LOOM, "球の η ピーク時刻が 4 次式の根と合わない"
    assert abs(loom["th_peak_s"] - loom["th_pred_s"]) < 0.1, "球の η ピーク θ が 2asin(1/x*) と合わない"
    assert loom["rms_tau"] < 1e-3, "τ 球式が d/|v| に乗らない"
    assert abs(loom["ratio60"] - loom["ratio60_pred"]) < 5e-3, "円板式/球式が cos²(θ/2) から外れた"

    # 第5章: 好む向きは右向き(0°)の ±30°、DSI は 0 と 1 の間で意味のある値。
    assert abs(dsi["pref_deg"]) < 30.0, "好む向きが右向きではない"
    assert 0.3 < dsi["dsi"] < 1.0, "DSI が退化している"

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))

    # ★PoC の門(tests/test_poc_scripts_run.py)は exit 0 に加えて "PASS" の印字を
    #   要求する(合否を計算したのに捨てる門を防ぐ規約)。
    print("\nPASS: 回転の相関 %+.3f(ラミナ段なし %+.3f)、前進の偏り 上半 %+.3f / 全視野 %+.3f、"
          "η ピーク θ %.1f°(予測 %.1f°)、DSI %.2f(好む向き %+.0f°)—— "
          "ハエの視覚前段は閉じた式で検査できる op の連鎖で書けた。"
          % (c_band, c_dc, bias["upper"], bias["full"], loom["th_peak"], loom["th_pred"],
             dsi["dsi"], dsi["pref_deg"]))


if __name__ == "__main__":
    main()
