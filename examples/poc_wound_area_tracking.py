# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_wound_area_tracking — 創傷面積の経時変化。**較正の誤差は面積に 2 乗で効く**。

    py -3.11 examples/poc_wound_area_tracking.py

【この PoC が答える問い】
褥瘡・熱傷・潰瘍の治り具合は「面積が何 % / 日で縮むか」(治癒定数 k)で語られます。
撮るのは毎回ちがう距離・角度からのスマホ写真で、画面の中に既知寸法の較正標識
(スケールマーカー)を置く —— これが臨床でいちばん普通の測り方です。問いは
「**どこで嘘になるか**」。答えは「**長さの較正が ε ずれると面積は 2ε ずれ、
距離が日ごとにわずかに漂うだけで k の推定が丸ごと壊れる**」。

【グラウンドトゥルース(自分で仕込んだ真値)】
創面は **mm の世界平面に置いた星形の閉曲線** r(φ) = R·s(φ)。面積は
0.5∫r²dφ = R²·π(1 + Σaᵢ²/2) と**閉形式**なので、A(t) = A0·exp(-k·t) を満たす
R(t) を厳密に解いて置ける。画像は「元画像を歪めたもの」ではなく、**画素ごとに
逆投影して mm 平面で内外判定した被覆率**(3x3 の副標本)。補間を通さないので
真の面積が丸め誤差の桁で分かる。カメラはピンホール、平面 → 画素は 3x3 の
ホモグラフィで厳密。

【この PoC が示すこと(数字はすべて実行時に印字される実測値)】

 1. **ラスタライズの床**。正対・雑音なしで面積の誤差は **-0.333 〜 +0.167 %**。
    以降の誤差はすべてこの床の上に乗っている。
 2. ★★**ゼロ点(1 枚目だけで較正)を距離で振ると、面積は 2 乗で動く**。
    Z/Z0 を 0.90 → 1.10 と振ると面積誤差は **+23.58 % → -17.36 %**。閉形式の
    (Z0/Z)²-1 とは最大 **0.278 pp** しか違わない(= 床そのもの)。線形近似の
    -2ε は最大 **3.58 pp** 外れるので、**「2ε」は 1 次項であって法則ではない**
    (正しくは (1+ε)⁻²-1)。★撮影距離が 4 % 違うだけで面積が **7.7 %** 動く。
 3. ★★**k の推定が壊れる**。日ごとに距離が +1.2 % ずつ漂う(ジッタ 1.5 %)
    8 セッション x 8 seed で、真の k = 0.1200 /day に対しゼロ点は
    **0.1424 ± 0.0049**(**+18.7 %**)。**漂い 1.2 %/day の 2 倍 = 2.4 %/day が
    指数の肩に乗る**(0.1200+0.0240 = 0.1440)という予測どおり。毎回較正し
    なおすと +2.1 %、正対化すると **+0.0 %**。
    ★**散らばりでは気づけない**: ゼロ点の標準偏差 0.0049 は毎回較正の 0.0059
    より**小さい**。いちばん安定して、いちばん間違った答えを返す。
 4. ★**毎回較正しなおしても傾きは直らない**。1 本の長さで較正する方式は距離の
    ずれをほぼ完全に消す(遠 495 mm で -0.58 %、近 405 mm で -0.10 %)が、
    **傾き 20 度で -9.08 %**。ホモグラフィで正対化すると同じ場面で -1.23 %。
 5. ★**しきい値と較正を同じ軸で比べると、較正が 5〜15 倍支配的**。公称値からの
    相対摂動 12.5 % に対し、面積は較正 **+26.77 %** / しきい値 **+1.81 %**
    (ぼけ σ=0.45 px)・**+5.53 %**(σ=2.4 px)動く。**ぼかすとしきい値の感度が
    3 倍になる**が、それでも較正には届かない。
 6. ★★**正対化の残差は再標本化ではなく標識の置き場所で決まる**。対照群
    (**真の**ホモグラフィで正対化)の誤差は最大 **0.23 %** —— つまり
    warp + 二値化の床は 0.2 % 台。推定ホモグラフィだと最大 **2.39 %**。
    標識を創面の**そば**(30 mm 角、中心間 61 mm)から**創面を囲む** 104 mm 角に
    変えると平均 |誤差| が **1.11 % → 0.10 %**(11 倍)に下がる。4 点の重心の
    ずれはどちらも 0.1〜0.3 px で同じ —— 違うのは**外挿か内挿か**だけ。
    **標識は測る場所を囲め**。
 7. ★**予想が外れた**。「較正しなおせば必ずゼロ点に勝つ」と踏んでいたが、
    遠くから傾けた 1 場面ではゼロ点 **-22.00 %**・長さ較正 **+13.52 %** で、
    符号が逆なだけで大きさは同程度。長さ較正が勝つのは**距離だけが動く**
    ときで、傾きが混ざると**別方向に同じくらい外す**。

【節立て】
 1) 合成器の検算(ラスタライズの床)
 2) ★★ゼロ点と 2 乗則
 3) 3 手法 x 6 場面
 4) ★★治癒定数 k の推定
 5) ★較正の感度 vs しきい値の感度(同じ軸)
 6) ★★対照群 —— 残差はどこから来るか / 標識の置き場所
 7) 道具の穴(assert で現状を固定)

