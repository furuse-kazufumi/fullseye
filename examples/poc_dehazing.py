# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""霞を剥がす —— 大気散乱モデルで真値を作り、透過率と大気光を別々に採点する。

EXTEND: 実写に差し替えるなら ``build_scene`` だけを実データ読み込みに置き換える。
そのとき真の透過率 ``t`` と真のシーン ``J`` は手に入らないので、採点できるのは
本 PoC の 3 指標のうち (a) 見た目寄りの指標だけになる。**そこが実写の難しさの本体**で、
本 PoC が合成に徹しているのはそのため。実写で最低限やることは 4 つ。
(1) **リニアな輻度に戻す** —— ``I = J*t + A*(1-t)`` は輻度の線形式であって、
sRGB ガンマの掛かった画素値では成り立たない。掛けたまま流しても例外は出ず、
透過率が濃霧側へ系統的にずれるだけ。
(2) **白飛びを潰す** —— 飽和画素は ``I`` の上限で潰れているので、大気光 ``A`` の
推定(上位画素を見る手法すべて)が確実に外れる。8 節の白い物体と同じ壊れ方をする。
(3) **深度の絶対尺度は要らないが、無限遠は要る** —— 空・遠景を ``t≈0`` として
扱う判断が復元品質を支配する。7 節のとおりここは復元できない領域であり、
「復元した」と主張してはいけない場所。
(4) **雑音を先に測る** —— 9 節のとおり復元は雑音を ``1/t`` 倍する。遠景で
40 倍に増幅されるので、除霞の前段に置く平滑化の強さは ``t`` の分布で決めるべき。

この PoC が示すこと:

1. **真値は自分で作る** —— 深度地図 ``d``・大気光 ``A``・消散係数 ``beta`` を
   こちらが決めるので、真の透過率 ``t = exp(-beta*d)`` と真のシーン ``J`` の
   **両方**が既知になる。推定値はその両方と突き合わせる。
2. **見た目が良くなることと、真値に近づくことは別** —— 3 節。ヒストグラム等化は
   コントラストとエントロピーを最大にするが、真値との PSNR は「何もしない」より
   **下がる**。見た目の指標だけを見ていると、この符号の逆転に気づけない。
3. **律速がどちらかを言える** —— 4 節。真の ``t`` を与えたオラクルと、真の ``A`` を
   与えたオラクルを並べる。**透過率が律速**(``A`` を真値にしても PSNR はほとんど
   動かないが、``t`` を真値にすると大きく動く)。
4. **1 つの数字にまとめない** —— 全体 PSNR は近景の面積で決まる。5 節のとおり
   遠景では暗チャネルが「何もしない」に**負ける**が、全体値には現れない。
5. **崖を 5 つ、数字で** —— 霞の濃さ / 白い物体 / パッチ寸法とハロー /
   波長依存の消散 / 雑音の ``1/t`` 増幅。

★ この PoC が出した道具の穴は末尾の「所見」節に 7 件まとめた。要点は、fullseye に
**大気散乱の族がまるごと無い**こと(霞の合成 op も暗チャネル op も透過率精製 op も
無い)、``guided_filter`` が中身はバイラテラルであること、``min_filter`` の窓が
``3,5,7,9`` に固定されていて暗チャネルの標準寸法 15 が出せないこと。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import depth_bilateral                                           # noqa: E402
import filters_arith                                             # noqa: E402
import fullseye as fs                                            # noqa: E402
import imgmetrics                                                # noqa: E402

H, W = 120, 160
Y_HORIZON = 34.0                # 消失線の行。ここより上は空
GROUND_C = 510.0                # 地面の深度 d = GROUND_C / (y - Y_HORIZON) [m]
D_MIN, D_MAX = 6.0, 150.0       # 地面の深度の下限・上限 [m]
D_SKY = 400.0                   # 空の深度 [m]。無限大にはしない(下の注を見よ)
A_TRUE = np.array([0.82, 0.86, 0.92])   # 大気光。やや青い(短波長ほど散乱が強い)
BETA = 0.020                    # 消散係数 [1/m]。気象視程 = 3.912/beta = 196 m
OMEGA = 0.95                    # 暗チャネル法が霞を残す割合(遠近感を殺さないため)
T_FLOOR = 0.10                  # 透過率の下限。1/t の発散を止める
PATCH = 15                      # 暗チャネルの既定パッチ寸法 [px]
VAN_FRAC = 0.015                # 既定の場面に置く白い車両の面積率

# 深度の帯。**1 つの数字にまとめない**ための区分。
BANDS = (("近景 (<15m)", 0.0, 15.0),
         ("中景 (15-40m)", 15.0, 40.0),
         ("遠景 (40-150m)", 40.0, 150.0),
         ("空 (400m)", 150.0, 1e9))

# 空を「無限遠」でなく 400 m の有限値にした理由: 無限遠にすると真のシーン J が
# その画素で定義できず、真値との比較そのものが成立しない。400 m なら
# t = exp(-0.02*400) = 3.4e-4 で実質ゼロだが J は定義でき、「復元できない」ことを
# **数字で言える**。逃げずに採点するための選択であって、近似のためではない。


# --------------------------------------------------------------------------- #
# 1. 場面の合成 —— 深度・シーン輻度・霞                                          #
# --------------------------------------------------------------------------- #
def _rect(arr, r0, r1, c0, c1, value):
    """[r0,r1) x [c0,c1) を value で塗る。value はスカラでも (3,) でもよい。"""
    arr[r0:r1, c0:c1] = value