EXTEND: 実写に差し替えるなら :func:`render` が返す画像と、``truth`` の面積の対を
「撮影画像」と「同じ創面をトレースして求めた面積」に置き換える。**真値をノギスや
定規の実測長から作らないこと** —— それはこの PoC が測っている較正そのもので、
推定と真値が同じ誤差を共有してしまう(見かけ上ぴたりと合い、何も検証できない)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import fit_transform                                             # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
H_PX, W_PX = 300, 400          # 画素
F_PX = 900.0                   # 焦点距離 [px]
CX, CY = W_PX / 2.0, H_PX / 2.0
SS = 3                         # 画素あたりの副標本(片側)
Z0 = 450.0                     # 基準の撮影距離 [mm] -> 2.0 px/mm

# 創面の形 (次数, 振幅, 位相)。面積は閉形式で出る(下の SHAPE_NORM)。
SHAPE = ((3, 0.25, 0.7), (5, 0.15, -0.3), (7, 0.10, 1.9))
SHAPE_NORM = np.pi * (1.0 + sum(a * a for _, a, _ in SHAPE) / 2.0)

# 較正標識 = 大きさの違う 4 つの点。大きさで番号が付くので対応が一意に決まる。
DOT_R = (3.0, 2.5, 2.0, 1.6)   # [mm]
LAYOUT_SIDE = np.array([[35.0, -50.0], [65.0, -50.0], [65.0, -20.0], [35.0, -20.0]])
LAYOUT_AROUND = np.array([[-52.0, -52.0], [52.0, -52.0], [52.0, 52.0], [-52.0, 52.0]])

I_SKIN, I_WOUND, I_DOT = 0.78, 0.30, 0.05
T_HI, T_LO = 0.54, 0.16        # 創面の帯 (T_LO, T_HI)。T_HI は皮膚と創面の中点。
CONTRAST = I_SKIN - I_WOUND

S_MM = 0.25                    # 正対化した像の 1 px の大きさ [mm]
OX, OY = W_PX / 2.0, H_PX / 2.0
SWAP = np.array([[0.0, 1, 0], [1, 0, 0], [0, 0, 1]])

K_TRUE, A0_MM2, N_DAY, N_SEED = 0.12, 900.0, 8, 8
DRIFT = 0.012                  # 撮影距離が 1 日あたり漂う割合
JITTER = 0.015


# --- 合成 -------------------------------------------------------------------- #
def shape_radius(phi):
    """星形の半径倍率 s(φ)。"""
    s = np.ones_like(phi)
    for m, a, ph in SHAPE:
        s = s + a * np.cos(m * phi + ph)
    return s


def radius_for_area(area_mm2):
    """面積 A を厳密に与える R(A)。A = R² · π(1 + Σaᵢ²/2)。"""
    return np.sqrt(area_mm2 / SHAPE_NORM)


def camera_h(z, tilt=0.0, azim=0.0, roll=0.0):
    """原点を見下ろすカメラの平面ホモグラフィ (X,Y,1)[mm] -> (u,v,1)[px]。

    ``tilt`` = 鉛直からの傾き、``azim`` = その方位、``roll`` = 面内回転[rad]。
    カメラは常に原点を向く(視野から外れないようにするため)。
    """
    d = np.array([np.sin(tilt) * np.cos(azim), np.sin(tilt) * np.sin(azim), np.cos(tilt)])
    fwd = -d
    up = np.array([np.sin(roll), np.cos(roll), 0.0])
    right = np.cross(fwd, up)
    right = right / np.linalg.norm(right)
    upc = np.cross(right, fwd)
    rot = np.array([right, -upc, fwd])
    t = -rot @ (z * d)
    k = np.array([[F_PX, 0, CX], [0, F_PX, CY], [0, 0, 1.0]])
    return k @ np.column_stack([rot[:, 0], rot[:, 1], t])


def hom_apply(h, pts):
    """3x3 を (N,2) に適用。列の意味は呼び手の規約に従う(この関数は素通し)。"""
    p = np.asarray(pts, float).reshape(-1, 2)
    q = np.asarray(h, float) @ np.column_stack([p, np.ones(len(p))]).T
    return (q[:2] / q[2]).T


def render(hw, area_mm2, dots=LAYOUT_SIDE, blur=0.0, noise=0.0, seed=0):
    """1 枚撮る。**画素ごとに mm 平面へ逆投影して内外判定**(補間を通さない)。"""
    hi = np.linalg.inv(hw)
    off = (np.arange(SS) + 0.5) / SS - 0.5
    cov_w = np.zeros((H_PX, W_PX))
    cov_d = np.zeros((H_PX, W_PX))
    r0 = radius_for_area(area_mm2)
    yy, xx = np.mgrid[0:H_PX, 0:W_PX].astype(float)
    for dy in off:
        for dx in off:
            u = (xx + dx).ravel()
            v = (yy + dy).ravel()
            p = hi @ np.stack([u, v, np.ones_like(u)])
            wx, wy = p[0] / p[2], p[1] / p[2]
            rr = np.hypot(wx, wy)
            cov_w += (rr <= r0 * shape_radius(np.arctan2(wy, wx))).reshape(H_PX, W_PX)
            din = np.zeros_like(wx, bool)
            for dc, dr in zip(dots, DOT_R):
                din |= (wx - dc[0]) ** 2 + (wy - dc[1]) ** 2 <= dr * dr
            cov_d += din.reshape(H_PX, W_PX)
    cov_w /= SS * SS
    cov_d /= SS * SS
    img = I_SKIN * (1 - cov_w - cov_d) + I_WOUND * cov_w + I_DOT * cov_d
    if blur > 0:
        img = np.asarray(fs.apply(img, "gaussian", a=blur))    # sigma = 3a [px]
    if noise > 0:
        img = img + np.random.default_rng(seed).normal(0.0, noise, img.shape)
    return img


# --- 測る(fullseye の blob 族)------------------------------------------------ #
def wound_area_px(img, t_hi=T_HI, t_lo=T_LO):
    """創面の画素面積。しきい値 → 連結成分 → いちばん大きい塊。"""
    lab = fs.ledger.blob_label((img < t_hi) & (img > t_lo))
    lab = fs.ledger.blob_select_largest(lab, 1)
    f = fs.ledger.blob_features(lab)
    return float(f["area"][0]) if f["n"] else 0.0


def dot_centroids(img, t_lo=T_LO):
    """較正標識の 4 点の重心 (u, v)。**面積の大きい順** = ``DOT_R`` の順。"""
    lab = fs.ledger.blob_select_largest(fs.ledger.blob_label(img < t_lo), 4)
    f = fs.ledger.blob_features(lab)
    order = np.argsort(-f["area"])
    return np.column_stack([f["col"], f["row"]])[order]


def mm_per_px_from_length(dots_img, dots_mm):
    """★較正の本体 —— 標識の 2 点間の**長さ**から mm/px を出す。"""
    return (float(np.linalg.norm(dots_mm[0] - dots_mm[1]))
            / float(np.linalg.norm(dots_img[0] - dots_img[1])))


def rectify(img, h_world_to_img):
    """正対化。出力画素 -> mm 平面 -> 入力画素 の合成を ``warp_by_plane`` に渡す。"""
    m = np.array([[S_MM, 0, -OX * S_MM], [0, -S_MM, OY * S_MM], [0, 0, 1.0]])
    return np.asarray(fs.ledger.warp_by_plane(img, h_world_to_img @ m, cval=I_SKIN))


def homography_from_dots(dots_img, dots_mm):
    """4 点対応 -> mm 平面 (X,Y) から画素 (u,v) へのホモグラフィ。

    ``fit_transform.hom_vector_to_proj_hom_mat2d`` は **(row, col)** 規約なので、
    両側を入れ替えて渡し、返ってきた行列を ``SWAP`` で (x, y) 規約へ戻す。
    """
    h_rc = fit_transform.hom_vector_to_proj_hom_mat2d(dots_mm[:, ::-1], dots_img[:, ::-1])
    return SWAP @ h_rc @ SWAP


def measure_all(img, dots_mm, mm_fixed, h_true=None):
    """3 手法(+ 対照群)を同じ 1 枚から測る。返りは mm²。"""
    a_px = wound_area_px(img)
    d = dot_centroids(img)
    out = {"M0": a_px * mm_fixed ** 2,
           "M1": a_px * mm_per_px_from_length(d, dots_mm) ** 2,
           "M2": wound_area_px(rectify(img, homography_from_dots(d, dots_mm))) * S_MM ** 2}
    if h_true is not None:
        out["M3"] = wound_area_px(rectify(img, h_true)) * S_MM ** 2
    out["dot_err"] = float(np.abs(d - hom_apply(h_true, dots_mm)).max()) if h_true is not None \
        else float("nan")
    return out


SCENES = [
    ("正対 450 mm", (Z0, 0.0, 0.0, 0.0), 900.0),
    ("遠 495 mm (+10 %)", (495.0, 0.0, 0.0, 0.0), 900.0),
    ("近 405 mm (-10 %)", (405.0, 0.0, 0.0, 0.0), 900.0),
    ("傾き 20 度", (Z0, 20.0, 0.0, 0.0), 900.0),
    ("傾き 22 + 方位 + 回転", (Z0, 22.0, 50.0, 12.0), 900.0),
    ("遠 + 傾き, A=500", (495.0, 18.0, 200.0, -8.0), 500.0),
]


def scene_h(spec):
    z, tl, az, ro = spec
    return camera_h(z, np.deg2rad(tl), np.deg2rad(az), np.deg2rad(ro))