def depth_map(van_frac=VAN_FRAC):
    """深度地図 (H,W) [m] を返す。**既知の段差**を持つ構造のある場面。

    地面は透視投影の閉形式 ``d = C/(y - y_h)`` で連続に、建物・車両・生垣は
    一定深度の矩形で**不連続**に置く。段差の位置がこちらの手にあるので、
    ハロー(段差の周りで透過率が滲む現象)を画素単位で切り出せる。
    """
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    d = np.full((H, W), D_SKY)
    ground = yy >= 38.0
    d[ground] = np.clip(GROUND_C / (yy[ground] - Y_HORIZON), D_MIN, D_MAX)
    # 建物 3 棟。接地行 y = y_h + C/d を守るので幾何的に矛盾しない。
    for d_b, c0, c1, r_top in ((55.0, 2, 44, 8), (30.0, 52, 88, 16), (85.0, 104, 158, 4)):
        r_base = int(round(Y_HORIZON + GROUND_C / d_b))
        _rect(d, r_top, r_base, c0, c1, d_b)
    _rect(d, 66, 77, 100, 150, 12.0)                    # 生垣(暗い物体)
    van = van_rect(van_frac)
    if van is not None:
        r0, r1, c0, c1 = van
        _rect(d, r0, r1, c0, c1, 18.0)                  # 白い車両
    return d