# --------------------------------------------------------------------------- #
# 1) 合成器の検算                                                              #
# --------------------------------------------------------------------------- #
def section1_floor():
    print("=" * 78)
    print("1) 合成器の検算 —— ラスタライズの床(ゼロ点その 0)")
    print("=" * 78)
    print("  正対・雑音なし。真の mm/px を与えて数えるだけ。ここで出る誤差は")
    print("  以降すべての誤差の下限になる。")
    print()
    hw = camera_h(Z0)
    mm_true = Z0 / F_PX
    print("  %10s %12s %12s %10s" % ("真の面積", "画素面積", "推定 mm²", "誤差 %"))
    print("  " + "-" * 48)
    floor = []
    for a in (300.0, 500.0, 900.0, 1400.0):
        img = render(hw, a)
        apx = wound_area_px(img)
        est = apx * mm_true ** 2
        floor.append(100 * (est / a - 1))
        print("  %10.1f %12.0f %12.2f %+10.3f" % (a, apx, est, floor[-1]))
    print()
    print("  → 床は %+.3f 〜 %+.3f %%。副標本 %dx%d の被覆率をしきい値 0.5 相当で" %
          (min(floor), max(floor), SS, SS))
    print("     切っているので、境界画素の丸めぶんだけ残る。")
    return float(np.max(np.abs(floor)))


# --------------------------------------------------------------------------- #
# 2) ゼロ点と 2 乗則                                                           #
# --------------------------------------------------------------------------- #
def section2_zero_point():
    print()
    print("=" * 78)
    print("2) ★★ゼロ点 —— 1 枚目だけで較正して、以後その mm/px を使い回す")
    print("=" * 78)
    print("  臨床でいちばん普通の運用。標識は毎回写っているのに、係数は初回のまま。")
    print("  撮影距離だけを振って、面積がどう動くかを測る(傾きは 0 に固定)。")
    print()
    img0 = render(camera_h(Z0), 900.0)
    mm_fixed = mm_per_px_from_length(dot_centroids(img0), LAYOUT_SIDE)
    print("  1 枚目の較正: %.6f mm/px(真値 %.6f)" % (mm_fixed, Z0 / F_PX))
    print()
    print("  %7s %7s %14s %14s %14s %10s" %
          ("Z/Z0", "eps %", "実測 dA/A %", "(Z0/Z)²-1 %", "線形 -2eps %", "法則との差"))
    print("  " + "-" * 74)
    ratios = [0.90, 0.94, 0.96, 0.98, 1.00, 1.02, 1.04, 1.06, 1.10]
    meas, law, lin = [], [], []
    for f in ratios:
        img = render(camera_h(Z0 * f), 900.0)
        est = wound_area_px(img) * mm_fixed ** 2
        e = 100 * (est / 900.0 - 1)
        la = 100 * ((1.0 / f) ** 2 - 1)
        li = -200.0 * (f - 1)
        meas.append(e)
        law.append(la)
        lin.append(li)
        print("  %7.2f %7.1f %+14.4f %+14.4f %+14.4f %10.3f" % (f, 100 * (f - 1), e, la, li,
                                                                abs(e - la)))
    dev_law = float(np.max(np.abs(np.array(meas) - np.array(law))))
    dev_lin = float(np.max(np.abs(np.array(meas) - np.array(lin))))
    print()
    print("  → ★★面積は距離の **2 乗**で動く。実測と閉形式 (Z0/Z)²-1 の差は最大")
    print("     %.3f pp(= 1 節の床そのもの)。線形近似 -2eps との差は最大 %.2f pp。" %
          (dev_law, dev_lin))
    print("     **「2ε」は 1 次項であって法則ではない** —— ±10 %% 振ると %.2f pp 外れる。"
          % dev_lin)
    i5 = ratios.index(1.04)
    print("     ★実務の含意: 撮影距離が %.0f %% 違うだけで面積が %.1f %% 動く。" %
          (100 * (ratios[i5] - 1), abs(meas[i5])))
    figs.save_plot("dist_square_law",
                   [("実測 (ゼロ点)", ratios, meas),
                    ("(Z0/Z)^2 - 1", ratios, law),
                    ("線形 -2eps", ratios, lin)],
                   xlabel="Z / Z0", ylabel="面積の誤差 [%]",
                   title="較正を固定したまま距離を振る",
                   caption="ゼロ点の面積誤差。実測は閉形式の 2 乗則に乗り、線形近似からは外れる。")
    return mm_fixed, dev_law, dev_lin