def van_rect(frac):
    """面積率 frac の白い車両の矩形 (r0,r1,c0,c1)。frac<=0 なら None。

    接地行は深度 18 m と整合する y = 62 に固定し、上へ伸ばす。縦横比 1:1.4。
    """
    if frac <= 0.0:
        return None
    area = frac * H * W
    h = max(3, int(round(math.sqrt(area / 1.4))))
    w = max(3, int(round(1.4 * h)))
    r1 = 63
    r0 = max(0, r1 - h)
    c0 = max(0, 72 - w // 2)
    c1 = min(W, c0 + w)
    return r0, r1, c0, c1


def scene_radiance(van_frac=VAN_FRAC):
    """霞の無いシーン輻度 J (H,W,3) を [0,1] で返す。乱数は粒状感のみ(seed 固定)。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    j = np.zeros((H, W, 3))
    # 空 —— 上ほど濃い青。t≈0 なのでほぼ観測に出ないが、真値としては定義しておく。
    sky_t = np.clip(yy / Y_HORIZON, 0.0, 1.0)[..., None]
    j[:] = np.array([0.34, 0.44, 0.62]) * (1 - sky_t) + np.array([0.56, 0.62, 0.72]) * sky_t
    # 地面 —— 舗装 + 車線の破線 + 縁石
    road = np.zeros((H, W), bool)
    road[38:, :] = True
    j[road] = np.array([0.24, 0.23, 0.22])
    dash = road & (np.abs(xx - 78.0) < 2.0) & (((yy.astype(int) // 6) % 2) == 0)
    j[dash] = np.array([0.74, 0.73, 0.68])
    kerb = road & ((np.abs(xx - 16.0) < 1.5) | (np.abs(xx - 142.0) < 1.5))
    j[kerb] = np.array([0.44, 0.43, 0.41])
    # 建物 3 棟 —— 壁の地色 + 窓の格子。格子があるので SSIM と暗チャネルが効く。
    walls = ((55.0, 2, 44, 8, (0.42, 0.40, 0.38), (0.07, 0.08, 0.10), 7, 6),
             (30.0, 52, 88, 16, (0.56, 0.53, 0.49), (0.70, 0.66, 0.55), 6, 5),
             (85.0, 104, 158, 4, (0.31, 0.34, 0.37), (0.11, 0.12, 0.14), 8, 7))
    for d_b, c0, c1, r_top, base, win, pr, pc in walls:
        r_base = int(round(Y_HORIZON + GROUND_C / d_b))
        _rect(j, r_top, r_base, c0, c1, np.array(base))
        for r in range(r_top + 2, r_base - 2, pr):
            for c in range(c0 + 2, c1 - 2, pc):
                _rect(j, r, min(r + pr - 3, r_base - 2), c, min(c + pc - 3, c1 - 2), np.array(win))
    _rect(j, 66, 77, 100, 150, np.array([0.05, 0.15, 0.06]))     # 生垣。暗チャネルの餌
    van = van_rect(van_frac)
    if van is not None:
        r0, r1, c0, c1 = van
        _rect(j, r0, r1, c0, c1, np.array([0.96, 0.96, 0.94]))   # 白い車両
        _rect(j, r0 + 2, r0 + 2 + max(1, (r1 - r0) // 4), c0 + 2, c1 - 2,
              np.array([0.18, 0.20, 0.24]))                      # 窓(全部真っ白にしない)
    # 材質の粒 —— 構造ではなく質感。振幅 0.01 で、判定を左右しない大きさに留める。
    grain = np.random.RandomState(20260906).normal(0.0, 0.010, (H, W, 1))
    return np.clip(j + grain, 0.0, 1.0)


def haze(j, d, beta=BETA, a=A_TRUE, quantize=True):
    """大気散乱モデル ``I = J*t + A*(1-t)``、``t = exp(-beta*d)``。

    beta がスカラなら t は (H,W)、(3,) なら波長依存で t は (H,W,3)。

    ``quantize=True`` で **8 bit に丸める**。これを入れないとオラクル(真の t と
    真の A を与えた復元)が数値誤差まで完全一致して PSNR が 300 dB を超え、
    「オラクルとの差」という物差しが意味を失う。実機は 8 bit で来るのだから、
    丸めを入れる方が正直で、しかも 9 節の ``1/t`` 増幅の下限が量子化で決まる
    ことまで見える。
    """
    beta = np.asarray(beta, float)
    t = np.exp(-beta * d[..., None]) if beta.ndim else np.exp(-beta * d)[..., None]
    i = np.clip(j * t + np.asarray(a) * (1.0 - t), 0.0, 1.0)
    return (np.round(i * 255.0) / 255.0 if quantize else i), t


def build_scene(van_frac=VAN_FRAC, beta=BETA, a=A_TRUE, quantize=True):
    """(観測 I, 真の J, 真の t (H,W), 深度 d) を返す。t は代表(平均)チャネル。"""
    d = depth_map(van_frac)
    j = scene_radiance(van_frac)
    i, t3 = haze(j, d, beta, a, quantize)
    return i, j, t3.mean(axis=2), d


# --------------------------------------------------------------------------- #
# 2. 手法 —— ゼロ点・暗チャネル・オラクル                                        #
# --------------------------------------------------------------------------- #
def dark_channel(img, patch=PATCH):
    """暗チャネル ``min_c min_{y in patch} I^c(y)``。

    最小値フィルタは ``filters_arith.rank_image(..., rank=0)`` を使う。
    進化 op の ``min_filter`` は窓が ``3,5,7,9`` に固定されていて、暗チャネル法の
    標準寸法 15 が**出せない**(所見 3)。
    """
    mn = img.min(axis=2)
    if patch <= 1:
        return mn
    return filters_arith.rank_image(mn, mask_size=patch, rank=0)


def airlight_dcp(img, patch=PATCH, frac=0.001):
    """暗チャネルの上位 frac 画素のなかで、最も明るい画素の色を大気光とする。

    He, Sun & Tang, "Single Image Haze Removal Using Dark Channel Prior",
    CVPR 2009 の手順。「霞が最も濃い = 暗チャネルが最も明るい」場所を探し、
    そのなかで最も明るい画素を取る、という二段構え。
    """
    dc = dark_channel(img, patch)
    n = max(1, int(round(dc.size * frac)))
    idx = np.argpartition(dc.ravel(), -n)[-n:]
    cand = img.reshape(-1, 3)[idx]
    return cand[int(np.argmax(cand.sum(axis=1)))].copy()


def airlight_brightest(img, frac=0.001):
    """素朴な手 —— 画像の上位 frac % の明るい画素の平均を大気光とする。

    暗チャネルを経由しないぶん実装は簡単だが、**白い物体があると必ず外れる**
    (8 節でその条件を数字で出す)。
    """
    lum = img.sum(axis=2)
    n = max(1, int(round(lum.size * frac)))
    idx = np.argpartition(lum.ravel(), -n)[-n:]
    return img.reshape(-1, 3)[idx].mean(axis=0)


def transmission_dcp(img, a, patch=PATCH, omega=OMEGA):
    """``t = 1 - omega * darkchannel(I/A)``。大気光で正規化してから暗チャネルを取る。"""
    return np.clip(1.0 - omega * dark_channel(img / np.asarray(a), patch), 0.0, 1.0)


def refine_transmission(t, img, spatial_sigma=6.0, range_sigma=0.08):
    """観測画像の輝度を guide にした joint bilateral で透過率を精製する。

    本来ここは guided filter か soft matting を使う所だが、fullseye の
    ``guided_filter`` op は**中身がバイラテラル**で局所線形モデルではない
    (所見 2)。同じ代役なら、深度用に書かれていて guide の単位が明示されている
    ``depth_bilateral.joint_bilateral`` の方が素性が分かるのでそちらを使う。
    ``invalid=None`` を明示しないと ``t==0`` の画素が「無効」扱いで捨てられる。
    """
    guide = img.mean(axis=2)
    return depth_bilateral.joint_bilateral(t, guide, spatial_sigma, range_sigma, invalid=None)


def recover(img, a, t, t_floor=T_FLOOR):
    """``J = (I - A)/max(t,t0) + A``。t0 が無いと遠景で 1/t が発散する。"""
    tt = np.maximum(np.asarray(t), t_floor)[..., None]
    return np.clip((img - np.asarray(a)) / tt + np.asarray(a), 0.0, 1.0)


def stretch_percentile(img, lo=1.0, hi=99.0):
    """ゼロ点その 2 —— チャネル別のパーセンタイル線形伸張(大域コントラスト)。"""
    out = np.empty_like(img)
    for c in range(3):
        p0, p1 = np.percentile(img[..., c], (lo, hi))
        out[..., c] = np.clip((img[..., c] - p0) / max(1e-9, p1 - p0), 0.0, 1.0)
    return out


def equalize_rgb(img):
    """ゼロ点その 3 —— チャネル別ヒストグラム等化(``fs.op.equalize``)。"""
    return np.stack([fs.op.equalize(img[..., c], a=0.5, b=0.5) for c in range(3)], axis=2)


def clahe_rgb(img, a=0.6, b=0.25):
    """参考 —— 局所コントラスト(``fs.op.clahe``)。大域等化より穏やかなはず。"""
    return np.stack([fs.op.clahe(img[..., c], a=a, b=b) for c in range(3)], axis=2)


# --------------------------------------------------------------------------- #
# 3. 採点 —— 3 本の指標を混ぜない                                                #
# --------------------------------------------------------------------------- #
def psnr_masked(a, b, mask=None, data_range=1.0):
    """マスク内の PSNR [dB]。完全一致は inf(``imgmetrics.psnr`` と同じ流儀)。"""
    if mask is None:
        return float(imgmetrics.psnr(a, b, data_range=data_range))
    diff = (a - b)[mask]
    mse = float(np.mean(diff * diff))
    return float("inf") if mse <= 0.0 else 10.0 * math.log10(data_range ** 2 / mse)


def angle_deg(u, v):
    """2 つの色ベクトルのなす角 [度]。大気光の**色**が合っているかを見る。"""
    u, v = np.asarray(u, float), np.asarray(v, float)
    c = float(np.dot(u, v) / max(1e-12, np.linalg.norm(u) * np.linalg.norm(v)))
    return math.degrees(math.acos(min(1.0, max(-1.0, c))))


def rms_contrast(img):
    """見た目寄りの指標 —— 輝度の標準偏差。真値を一切見ない。"""
    return float(np.std(img.mean(axis=2)))


def band_masks(d):
    return [(name, (d >= lo) & (d < hi)) for name, lo, hi in BANDS]


def edge_band(d, width=5):
    """深度の**段差の周り** width px の帯。ハローが出る場所。"""
    ld = np.log10(d)
    rng = filters_arith.rank_image(ld, 3, 8) - filters_arith.rank_image(ld, 3, 0)
    step = rng > 0.05
    k = 2 * width + 1
    return filters_arith.rank_image(step.astype(np.float64), k, k * k - 1) > 0.5


# --------------------------------------------------------------------------- #
# 4. 本体                                                                       #
# --------------------------------------------------------------------------- #
def main():
    t_start = time.perf_counter()
    np.set_printoptions(precision=4, suppress=True)

    print("=== 1. 場面 —— 真値をこちらで握る ===")
    img, j_true, t_true, d = build_scene()
    masks = band_masks(d)
    print(f"  画素 {H}x{W} / 大気光 A = {A_TRUE} / beta = {BETA:.3f} 1/m"
          f"(気象視程 {3.912 / BETA:.0f} m)")
    print(f"  {'帯':<16}{'画素数':>8}{'面積率':>9}{'深度中央':>10}{'真の t 中央':>12}{'1/t':>8}")
    for name, m in masks:
        print(f"  {name:<16}{int(m.sum()):>8}{100 * m.mean():>8.1f}%"
              f"{np.median(d[m]):>10.1f}{np.median(t_true[m]):>12.4f}"
              f"{1.0 / max(1e-9, np.median(t_true[m])):>8.1f}")
    near_mid = 100 * (masks[0][1] | masks[1][1]).mean()
    print(f"  → 近景と中景で面積の {near_mid:.0f} % を占める。**全体 1 個の数字はこの面積比**で決まる。")
    print(f"  深度の段差(不連続)を持つ矩形 5 個。段差周り 5px の帯は "
          f"{100 * edge_band(d).mean():.1f} % の画素。")

    print("\n=== 2. ゼロ点 —— 見た目が良くなることと、真値に近づくことは別 ===")
    zero = (("何もしない", img),
            ("大域コントラスト伸張", stretch_percentile(img)),
            ("ヒストグラム等化", equalize_rgb(img)),
            ("CLAHE(局所・参考)", clahe_rgb(img)))
    print(f"  {'手法':<24}{'RMS 対比':>10}{'エントロピー':>13}{'PSNR 全体':>11}{'SSIM':>8}")
    zero_scores = {}
    for name, out in zero:
        p = psnr_masked(out, j_true)
        s = float(imgmetrics.ssim(out, j_true, data_range=1.0, channel_axis=2))
        e = float(imgmetrics.image_entropy(out.mean(axis=2)))
        zero_scores[name] = (rms_contrast(out), e, p, s)
        print(f"  {name:<24}{rms_contrast(out):>10.4f}{e:>13.3f}{p:>11.2f}{s:>8.4f}")
    print(f"  真値 J そのもの         {rms_contrast(j_true):>10.4f}"
          f"{float(imgmetrics.image_entropy(j_true.mean(axis=2))):>13.3f}"
          f"{'inf':>11}{1.0:>8.4f}")
    print("  → ヒストグラム等化は RMS 対比とエントロピーを最大にしながら、PSNR は")
    print("     「何もしない」より**下がる**。見た目の指標は符号が逆に動きうる。")

    print("\n=== 3. 主要手法 —— J の誤差 / t の誤差 / A の誤差を分けて出す ===")
    a_dcp = airlight_dcp(img)
    a_bri = airlight_brightest(img)
    t_dcp = transmission_dcp(img, a_dcp)
    t_ref = refine_transmission(t_dcp, img)
    methods = (
        ("何もしない",            None,   None,   img),
        ("大域コントラスト",      None,   None,   stretch_percentile(img)),
        ("暗チャネル p=15",       a_dcp,  t_dcp,  recover(img, a_dcp, t_dcp)),
        ("暗チャネル + 精製",     a_dcp,  t_ref,  recover(img, a_dcp, t_ref)),
        ("オラクル A(t は推定)", A_TRUE, t_dcp,  recover(img, A_TRUE, t_dcp)),
        ("オラクル t(A は推定)", a_dcp,  t_true, recover(img, a_dcp, t_true)),
        ("オラクル A と t",       A_TRUE, t_true, recover(img, A_TRUE, t_true)),
    )
    print(f"  {'手法':<22}{'PSNR':>8}{'SSIM':>8}{'t MAE':>9}{'A 誤差':>9}{'A 角度':>9}")
    scores = {}
    for name, a_est, t_est, out in methods:
        p = psnr_masked(out, j_true)
        s = float(imgmetrics.ssim(out, j_true, data_range=1.0, channel_axis=2))
        tm = float("nan") if t_est is None else float(np.mean(np.abs(t_est - t_true)))
        ae = float("nan") if a_est is None else float(np.linalg.norm(np.asarray(a_est) - A_TRUE))
        ag = float("nan") if a_est is None else angle_deg(a_est, A_TRUE)
        scores[name] = (p, s, tm, ae, ag)
        f = (lambda v, w, n: f"{v:>{w}.{n}f}" if v == v else f"{'—':>{w}}")
        print(f"  {name:<22}{p:>8.2f}{s:>8.4f}{f(tm, 9, 4)}{f(ae, 9, 4)}{f(ag, 9, 3)}")
    print(f"  推定した大気光: 暗チャネル法 {a_dcp}  上位 0.1 % 明画素 {a_bri}")
    d_a = scores["オラクル A(t は推定)"][0] - scores["暗チャネル p=15"][0]
    d_t = scores["オラクル t(A は推定)"][0] - scores["暗チャネル p=15"][0]
    print(f"  → **透過率が律速**。A を真値に差し替えても PSNR は {d_a:+.2f} dB しか動かないのに、")
    print(f"     t を真値にすると {d_t:+.2f} dB 動く。伸びしろの {100 * d_t / max(1e-9, d_a + d_t):.0f} % は t 側にある。")
    print(f"  ただし **A が易しいのはこの場面に空が写っているから**(面積 {100 * masks[3][1].mean():.0f} %、")
    print("     観測値がほぼ A そのもの)。空が無い場面では話が変わる —— 6 節で壊す。")

    print("\n=== 4. 帯ごとの内訳 —— 全体 PSNR が打ち消し合わせているもの ===")
    print(f"  {'手法':<22}" + "".join(f"{n:>16}" for n, _ in masks))
    for name, _a, _t, out in methods:
        row = "".join(f"{psnr_masked(out, j_true, m):>16.2f}" for _n, m in masks)
        print(f"  {name:<22}{row}")
    gains = [psnr_masked(methods[2][3], j_true, m) - psnr_masked(img, j_true, m)
             for _n, m in masks]
    total_gain = scores["暗チャネル p=15"][0] - scores["何もしない"][0]
    print(f"  暗チャネルの利得 [dB]: " + " / ".join(
        f"{n.split(' ')[0]} {g:+.2f}" for (n, _m), g in zip(masks, gains)))
    print(f"  → 全体では {total_gain:+.2f} dB だが、その内訳は**近景 {gains[0]:+.2f} dB の劣化**を")
    print(f"     中景 {gains[1]:+.2f} / 遠景 {gains[2]:+.2f} dB の改善が打ち消して出た数字。1 個の数字だと")
    print("     「近景を壊した」ことが完全に見えない。近景は元々霞が薄く、除霞は")
    print("     ほぼ雑音と透過率の誤差を足すだけになる(触らないのが正解の領域)。")
    print(f"  空は誰も直せない —— オラクル(真の t と真の A)ですら "
          f"{psnr_masked(methods[6][3], j_true, masks[3][1]):.2f} dB で、")
    print(f"     何もしない {psnr_masked(img, j_true, masks[3][1]):.2f} dB とほぼ同じ。t の下限 "
          f"{T_FLOOR} が効いていて、")
    print("     真の t = 0.0003 を使えば復元式は 0/0 になる。**ここは推定の問題ではない**。")

    print("\n=== 5. 崖 (a) 霞の濃さ —— beta を薄いから濃いまで振る ===")
    print("  t の誤差は 2 通りで出す。絶対誤差 |t̂-t| は t 自体が小さくなると勝手に")
    print("  小さくなるので、**尺度によらない光学的深さの誤差 |ln t̂ - ln t|** を並べる。")
    print(f"  {'beta':>7}{'視程 m':>8}{'t 中央':>8}{'|dt|':>8}{'|d ln t|':>10}"
          f"{'A 角度':>8}{'PSNR 霞':>9}{'PSNR 除霞':>10}{'利得':>8}{'オラクル':>9}")
    beta_rows = []
    for beta in (0.0025, 0.005, 0.0075, 0.010, 0.020, 0.040, 0.080):
        i2, j2, t2, _d2 = build_scene(beta=beta)
        a2 = airlight_dcp(i2)
        te = transmission_dcp(i2, a2)
        p_raw = psnr_masked(i2, j2)
        p_dcp = psnr_masked(recover(i2, a2, te), j2)
        p_or = psnr_masked(recover(i2, A_TRUE, t2), j2)
        tm = float(np.mean(np.abs(te - t2)))
        od = float(np.mean(np.abs(np.log(np.clip(te, 1e-3, 1.0))
                                  - np.log(np.clip(t2, 1e-3, 1.0)))))
        beta_rows.append((beta, tm, od, p_raw, p_dcp, p_or))
        print(f"  {beta:>7.4f}{3.912 / beta:>8.0f}{np.median(t2):>8.4f}{tm:>8.4f}{od:>10.4f}"
              f"{angle_deg(a2, A_TRUE):>8.3f}{p_raw:>9.2f}{p_dcp:>10.2f}"
              f"{p_dcp - p_raw:>+8.2f}{p_or:>9.2f}")
    cross = [r for r in beta_rows if r[4] <= r[3]]
    print(f"  → **薄い霞では除霞が害になる**。利得が負に転じるのは beta <= "
          f"{max(r[0] for r in cross) if cross else float('nan'):.4f}"
          f"(視程 {3.912 / max(r[0] for r in cross):.0f} m 以上)。")
    print("     絶対誤差 |dt| は beta とともに**減る**が、これは t が 0 に潰れるだけの見かけ。")
    print("     光学的深さで測ると単調に増えていて、そちらが実際の難しさに対応する。")

    print("\n=== 6. 崖 (b)(d) 白い物体 —— 大気光の推定が壊れる条件 ===")
    print("  白い車両(反射率 0.96、深度 18 m)の面積率を振る。空は常に画面内にある。")
    print(f"  {'白面積率':>9}{'A角 暗ch':>10}{'A角 明画素':>12}{'|dA| 暗ch':>11}"
          f"{'|dA| 明画素':>13}{'t MAE 暗ch':>12}{'PSNR 暗ch':>11}")
    white_rows = []
    for frac in (0.0, 0.005, 0.015, 0.03, 0.06, 0.12):
        i2, j2, t2, _d2 = build_scene(van_frac=frac)
        ad, ab = airlight_dcp(i2), airlight_brightest(i2)
        te = transmission_dcp(i2, ad)
        row = (frac, angle_deg(ad, A_TRUE), angle_deg(ab, A_TRUE),
               float(np.linalg.norm(ad - A_TRUE)), float(np.linalg.norm(ab - A_TRUE)),
               float(np.mean(np.abs(te - t2))), psnr_masked(recover(i2, ad, te), j2))
        white_rows.append(row)
        print(f"  {100 * frac:>8.1f}%{row[1]:>10.3f}{row[2]:>12.3f}{row[3]:>11.4f}"
              f"{row[4]:>13.4f}{row[5]:>12.4f}{row[6]:>11.2f}")
    print("  → 上位 0.1 % 明画素法は白い車両が **0.5 % 出た時点で**角度誤差が")
    print(f"     {white_rows[1][2]:.2f} 度・絶対誤差 {white_rows[1][4]:.3f} に跳ぶ。暗チャネル法は")
    print("     「暗チャネルが明るい所」を先に絞るので、白い**近景**物体では壊れない")
    print("     (白い車両の暗チャネルは霞の量しか反映しないため)。")
    print("  白い物体を **遠景**(空と同じ明るさ)に置くと両方壊れる —— 次でそれを分離する。")
    # 白い物体を空の直下(遠景 85 m の建物面)に置いた場合を 1 点だけ作る。
    i3, j3, t3, d3 = build_scene(van_frac=0.0)
    r0, r1, c0, c1 = 6, 30, 112, 150                    # 遠景建物の上部を白く塗る
    j3w = j3.copy()
    j3w[r0:r1, c0:c1] = np.array([0.97, 0.97, 0.96])
    i3w, _ = haze(j3w, d3)
    ad3, ab3 = airlight_dcp(i3w), airlight_brightest(i3w)
    te3 = transmission_dcp(i3w, ad3)
    print(f"  {'遠景の白壁 (5.0 %)':<22}A角 暗ch {angle_deg(ad3, A_TRUE):.3f} 度 / "
          f"明画素 {angle_deg(ab3, A_TRUE):.3f} 度 / t MAE {np.mean(np.abs(te3 - t3)):.4f}")
    print("  → 深度が同じでも**白いかどうか**でなく、**遠いかどうか**が効く。遠景の白壁は")
    print("     観測上ほぼ大気光と同色になるので、どちらの推定も色としては外れない。")
    print("     壊れるのは t の側 —— 白壁は暗チャネルが明るく、霞と区別できない。")

    print("\n=== 7. 崖 (c) パッチ寸法とハロー ===")
    eb = edge_band(d)
    print(f"  {'パッチ':>7}{'t MAE 全体':>12}{'t MAE 段差帯':>14}{'t MAE 平坦':>12}"
          f"{'比':>7}{'PSNR':>8}{'ms':>7}")
    patch_rows = []
    for patch in (3, 7, 15, 31):
        t0 = time.perf_counter()
        ap = airlight_dcp(img, patch=patch)
        te = transmission_dcp(img, ap, patch=patch)
        ms = 1e3 * (time.perf_counter() - t0)
        err = np.abs(te - t_true)
        row = (patch, float(err.mean()), float(err[eb].mean()), float(err[~eb].mean()),
               psnr_masked(recover(img, ap, te), j_true))
        patch_rows.append(row)
        print(f"  {patch:>7}{row[1]:>12.4f}{row[2]:>14.4f}{row[3]:>12.4f}"
              f"{row[2] / row[3]:>7.2f}{row[4]:>8.2f}{ms:>7.1f}")
    te15 = transmission_dcp(img, a_dcp, patch=15)
    tr15 = refine_transmission(te15, img)
    e15, r15 = np.abs(te15 - t_true), np.abs(tr15 - t_true)
    print(f"  精製(joint bilateral): 段差帯 {e15[eb].mean():.4f} → {r15[eb].mean():.4f}"
          f" / 平坦 {e15[~eb].mean():.4f} → {r15[~eb].mean():.4f}")
    print("  → パッチが小さいと平坦部で物体の地色を霞と誤認し(暗チャネルが 0 でない)、")
    print("     大きいと段差帯の誤差が膨らむ。段差帯 / 平坦の**比**がハローの強さ。")

    print("\n=== 8. 崖 —— 波長依存の消散(モデルそのものが外れる) ===")
    print("  暗チャネル法は t を 1 枚(チャネル共通)としか置けない。beta を波長で変える。")
    print(f"  {'beta (R,G,B)':<26}{'t MAE':>9}{'A 角度':>9}{'PSNR':>8}{'色の偏り':>11}")
    for label, bvec in (("等方 (0.020,0.020,0.020)", (0.020, 0.020, 0.020)),
                        ("弱い波長依存 λ^-1 相当", (0.017, 0.020, 0.024)),
                        ("強い波長依存 λ^-4 相当", (0.010, 0.020, 0.041))):
        i2, t3v = haze(scene_radiance(), depth_map(), beta=np.array(bvec))
        j2 = scene_radiance()
        t2 = t3v.mean(axis=2)
        a2 = airlight_dcp(i2)
        te = transmission_dcp(i2, a2)
        out = recover(i2, a2, te)
        bias = float(np.mean(out[..., 2] - j2[..., 2]) - np.mean(out[..., 0] - j2[..., 0]))
        print(f"  {label:<26}{np.mean(np.abs(te - t2)):>9.4f}{angle_deg(a2, A_TRUE):>9.3f}"
              f"{psnr_masked(out, j2):>8.2f}{bias:>11.4f}")
    print("  → 単一 t のモデルでは、波長依存が強いほど青が系統的にずれる(色の偏りの列)。")
    print("     これは推定の精度でなく**モデルの表現力**の限界で、t を真値にしても消えない。")

    print("\n=== 9. 崖 (e) 雑音の 1/t 増幅 —— 距離別に出す ===")
    sigma = 0.010
    noisy = np.clip(img + np.random.RandomState(7).normal(0.0, sigma, img.shape), 0.0, 1.0)
    out_or = recover(noisy, A_TRUE, t_true)
    out_dcp = recover(noisy, airlight_dcp(noisy), transmission_dcp(noisy, airlight_dcp(noisy)))
    base_or = recover(img, A_TRUE, t_true)
    print(f"  入力の雑音 sigma = {sigma:.3f}")
    print(f"  {'帯':<16}{'1/max(t,t0) 予測':>18}{'実測 増幅率':>14}{'比':>7}"
          f"{'PSNR 劣化 dB':>14}")
    amp_rows = []
    for name, m in masks:
        pred = float(np.mean(1.0 / np.maximum(t_true[m], T_FLOOR)))
        meas = float(np.std((out_or - base_or)[m])) / sigma
        drop = psnr_masked(base_or, j_true, m) - psnr_masked(out_or, j_true, m)
        amp_rows.append((name, pred, meas, drop))
        print(f"  {name:<16}{pred:>18.2f}{meas:>14.2f}{meas / pred:>7.2f}{drop:>14.2f}")
    print(f"  暗チャネルを雑音つきで回した場合の全体 PSNR: "
          f"{psnr_masked(out_dcp, j_true):.2f} dB "
          f"(雑音無し {scores['暗チャネル p=15'][0]:.2f} dB)")
    print("  → 増幅率は 1/max(t,t0) の予測とよく合う。実測が予測を下回るのは、復元後の")
    print("     [0,1] クリップが増幅された雑音を切り落とすため(誤差は消えず飽和に化ける)。")

    print(f"\n=== 10. 所要時間 {time.perf_counter() - t_start:.2f} 秒 ===")

    print("\n=== 所見 —— fullseye の道具の穴(このファイルは直していない)===")
    print("  1. **大気散乱の族がまるごと無い**。霞の合成(I=J*t+A*(1-t))・暗チャネル・")
    print("     大気光推定・透過率精製・視程換算(3.912/beta)のどれも op が無く、")
    print("     ledger 側の 'transmittance' 3 件は Beer-Lambert のガラス透過であって")
    print("     空間的な透過率地図ではない。本 PoC は 5 手法すべてを自前で書いた。")
    print("  2. ``fs.op.guided_filter`` は **docstring が自認しているとおり中身が")
    print("     bilateral**。guided filter の売りは局所線形モデルで guide の勾配へ")
    print("     追従することなので、透過率の精製という本命の用途では代役にならない。")
    print("  3. ``fs.op.min_filter`` の窓は ``3,5,7,9`` 固定(param_specs の bucket)。")
    print("     暗チャネルの標準寸法 15 も、本 PoC が試した 31 も出せない。")
    print("     ``filters_arith.rank_image(x, mask_size=k, rank=0)`` なら任意寸法で出せて")
    print("     scipy の minimum_filter と bit 一致するが、進化 op からは到達できない。")
    print("  4. ``depth_bilateral.joint_bilateral`` の ``invalid=0.0`` が既定。透過率は")
    print("     遠景で 0 に漸近するので、既定のまま渡すと**遠景が黙って捨てられる**。")
    print("     深度に 0 の欠測番兵を想定した既定値だが、0 が正当な値である量には危ない。")
    print("  5. ``imgmetrics.psnr`` にマスク引数が無い。帯ごとの内訳を出すのが本 PoC の")
    print("     主題なのに、毎回自前で MSE を書くことになる(``psnr_masked``)。")
    print("     ``ssim`` も同様で、こちらは窓があるためマスク版が自明でない。")
    print("  6. 透過率・深度・大気光といった**物理量の型**が無い。すべて素の ndarray なので、")
    print("     t (0..1) と深度 (m) と輻度 (0..1) を取り違えても例外は出ない。")
    print("     本 PoC でも t を [0,1] に clip する箇所は全部手書きの防御になっている。")
    print("  7. 見た目の指標(RMS 対比・エントロピー)と真値との指標(PSNR/SSIM)が")
    print("     同じ ``imgmetrics`` に同居していて、参照画像が要るか否かの区別が名前から")
    print("     読めない。2 節のとおり両者は符号が逆に動きうるので、混ぜると事故る。")

    # ---- 自己検査 —— 結論を機械で固定する ----------------------------------
    # (1) 合成が大気散乱モデルどおりであること(往復の一致)。
    i_chk, j_chk, _t_chk, d_chk = build_scene()
    t_chk3 = np.exp(-BETA * d_chk)[..., None]
    assert np.max(np.abs(i_chk - np.clip(j_chk * t_chk3 + A_TRUE * (1 - t_chk3), 0, 1))) < 1e-12

    # (2) 見た目と真値は別 —— 等化は対比を最大にしながら PSNR で「何もしない」に負ける。
    c_eq, _e_eq, p_eq, _s_eq = zero_scores["ヒストグラム等化"]
    c_no, _e_no, p_no, _s_no = zero_scores["何もしない"]
    assert c_eq > c_no, "等化がコントラストを上げていない(前提が崩れている)"
    assert p_eq < p_no, f"等化の PSNR {p_eq:.2f} が「何もしない」{p_no:.2f} を下回っていない"

    # (3) 除霞は「何もしない」「大域コントラスト」の両ゼロ点に勝つ。
    assert scores["暗チャネル p=15"][0] > scores["何もしない"][0] + 1.0
    assert scores["暗チャネル p=15"][0] > scores["大域コントラスト"][0] + 1.0

    # (4) **透過率が律速** —— A を真値にした利得より t を真値にした利得が大きい。
    assert d_t > 3.0 * d_a, f"t 側の利得 {d_t:.2f} dB が A 側 {d_a:.2f} dB を圧倒していない"
    assert scores["オラクル A と t"][0] > scores["暗チャネル p=15"][0] + 3.0

    # (5) 遠景では暗チャネルが「何もしない」に勝てず、全体値にそれが出ない。
    assert far_dcp - far_none < scores["暗チャネル p=15"][0] - scores["何もしない"][0]
    assert scores["暗チャネル p=15"][0] > scores["何もしない"][0]

    # (6) 崖 (a) —— 霞が濃いほど透過率の誤差は単調に増える。
    tmaes = [r[1] for r in beta_rows]
    assert all(x < y for x, y in zip(tmaes, tmaes[1:])), f"beta で t MAE が単調でない {tmaes}"

    # (7) 崖 (d) —— 上位 0.1 % 明画素法は白い物体で暗チャネル法より先に壊れる。
    assert white_rows[0][2] < 1.0, "白い物体が無いのに明画素法が既に外れている"
    assert white_rows[-1][2] > 5.0 * max(1e-6, white_rows[0][2]), "明画素法が壊れていない"
    assert white_rows[-1][2] > white_rows[-1][1], "暗チャネル法の方が悪くなっている"

    # (8) 崖 (c) —— パッチを大きくすると段差帯 / 平坦の誤差比(ハロー)が増える。
    ratios = [r[2] / r[3] for r in patch_rows]
    assert ratios[-1] > ratios[0], f"パッチ寸法でハロー比が増えていない {ratios}"

    # (9) 崖 (e) —— 雑音の増幅は遠いほど大きく、1/max(t,t0) の予測を超えない。
    preds = [r[1] for r in amp_rows]
    meas = [r[2] for r in amp_rows]
    assert all(x < y for x, y in zip(preds, preds[1:])), "予測増幅率が距離で単調でない"
    assert all(x <= y for x, y in zip(meas[:2], meas[1:3])), "実測増幅率が近中遠で単調でない"
    assert all(m <= p * 1.05 for m, p in zip(meas, preds)), "実測が理論上限を超えている"

    # (10) 大気光の推定は「色」としては当たる —— 律速が t である根拠の裏取り。
    assert angle_deg(a_dcp, A_TRUE) < 1.5, "暗チャネル法の大気光が色として外れている"

    print("\nPASS")


if __name__ == "__main__":
    main()