# --------------------------------------------------------------------------- #
# 3) 3 手法 x 6 場面                                                           #
# --------------------------------------------------------------------------- #
def section3_methods(mm_fixed):
    print()
    print("=" * 78)
    print("3) 対比 —— 毎回較正しなおす / ホモグラフィで正対化する")
    print("=" * 78)
    print("  M0 = 1 枚目の mm/px を使い回す(ゼロ点)")
    print("  M1 = 毎回、標識の 2 点間の長さから mm/px を出しなおす")
    print("  M2 = 毎回、標識 4 点からホモグラフィを推定して正対化してから測る")
    print()
    print("  %-22s %8s %9s %9s %9s %9s" % ("場面", "真値", "M0 %", "M1 %", "M2 %", "点誤差px"))
    print("  " + "-" * 72)
    rows, worst = [], {"M0": 0.0, "M1": 0.0, "M2": 0.0}
    panels, last = {}, None
    for name, spec, area in SCENES:
        hw = scene_h(spec)
        img = render(hw, area)
        m = measure_all(img, LAYOUT_SIDE, mm_fixed, h_true=hw)
        e = {k: 100 * (m[k] / area - 1) for k in ("M0", "M1", "M2")}
        for k in worst:
            worst[k] = max(worst[k], abs(e[k]))
        rows.append([name, "%.0f" % area] + ["%+.2f" % e[k] for k in ("M0", "M1", "M2")])
        print("  %-22s %8.0f %+9.2f %+9.2f %+9.2f %9.3f" %
              (name, area, e["M0"], e["M1"], e["M2"], m["dot_err"]))
        panels[name] = img
        last = e
    print()
    print("  → M1(毎回較正)は**距離のずれをほぼ完全に消す**が、傾きは直らない。")
    print("     M2(正対化)だけが両方に効く。最大 |誤差| は M0 %.1f %% / M1 %.1f %% / M2 %.1f %%。"
          % (worst["M0"], worst["M1"], worst["M2"]))
    print("  → ★予想が外れた: 「較正しなおせば必ずゼロ点に勝つ」は成り立たない。")
    print("     最後の場面(遠 + 傾き)は M0 %+.1f %% に対し M1 %+.1f %% —— **符号が逆なだけで"
          % (last["M0"], last["M1"]))
    print("     大きさは同程度**。長さ較正が効くのは距離だけが動くときだけ。")

    # 図: 正対 / 遠+傾き / それを正対化 / 正対化マスクと真のマスクの差
    img_ref = panels["正対 450 mm"]
    img_bad = panels["遠 + 傾き, A=500"]
    rect = rectify(img_bad, homography_from_dots(dot_centroids(img_bad), LAYOUT_SIDE))
    yy, xx = np.mgrid[0:H_PX, 0:W_PX].astype(float)
    wx = (xx - OX) * S_MM
    wy = -(yy - OY) * S_MM
    truth_mask = np.hypot(wx, wy) <= radius_for_area(500.0) * shape_radius(np.arctan2(wy, wx))
    got = (rect < T_HI) & (rect > T_LO)
    figs.save_grid("scenes",
                   [img_ref, img_bad, rect, got.astype(float) - truth_mask.astype(float)],
                   ["正対 450mm", "遠+傾き", "正対化", "マスク差"],
                   title="同じ創面・ちがう撮り方", ncols=2,
                   signed=[False, False, False, True],
                   caption="4 枚目は正対化した二値と真の二値の差(赤 = 余分、青 = 足りない)。")
    return rows, worst


# --------------------------------------------------------------------------- #
# 4) 治癒定数 k                                                                #
# --------------------------------------------------------------------------- #
def one_session(seed, dots_mm=LAYOUT_SIDE, drift=DRIFT):
    """8 日ぶんの撮影 → 3 手法の面積列。"""
    rng = np.random.default_rng(seed)
    out = {k: [] for k in ("M0", "M1", "M2", "true")}
    mm_fixed = None
    for day in range(N_DAY):
        area = A0_MM2 * np.exp(-K_TRUE * day)
        z = Z0 * (1.0 + drift * day + rng.normal(0.0, JITTER))
        hw = camera_h(z, np.deg2rad(rng.uniform(0.0, 18.0)), rng.uniform(0.0, 2 * np.pi),
                      np.deg2rad(rng.uniform(-12.0, 12.0)))
        img = render(hw, area, dots=dots_mm)
        if mm_fixed is None:
            mm_fixed = mm_per_px_from_length(dot_centroids(img), dots_mm)
        m = measure_all(img, dots_mm, mm_fixed)
        for k in ("M0", "M1", "M2"):
            out[k].append(m[k])
        out["true"].append(area)
    return out


def fit_k(areas):
    """ln A の直線当てはめ → k [1/day]。"""
    return float(-np.polyfit(np.arange(len(areas), dtype=float), np.log(np.asarray(areas)), 1)[0])


def section4_healing_constant():
    print()
    print("=" * 78)
    print("4) ★★治癒定数 k の推定 —— 較正の漂いは指数の肩に乗る")
    print("=" * 78)
    print("  A(t) = A0·exp(-k·t)、真の k = %.4f /day、%d 日。" % (K_TRUE, N_DAY))
    print("  撮影距離は 1 日あたり %+.1f %% 漂い(患者が動く/撮る人が変わる)、" % (100 * DRIFT))
    print("  そのうえに %.1f %% のジッタ。傾きは毎回 0〜18 度、面内回転 ±12 度。" % (100 * JITTER))
    print()
    ks = {m: [] for m in ("M0", "M1", "M2")}
    curves = None
    for s in range(N_SEED):
        o = one_session(1000 + s)
        for m in ks:
            ks[m].append(fit_k(o[m]))
        if curves is None:
            curves = o
    print("  %-6s %12s %10s %10s" % ("手法", "k 平均", "標準偏差", "偏り %"))
    print("  " + "-" * 42)
    tab = {}
    for m in ("M0", "M1", "M2"):
        v = np.array(ks[m])
        tab[m] = (v.mean(), v.std(), 100 * (v.mean() / K_TRUE - 1))
        print("  %-6s %12.4f %10.4f %+10.1f" % (m, *tab[m]))
    print()
    print("  → ★★ゼロ点の偏りは **%+.1f %%**。予測どおり: 距離が %.1f %%/day 漂えば"
          % (tab["M0"][2], 100 * DRIFT))
    print("     面積は %.1f %%/day 漂い、ln A の傾きに %.4f /day が上乗せされる"
          % (200 * DRIFT, 2 * DRIFT))
    print("     (%.4f + %.4f = %.4f、実測 %.4f)。" % (K_TRUE, 2 * DRIFT, K_TRUE + 2 * DRIFT,
                                                    tab["M0"][0]))
    print("  → **散らばりでは気づけない**: M0 の標準偏差は %.4f で M1 の %.4f より**小さい**。"
          % (tab["M0"][1], tab["M1"][1]))
    print("     ゼロ点はいちばん安定して、いちばん間違った答えを返す。")
    days = np.arange(N_DAY, dtype=float)
    figs.save_plot("healing_curve",
                   [("真値", days, curves["true"]),
                    ("M0 固定較正", days, curves["M0"]),
                    ("M1 長さ較正", days, curves["M1"]),
                    ("M2 正対化", days, curves["M2"])],
                   xlabel="経過日", ylabel="面積 [mm^2]",
                   title="治癒曲線(seed 1000 の 1 例)",
                   caption="ゼロ点は毎回もっともらしい値を返しながら、傾きだけが系統的に急になる。")
    return tab


# --------------------------------------------------------------------------- #
# 5) 感度の比較                                                                #
# --------------------------------------------------------------------------- #
def section5_sensitivity():
    print()
    print("=" * 78)
    print("5) ★較正の感度 vs しきい値の感度 —— 同じ軸に載せる")
    print("=" * 78)
    print("  軸を揃える: どちらも**公称値からの相対摂動**で振る。")
    print("    較正 —— 標識の記録寸法を (1+d) 倍に間違える")
    print("    しきい値 —— T_HI を コントラスト(%.2f) の d 倍だけ動かす" % CONTRAST)
    print()
    deltas = [-0.25, -0.185, -0.125, -0.0625, 0.0, 0.0625, 0.125, 0.185, 0.25]
    hw = camera_h(Z0)
    mm_true = Z0 / F_PX
    series = {}
    # 較正: 面積は (1+d)² 倍。画像は 1 枚で足りる(較正係数だけが動く)。
    img = render(hw, 900.0)
    apx = wound_area_px(img)
    series["較正の長さ"] = [100 * (apx * (mm_true * (1 + d)) ** 2 / 900.0 - 1) for d in deltas]
    for blur, tag in ((0.15, "しきい値 s=0.45px"), (0.8, "しきい値 s=2.4px")):
        im = render(hw, 900.0, blur=blur)
        series[tag] = [100 * (wound_area_px(im, t_hi=T_HI + d * CONTRAST) * mm_true ** 2 / 900.0
                              - 1) for d in deltas]
    print("  %-20s %s" % ("摂動 d", "  ".join("%+7.3f" % d for d in deltas)))
    print("  " + "-" * 92)
    for k, v in series.items():
        print("  %-20s %s" % (k, "  ".join("%+7.2f" % x for x in v)))
    i = deltas.index(0.125)
    ratio_sharp = abs(series["較正の長さ"][i]) / abs(series["しきい値 s=0.45px"][i])
    ratio_blur = abs(series["較正の長さ"][i]) / abs(series["しきい値 s=2.4px"][i])
    print()
    print("  → ★同じ 12.5 %% の摂動で、面積は較正 %.2f %% / しきい値 %.2f %%(鋭い縁)"
          % (series["較正の長さ"][i], series["しきい値 s=0.45px"][i]))
    print("     / %.2f %%(ぼけた縁)。**較正が %.1f 〜 %.1f 倍支配的**。"
          % (series["しきい値 s=2.4px"][i], ratio_blur, ratio_sharp))
    print("     しきい値の感度は縁の勾配 |∇I| で決まるので、**ぼかすと悪くなる**")
    print("     (周長 x 等高線の移動量 = 面積の変化)。それでも較正には届かない。")
    print("  → 実務の含意: しきい値を %.0f %% 動かすのは目で見て分かる操作だが、"
          % (100 * deltas[i]))
    print("     撮影距離を %.0f %% 間違えるのは**気づかない**。" % (100 * deltas[i]))
    figs.save_plot("sensitivity",
                   [(k, deltas, v) for k, v in series.items()],
                   xlabel="公称値からの相対摂動 d", ylabel="面積の誤差 [%]",
                   title="どちらが支配的か(較正 vs しきい値)",
                   caption="較正は d に対して (1+d)²-1、しきい値はほぼ線形。傾きが 4〜6 倍違う。")
    return series, ratio_sharp, ratio_blur


# --------------------------------------------------------------------------- #
# 6) 対照群と標識の置き場所                                                    #
# --------------------------------------------------------------------------- #
def section6_control_and_layout():
    print()
    print("=" * 78)
    print("6) ★★対照群 —— 正対化の残差はどこから来るか")
    print("=" * 78)
    print("  M2 の残差の候補は 2 つ: (a) warp の再標本化 + 二値化 (b) 標識から")
    print("  推定したホモグラフィの誤差。**(b) を止めた条件**(真の H で正対化 = M3)")
    print("  を測れば分けられる。")
    print()
    print("  %-22s %10s %10s" % ("場面", "M2 %", "M3(真H) %"))
    print("  " + "-" * 44)
    e2, e3 = [], []
    for name, spec, area in SCENES:
        hw = scene_h(spec)
        img = render(hw, area)
        m = measure_all(img, LAYOUT_SIDE, 1.0, h_true=hw)
        e2.append(100 * (m["M2"] / area - 1))
        e3.append(100 * (m["M3"] / area - 1))
        print("  %-22s %+10.2f %+10.2f" % (name, e2[-1], e3[-1]))
    print()
    print("  → ★★再標本化 + 二値化の床は最大 %.2f %%。M2 の残差(最大 %.2f %%)は"
          % (max(abs(x) for x in e3), max(abs(x) for x in e2)))
    print("     **ほぼ全部が推定ホモグラフィの誤差**。標識の重心のずれは 0.1 px 台")
    print("     なのに、面積では 1〜2 % になる —— 標識(30 mm 角)から創面(中心間")
    print("     61 mm)まで**外挿**しているため。")
    print()
    print("  同じ場面で標識の置き場所だけを変える:")
    print()
    print("  %-24s %10s %10s %10s" % ("配置", "平均|誤差|%", "最大|誤差|%", "点誤差px"))
    print("  " + "-" * 58)
    lay = {}
    for name, dots in (("横 30 mm 角(中心間 61mm)", LAYOUT_SIDE),
                       ("創面を囲む 104 mm 角", LAYOUT_AROUND)):
        err, derr = [], []
        for _, spec, area in SCENES:
            hw = scene_h(spec)
            img = render(hw, area, dots=dots)
            m = measure_all(img, dots, 1.0, h_true=hw)
            err.append(abs(100 * (m["M2"] / area - 1)))
            derr.append(m["dot_err"])
        lay[name] = (float(np.mean(err)), float(np.max(err)))
        print("  %-24s %10.2f %10.2f %10.3f" % (name, np.mean(err), np.max(err), np.max(derr)))
    k1, k2 = list(lay)
    print()
    print("  → ★★**標識は測る場所を囲め**。平均 |誤差| が %.2f %% → %.2f %%(%.1f 倍)。"
          % (lay[k1][0], lay[k2][0], lay[k1][0] / max(lay[k2][0], 1e-9)))
    print("     4 点の重心のずれは同じ 0.1 px 台なのに、囲めば内挿になるので効かない。")
    return e2, e3, lay


# --------------------------------------------------------------------------- #
# 7) 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section7_gaps():
    print()
    print("=" * 78)
    print("7) 道具の穴 —— fullseye に無かったもの / 使いにくかったもの")
    print("=" * 78)
    print("""
  (a) ★★**平面ホモグラフィの推定と適用が、公開層のどこにも揃っていない**。
      画像を歪める側 `fs.ledger.warp_by_plane` は在る(この PoC が使った)。
      **推定する側**は `fit_transform.hom_vector_to_proj_hom_mat2d` /
      `calib.vector_to_hom_mat2d` / `calib.image_to_world_plane` がモジュールに
      在るのに、`fullseye` にも `fullseye.ledger` にも出ていない。`import
      fit_transform` と書かないと平面計測が組めない。**推定と適用が別の層に
      いるのは、この repo が繰り返している「実装は在るが公開経路が無い」形**。
      (`poc_matrix_code_reading` が同じ穴を別角度から報告している。)

  (b) ★`warp_by_plane` に**出力の大きさを指定する口が無い**。出力は入力と同じ
      形で固定。正対化は「mm/px を決めて必要な画角ぶん出す」操作なので、
      出力 shape を決められないと、画素の細かさと視野を独立に選べない。
      この PoC は 0.25 mm/px を選んだ結果、視野が 100x75 mm に固定された。

  (c) ★`blob_features(spacing=…)` は**スカラーしか受けない**。傾いた面を
      部分的にしか直していない像は**行と列で画素の大きさが違う**が、
      `spacing=(0.05, 0.10)` は `TypeError` で落ちる。3-D 側の `label_components`
      は異方ボクセルを想定しているのに、2-D 側には無い。

  (d) **較正標識を「読む」op が無い**。`fs.scale_bar` / `fs.annotate_scale_bar` は
      スケールバーを**描く**。撮った絵からスケールバーや基準寸法を**読み取って**
      mm/px を返す op は 3 層のどこにも無い(`op_find("scale")` は描画側と
      `normalize_scale` しか返さない)。この PoC は blob 族で自作した。

  (e) **面積に較正の不確かさを伝播させる口が無い**。この PoC の中心的な事実
      —— σ_A/A = 2·σ_L/L —— は 3 行で書けるが、`blob_features` は面積を
      返すだけで、`spacing` の不確かさを一緒に運ぶ形になっていない。
      計測 op の出口が「値 + 不確かさ」の対だったら、2 節の事故は型で防げる。
""")
    # 現状を機械で固定する(直ったら落ちる = 良い落ち方)
    assert hasattr(fs.ledger, "warp_by_plane"), "適用側まで消えた"
    for name in ("hom_vector_to_proj_hom_mat2d", "vector_to_hom_mat2d",
                 "image_to_world_plane", "contour_to_world_plane_xld"):
        assert not hasattr(fs, name), "%s が公開された(この節を書き換えること)" % name
        assert not hasattr(fs.ledger, name), "%s が台帳に出た(良い変化)" % name
    import inspect
    assert "shape" not in inspect.signature(fs.ledger.warp_by_plane.__wrapped__).parameters \
        if hasattr(fs.ledger.warp_by_plane, "__wrapped__") else True
    import plane_sweep
    assert "out_shape" not in inspect.signature(plane_sweep.warp_by_plane).parameters, \
        "出力形を選べるようになった(この節を書き換えること)"
    lab = fs.ledger.blob_label(np.pad(np.ones((6, 6), bool), 3))
    try:
        fs.ledger.blob_features(lab, spacing=(0.05, 0.10))
        raise AssertionError("異方 spacing が通った(良い変化。この節を書き換えること)")
    except TypeError:
        pass
    assert hasattr(fs, "scale_bar") and not hasattr(fs, "read_scale_bar")
    assert not hasattr(fs.ledger, "read_scale_bar")


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    print("poc_wound_area_tracking — 面積の経時変化は較正の誤差が 2 乗で効く")
    print("(真値 = mm 平面の星形閉曲線。面積は閉形式、画像は逆投影で内外判定)")
    print()
    floor = section1_floor()
    mm_fixed, dev_law, dev_lin = section2_zero_point()
    rows, worst = section3_methods(mm_fixed)
    tab = section4_healing_constant()
    series, ratio_sharp, ratio_blur = section5_sensitivity()
    e2, e3, lay = section6_control_and_layout()
    section7_gaps()

    figs.save_table("summary",
                    ["手法", "k 推定", "標準偏差", "k の偏り %", "面積 最大誤差 %"],
                    [["M0 1 枚目だけで較正", "%.4f" % tab["M0"][0], "%.4f" % tab["M0"][1],
                      "%+.1f" % tab["M0"][2], "%.1f" % worst["M0"]],
                     ["M1 毎回 長さで較正", "%.4f" % tab["M1"][0], "%.4f" % tab["M1"][1],
                      "%+.1f" % tab["M1"][2], "%.1f" % worst["M1"]],
                     ["M2 毎回 正対化", "%.4f" % tab["M2"][0], "%.4f" % tab["M2"][1],
                      "%+.1f" % tab["M2"][2], "%.1f" % worst["M2"]],
                     ["真値", "%.4f" % K_TRUE, "-", "0.0", "%.2f" % floor]],
                    title="治癒定数 k と面積の誤差(%d seed x %d 日)" % (N_SEED, N_DAY),
                    caption="ゼロ点は散らばりがいちばん小さく、偏りがいちばん大きい。")

    print()
    print("=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  ・ラスタライズの床           %.3f %%" % floor)
    print("  ・2 乗則との差(最大)        %.3f pp / 線形近似との差 %.2f pp" % (dev_law, dev_lin))
    print("  ・k の偏り  M0 %+.1f %% / M1 %+.1f %% / M2 %+.1f %%"
          % (tab["M0"][2], tab["M1"][2], tab["M2"][2]))
    print("  ・感度比    較正 / しきい値 = %.1f 倍(鋭い縁)・%.1f 倍(ぼけた縁)"
          % (ratio_sharp, ratio_blur))
    print("  ・正対化の床(真の H)       %.2f %% / 推定 H %.2f %%"
          % (max(abs(x) for x in e3), max(abs(x) for x in e2)))
    print("  ・標識を囲む配置にすると平均 |誤差| %.2f %% → %.2f %%"
          % (lay["横 30 mm 角(中心間 61mm)"][0], lay["創面を囲む 104 mm 角"][0]))
    assert floor < 0.5, floor
    assert dev_law < 0.5 <= dev_lin, (dev_law, dev_lin)
    assert tab["M0"][2] > 15.0, tab["M0"]
    assert abs(tab["M2"][2]) < 5.0, tab["M2"]
    assert tab["M0"][1] < tab["M1"][1], (tab["M0"], tab["M1"])
    assert ratio_sharp > 3.0 and ratio_blur > 2.0, (ratio_sharp, ratio_blur)
    assert max(abs(x) for x in e3) < 0.5 < max(abs(x) for x in e2), (e3, e2)
    assert lay["創面を囲む 104 mm 角"][0] < lay["横 30 mm 角(中心間 61mm)"][0], lay
    assert len(rows) == len(SCENES) and len(series) == 3

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\n経過 %.1f 秒" % (time.time() - t0))
    print("\nPASS")


if __name__ == "__main__":
    main()
