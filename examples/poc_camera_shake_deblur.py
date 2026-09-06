# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""手ブレはどこまで戻せるか —— 核を自分で作り、掛けて、戻して、元と比べる。

EXTEND: 実写真に差し替えるなら ``scene()`` の戻り値を ``fs.to_float01(fs.load(path))``
(グレースケール、[0,1])に置き換える。ただし **実写真には真値が無い** ので、この PoC
が出す数字のうち意味を保つのは 5 章(リンギング)と 7 章(速度)だけになる。実写真で
上限を測りたいなら「三脚で撮った静止画を真値、同じ構図を手持ちで撮った画を観測」に
するのが最短で、その場合は位置合わせ(``fs.register``)を先に通すこと —— 1 画素の
ずれは PSNR で 3 dB 前後効く。ブレ核を実測したいなら暗所で点光源(遠くの街灯)を
撮れば、その輝点の像がそのまま核になる。

この PoC が示すこと:

1. **核が厳密に既知でも、雑音が上限を決める** —— 無雑音なら循環モデルの逆畳み込みは
   ほぼ完全に戻る(22.4 dB の観測が 56.4 dB へ)。雑音を入れた瞬間に上限が落ち、
   SNR 60 / 40 / 30 / 20 dB でゼロ点に対する取り分は 15.5 / 6.5 / 3.8 / **1.8 dB**
   まで縮む。最良の正則化量 nsr は理論値(雑音電力 / 信号電力)と同じ桁で並んで
   動く —— 「雑音が多いほど高周波を諦める」が最適解の中身。
2. ★**ゼロ点に負ける領域がある** —— 「何もしない」と「アンシャープマスク」をゼロ点に
   置くと、15 px の直線ブレで **角度が 19.2 度ずれるとアンシャープマスクに、19.4 度で
   「何もしない」にも抜かれる**。長さは **4.4 px 過大**でゼロ点以下。取り分が半分に
   落ちる時点はもっと手前で、角度 5.0 度 / 長さ 1.3 px(核長の 9 %)しかない。
   核を **推定した** 場合(2 次元ケプストラム)
   は SNR 40 dB なら既知との差 0.5 dB で済むが、SNR 15 dB で推定が外れた瞬間に
   20.3 dB —— **ゼロ点(22.2 dB)を割る**。
3. **回転ブレはそもそも 1 枚の核で書けない** —— 並進ブレと違って場所ごとに核が違う。
   ある半径・方位で作った核で全画面を戻すと、そこは +6.2 dB 良くなる一方、反対側は
   -4.2 dB、直交側は -6.8 dB、ほぼブレていない回転中心は -49.4 dB と **戻すどころか
   悪化**する。「ブレ除去」と一括りにできない境目がここにある。
4. **リンギングは境界条件で決まる** —— 前向きモデルと同じ循環畳み込みなら縁の誤差は
   内部の 0.74 倍(縁の方が良い)だが、現実の(非循環な)ブレを循環モデルで戻すと
   1.80 倍に反転する。強いエッジのオーバーシュートは正則化で 30.7 % から 9.7 % まで
   減らせるが、その代わり PSNR が 28.9 dB から 27.2 dB へ落ちる —— それが値段。

★ この PoC が出した道具の穴(op 本体は直していない):

(a) **利用者から呼べる 2-D の逆畳み込みは ``fs.cx_wiener_deconvolve`` 1 つだけ**。
    Richardson-Lucy は 2-D 版が ``fs.op.iv_richardson_lucy`` /
    ``fs.op.xsk_richardson_lucy`` の 2 つあるが、**どちらも核を受け取らない**
    (前者は固定 sigma のガウス、後者は固定 3x3 の箱を仮定)。核を渡せる RL は
    ``fs.vol_richardson_lucy``(3-D)だけで、``(1, H, W)`` の板として渡せば通るが、
    零詰めの畳み込みが前提なので **循環ブレを渡すと観測より悪化する**(2 章の末尾に
    実測を出す)。2-D で核を取る RL が無いのは穴。
(b) **ブレ核の生成器が facade から呼べない**。``filters_freq.gen_psf_motion`` と
    ``gen_psf_defocus``、``backends_inverse._motion_psf`` は実在するのに、
    ``fs.ledger`` にも ``fs`` 直下にも出ていない。この PoC は 3 種類の核を全部
    自前で作った(``psf_line`` / ``psf_shake`` / ``psf_arc``)。
(c) **任意カーネルの 2-D 畳み込み op が無い**。``fs.ledger`` で ``conv`` を含む名前は
    凸包と 1-D の装置応答だけ。前向きモデル(ブレを掛ける側)も自前で書くしかない。
(d) **核推定(ブラインド)の手掛かりが無い**。ケプストラムは 1-D 音響側
    (``acoustics.cepstrum``)にしかなく、2-D のスペクトル零線から核長・角度を読む
    経路が無い。この PoC は ``estimate_line_kernel`` を自前で書いた(20 行)。
    直線ブレなら SNR 20 dB まで 0.1 px / 1 度で当たるので、op として置く価値がある。
(e) ``fs.cx_wiener_deconvolve`` は戻り値を ``[0, 1]`` に切り詰める。**負側の
    リンギングが見えなくなる**ので、アンダーシュート量を測る用途には使えない
    (この PoC の 5 章はオーバーシュート側だけを測っている)。
(f) コア op ``unsharp`` の docstring が **空**。同じ働きの ``xpil_unsharp_mask`` /
    ``xkor_unsharp`` には説明があるのに、素の ``unsharp`` だけ何も書かれていない。
    さらに category が ``smoothing`` になっている(鮮鋭化なのに)。
"""
from __future__ import annotations

import math
import time

import numpy as np

import fullseye as fs

SEED = 20260906
DR = 1.0                      # data_range。真値も観測も [0, 1] に載せる


# --------------------------------------------------------------------------- #
# 1. 真値 —— 構造のある場面(乱数だけの場面は対称性の破れを隠す)                 #
# --------------------------------------------------------------------------- #
def scene(n=256):
    """既知の真値。強いエッジ・細線・周波数の階段・なめらかな勾配を 1 枚に載せる。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    img = 0.22 + 0.10 * (yy / (n - 1))                      # なめらかな勾配

    img[40:110, 40:110] = 0.75                              # 強いエッジを持つ矩形
    r = np.hypot(yy - 0.28 * n, xx - 0.72 * n)
    img[r < 0.13 * n] = 0.62                                # 円板

    for k, x0 in enumerate(range(30, 230, 26)):             # 幅が増える縦縞
        w = 1 + k // 2
        img[150:200, x0:x0 + w] = 0.80

    th = np.arctan2(yy - 0.78 * n, xx - 0.24 * n)           # 放射状のスポーク
    rr = np.hypot(yy - 0.78 * n, xx - 0.24 * n)
    spoke = (np.cos(12 * th) > 0) & (rr < 0.16 * n)
    img[spoke] = 0.70

    img[215:218, 30:226] = 0.30                             # 細い横線
    return np.clip(img, 0.0, 1.0)


def scene_rotation(n=256, radius=70):
    """回転ブレ用の真値。**同じ絵柄**を中心から等距離の 4 方位に置く。

    場所ごとの良し悪しを比べるので、絵柄が違うと「核が合っていないのか」
    「そこに戻すものが無いのか」を分けられない。同じ絵柄なら分けられる。
    """
    img = np.full((n, n), 0.25)
    c = n // 2
    for dy, dx in ((0, radius), (0, -radius), (radius, 0), (-radius, 0)):
        y, x = c + dy, c + dx
        img[y - 9:y + 10, x - 2:x + 3] = 0.85               # 十字(縦棒)
        img[y - 2:y + 3, x - 9:x + 10] = 0.85               # 十字(横棒)
        img[y - 13:y - 10, x - 12:x + 13] = 0.60            # 帯(向きが分かる印)
    return img


# --------------------------------------------------------------------------- #
# 2. ブレ核 —— 直線・折れ曲がり(手ブレ風)・回転(局所)                        #
# --------------------------------------------------------------------------- #
def _splat(k, y, x, w):
    """(y, x) に重み w を双一次で撒く。核を 1 画素刻みで作ると角度が量子化される。"""
    h, wd = k.shape
    y0, x0 = int(math.floor(y)), int(math.floor(x))
    fy, fx = y - y0, x - x0
    for dy, wy in ((0, 1.0 - fy), (1, fy)):
        for dx, wx in ((0, 1.0 - fx), (1, fx)):
            iy, ix = y0 + dy, x0 + dx
            if 0 <= iy < h and 0 <= ix < wd:
                k[iy, ix] += w * wy * wx


def _finish(k):
    s = float(k.sum())
    if s <= 0.0:
        raise ValueError("核の総和が 0 —— 台紙が小さすぎて軌跡がはみ出した")
    return k / s


def psf_line(length, angle_deg, pad=3):
    """直線ブレ。露光中にセンサが等速で滑った場合の核。角度 0 度 = 横方向。"""
    L = float(length)
    ks = int(2 * math.ceil(L / 2 + pad) + 1)
    c = ks // 2
    k = np.zeros((ks, ks))
    t_ = np.deg2rad(float(angle_deg))
    dy, dx = math.sin(t_), math.cos(t_)
    n = max(64, int(24 * L))
    for t in np.linspace(-(L - 1) / 2.0, (L - 1) / 2.0, n):
        _splat(k, c + t * dy, c + t * dx, 1.0)
    return _finish(k)


def psf_shake(waypoints, pad=3, n=1200):
    """手ブレ風の折れ曲がった軌跡。等速でなく、折れ点の近くに露光が溜まる。

    ``waypoints`` は (行, 列) の画素座標の折れ線。実際の手ブレは加速度が
    連続なのでもっと滑らかだが、「直線でない」ことの効きを見るにはこれで足りる。
    """
    p = np.asarray(waypoints, dtype=np.float64)
    p = p - p.mean(axis=0)
    seg = np.diff(p, axis=0)
    leng = np.hypot(seg[:, 0], seg[:, 1])
    total = float(leng.sum())
    span = float(np.abs(p).max())
    ks = int(2 * math.ceil(span + pad) + 1)
    c = ks // 2
    k = np.zeros((ks, ks))
    for t in np.linspace(0.0, total, n):                  # 弧長で等間隔 = 等速露光
        acc, i = 0.0, 0
        while i < len(leng) - 1 and acc + leng[i] < t:
            acc += leng[i]
            i += 1
        u = 0.0 if leng[i] <= 0 else (t - acc) / leng[i]
        q = p[i] + u * seg[i]
        _splat(k, c + q[0], c + q[1], 1.0)
    return _finish(k)


def _rotmat(deg):
    """(行, 列) ベクトルに掛ける回転行列。正の角で内容が反時計回りに回る向き。"""
    t_ = math.radians(float(deg))
    c, s = math.cos(t_), math.sin(t_)
    return np.array([[c, -s], [s, c]])


def psf_arc(radius, sweep_deg, pad=3, n=400):
    """回転ブレの **その場所だけの** 核。中心から (0, radius) 離れた点の軌跡。

    回転ブレはシフト不変でない —— 核は半径にも方位にも依存する。この関数が返すのは
    「中心の右 radius 画素の 1 点で成り立つ核」であって、画面全体の核ではない。
    """
    v = np.array([0.0, float(radius)])
    offs = [v - _rotmat(-th) @ v for th in np.linspace(0.0, float(sweep_deg), n)]
    span = max(float(np.abs(np.asarray(offs)).max()), 1.0)
    ks = int(2 * math.ceil(span + pad) + 1)
    c = ks // 2
    k = np.zeros((ks, ks))
    for s in offs:
        _splat(k, c + s[0], c + s[1], 1.0)
    return _finish(k)


# --------------------------------------------------------------------------- #
# 3. 前向きモデル(ブレを掛ける側)と雑音                                        #
# --------------------------------------------------------------------------- #
def _otf(psf, shape):
    """核を画像サイズの台紙に置き、中心を原点へ転がす。復元側と同じ約束にする。"""
    pad = np.zeros(shape)
    ph, pw = psf.shape
    pad[:ph, :pw] = psf
    pad = np.roll(pad, (-(ph // 2), -(pw // 2)), axis=(0, 1))
    return np.fft.fft2(pad)


def blur_circular(img, psf):
    """循環畳み込み。復元側のモデルと **完全に一致** する理想化した観測。"""
    return np.real(np.fft.ifft2(np.fft.fft2(img) * _otf(psf, img.shape)))


def blur_padded(img, psf):
    """反射パディングの畳み込み。現実のブレはこちら側(画面外から画が流れ込む)。"""
    ph, pw = psf.shape
    my, mx = ph, pw
    big = np.pad(img, ((my, my), (mx, mx)), mode="reflect")
    out = blur_circular(big, psf)
    return out[my:my + img.shape[0], mx:mx + img.shape[1]]


def rotate_bilinear(img, deg):
    """内容を deg だけ回す。端は最寄り値で押さえる(回転ブレの前向きモデル用)。"""
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    m = _rotmat(-deg)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    sy = m[0, 0] * (yy - cy) + m[0, 1] * (xx - cx) + cy
    sx = m[1, 0] * (yy - cy) + m[1, 1] * (xx - cx) + cx
    sy = np.clip(sy, 0, h - 1)
    sx = np.clip(sx, 0, w - 1)
    y0 = np.floor(sy).astype(int); x0 = np.floor(sx).astype(int)
    y1 = np.minimum(y0 + 1, h - 1); x1 = np.minimum(x0 + 1, w - 1)
    fy = sy - y0; fx = sx - x0
    return ((1 - fy) * ((1 - fx) * img[y0, x0] + fx * img[y0, x1])
            + fy * ((1 - fx) * img[y1, x0] + fx * img[y1, x1]))


def blur_rotational(img, sweep_deg, n=41):
    """本物の回転ブレ。1 枚の核では書けない —— 回した像を平均するのが定義。"""
    acc = np.zeros_like(img)
    for th in np.linspace(0.0, float(sweep_deg), n):
        acc += rotate_bilinear(img, th)
    return acc / n


def add_noise(img, snr_db, rng):
    """SNR = 10 log10(観測の分散 / 雑音の分散)。無限大なら雑音を足さない。"""
    if not np.isfinite(snr_db):
        return img.copy(), 0.0
    sig = float(np.var(img))
    sd = math.sqrt(sig / (10.0 ** (float(snr_db) / 10.0)))
    return img + sd * rng.standard_normal(img.shape), sd


# --------------------------------------------------------------------------- #
# 4. 復元とゼロ点                                                              #
# --------------------------------------------------------------------------- #
def psnr(gt, est):
    return fs.psnr(gt, np.clip(est, 0.0, 1.0), data_range=DR)


def q(gt, est):
    """(PSNR [dB], SSIM)。どちらも fullseye の台帳 op。"""
    e = np.clip(est, 0.0, 1.0)
    return fs.psnr(gt, e, data_range=DR), fs.ssim(gt, e, data_range=DR)


NSR_GRID = np.logspace(-8.0, -0.3, 28)


def wiener_best(obs, psf, gt):
    """核を渡して正則化量だけを最良化(神託)。復元側に有利な条件で上限を測る。"""
    best = (-1.0, None, None)
    for nsr in NSR_GRID:
        est = fs.cx_wiener_deconvolve(obs, psf, nsr=float(nsr))
        p = psnr(gt, est)
        if p > best[0]:
            best = (p, float(nsr), est)
    return best


UNSHARP_GRID = [(a, b) for a in (0.15, 0.3, 0.5, 0.7, 0.9, 1.0)
                for b in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)]


def unsharp_best(obs, gt):
    """ゼロ点その 2。**神託で最良のつまみを選ぶ** ので、ゼロ点側に有利な測り方。"""
    best = (-1.0, None, None)
    x = np.clip(obs, 0.0, 1.0)
    for a, b in UNSHARP_GRID:
        est = fs.op.unsharp(x, a=a, b=b)
        p = psnr(gt, est)
        if p > best[0]:
            best = (p, (a, b), est)
    return best


def crossing(xs, ys, level):
    """ys が level を下回る x を線形補間で 1 つ返す(見つからなければ None)。"""
    for i in range(1, len(xs)):
        if ys[i - 1] >= level > ys[i]:
            t = (ys[i - 1] - level) / (ys[i - 1] - ys[i])
            return xs[i - 1] + t * (xs[i] - xs[i - 1])
    return None


def estimate_line_kernel(obs, rmin=4.0, rmax=45.0):
    """真値を見ずに直線ブレの核を読む —— 対数振幅スペクトルの逆変換の負のピーク。

    直線ブレは周波数領域で ``sinc`` の零線を刻む。対数を取ってから逆変換すると
    その周期性が **負のピーク** として実空間に立ち、その位置が軌跡の端から端まで
    の変位そのものになる。窓を掛けるのは画像の縁の不連続が十字状の偽ピークを
    立てるため。★ この 20 行に相当する op が fullseye には無い(道具の穴 d)。
    """
    x = np.asarray(obs, float)
    x = x - x.mean()
    win = np.outer(np.hanning(x.shape[0]), np.hanning(x.shape[1]))
    ceps = np.real(np.fft.ifft2(np.log(np.abs(np.fft.fft2(x * win)) + 1e-9)))
    ceps = np.fft.fftshift(ceps)
    h, w = ceps.shape
    c0, c1 = h // 2, w // 2
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(yy - c0, xx - c1)
    masked = np.where((r >= rmin) & (r <= rmax), ceps, np.inf)
    iy, ix = np.unravel_index(int(np.argmin(masked)), ceps.shape)
    dy, dx = iy - c0, ix - c1
    # ピークは「端から端までの変位」= psf_line の長さ引く 1 に対応する。
    return math.hypot(dy, dx) + 1.0, math.degrees(math.atan2(dy, dx)) % 180.0


# --------------------------------------------------------------------------- #
# 本体                                                                         #
# --------------------------------------------------------------------------- #
def main():
    rng = np.random.default_rng(SEED)
    gt = scene(256)

    kernels = {
        "直線 L=15 20 度": psf_line(15, 20.0),
        "手ブレ(折れ線)": psf_shake([(0, 0), (2.5, 6.0), (-1.0, 10.5), (3.5, 14.0)]),
        "回転(局所)r=70": psf_arc(70.0, 6.0),
    }

    print("=== 1. 3 種類のブレ核 —— 真値は自分で決めているので完璧に分かる ===")
    print(f"  {'核':<18}{'台紙':>10}{'重心の広がり':>14}{'掛けた後 PSNR':>15}{'SSIM':>9}")
    for name, k in kernels.items():
        yy, xx = np.mgrid[0:k.shape[0], 0:k.shape[1]]
        cy = float((k * yy).sum()); cx = float((k * xx).sum())
        spread = math.sqrt(float((k * ((yy - cy) ** 2 + (xx - cx) ** 2)).sum()))
        b = blur_circular(gt, k)
        p, s = q(gt, b)
        print(f"  {name:<18}{str(k.shape):>10}{spread:>14.2f}{p:>15.2f}{s:>9.4f}")
    print("  → 広がりが大きいほど落ちる。手ブレの折れ線は同じ画素数を動いても")
    print("     直線より広がりが小さい(折り返しで自分の上に戻るため)。")

    print("\n=== 2. ゼロ点 —— 何もしない / アンシャープマスク / 核既知の復元 ===")
    print("  (SNR 40 dB、循環ブレ。アンシャープも Wiener も神託でつまみを最良化)")
    print(f"  {'核':<18}{'何もしない':>12}{'アンシャープ':>14}{'核既知':>10}{'取り分':>9}")
    for name, k in kernels.items():
        obs, _ = add_noise(blur_circular(gt, k), 40.0, np.random.default_rng(SEED))
        p_null = psnr(gt, obs)
        p_uns, _, _ = unsharp_best(obs, gt)
        p_win, _, _ = wiener_best(obs, k, gt)
        print(f"  {name:<18}{p_null:>12.2f}{p_uns:>14.2f}{p_win:>10.2f}"
              f"{p_win - max(p_null, p_uns):>9.2f}")
    print("  → 核が正しければ復元はゼロ点を明確に上回る。ここが勝てる領域。")
    print("     アンシャープマスクは 1 dB も稼げない —— 高周波を持ち上げても、")
    print("     ブレで潰れた零点は元に戻らない(掛け算の逆をしていないため)。")

    # 道具の穴 (a) の実測 —— 核を渡せる RL は 3-D 版しかなく、板にすると通るが負ける
    k0 = kernels["直線 L=15 20 度"]
    obs_rl, _ = add_noise(blur_circular(gt, k0), 40.0, np.random.default_rng(SEED))
    slab = np.clip(obs_rl, 0.0, 1.0)[None, :, :]
    rl = fs.vol_richardson_lucy(slab, k0[None, :, :], iterations=20)[0]
    print(f"  ★ 核を渡せる Richardson-Lucy は 3-D 版だけ。(1, H, W) の板にすると通るが")
    print(f"     {psnr(gt, rl):.2f} dB —— 何もしない {psnr(gt, obs_rl):.2f} dB より悪い。")
    print("     3-D 版は零詰めの畳み込みが前提で、循環ブレとは前向きモデルが違うため")
    print("     (道具の穴 a)。2-D で核を取る RL が無い、が本当の問題。")

    k_ref = kernels["直線 L=15 20 度"]
    blurred = blur_circular(gt, k_ref)

    print("\n=== 3. 雑音が上限を決める(核は厳密に既知)===")
    print(f"  {'SNR [dB]':>9}{'観測':>9}{'アンシャープ':>13}{'核既知':>9}{'取り分':>8}"
          f"{'最良 nsr':>11}{'理論 nsr':>11}")
    gains = {}
    for snr in (math.inf, 60.0, 40.0, 30.0, 20.0):
        obs, sd = add_noise(blurred, snr, np.random.default_rng(SEED + 1))
        p_null = psnr(gt, obs)
        p_uns, _, _ = unsharp_best(obs, gt)
        p_win, nsr, _ = wiener_best(obs, k_ref, gt)
        theory = (sd ** 2) / float(np.var(gt)) if sd > 0 else 0.0
        gains[snr] = p_win - max(p_null, p_uns)
        lab = "無雑音" if not np.isfinite(snr) else f"{snr:.0f}"
        print(f"  {lab:>9}{p_null:>9.2f}{p_uns:>13.2f}{p_win:>9.2f}"
              f"{gains[snr]:>8.2f}{nsr:>11.2e}{theory:>11.2e}")
    print("  → 無雑音なら循環モデルの逆はほぼ完全に戻る(核が完全に既知だから)。")
    print("     雑音を入れると上限が一気に落ち、20 dB では取り分が 2 dB を切る。")
    print("     最良 nsr は理論値(雑音電力 / 信号電力)と同じ桁に並ぶ —— 雑音が")
    print("     大きいほど強く正則化する = 高周波を諦める、が最適解の中身。")

    print("\n=== 4. 核の推定誤差 —— どれだけずれると破綻するか ===")
    obs40, _ = add_noise(blurred, 40.0, np.random.default_rng(SEED + 2))
    p_null40 = psnr(gt, obs40)
    p_uns40, uns_ab, _ = unsharp_best(obs40, gt)
    print(f"  ゼロ点: 何もしない {p_null40:.2f} dB / "
          f"アンシャープ(神託 a={uns_ab[0]}, b={uns_ab[1]}) {p_uns40:.2f} dB")
    print(f"  {'角度ずれ [度]':>13}{'PSNR':>9}{'対 何もしない':>15}{'対 アンシャープ':>17}")
    ang_x, ang_y = [], []
    for d in (0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0,
              16.0, 18.0, 20.0, 25.0, 30.0, 45.0):
        p, _, _ = wiener_best(obs40, psf_line(15, 20.0 + d), gt)
        ang_x.append(d); ang_y.append(p)
        print(f"  {d:>13.0f}{p:>9.2f}{p - p_null40:>15.2f}{p - p_uns40:>17.2f}")
    ang_break_uns = crossing(ang_x, ang_y, p_uns40)
    ang_break_null = crossing(ang_x, ang_y, p_null40)
    print(f"  {'長さずれ [px]':>13}{'PSNR':>9}{'対 何もしない':>15}{'対 アンシャープ':>17}")
    len_x, len_y = [], []
    for d in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0):
        p, _, _ = wiener_best(obs40, psf_line(15 + d, 20.0), gt)
        len_x.append(d); len_y.append(p)
        print(f"  {d:>13.0f}{p:>9.2f}{p - p_null40:>15.2f}{p - p_uns40:>17.2f}")
    len_break_null = crossing(len_x, len_y, p_null40)
    ang_half = crossing(ang_x, ang_y, p_null40 + 0.5 * (ang_y[0] - p_null40))
    len_half = crossing(len_x, len_y, p_null40 + 0.5 * (len_y[0] - p_null40))
    print(f"  → 角度が {ang_break_uns:.1f} 度ずれるとアンシャープマスクに抜かれ、"
          f"{ang_break_null:.1f} 度で「何もしない」にも抜かれる。")
    print(f"     長さは {len_break_null:.1f} px 過大でゼロ点以下。**現場で効くのは"
          "この 2 つの数字**。")
    print(f"     取り分が半分に落ちる時点はもっと手前で、角度 {ang_half:.1f} 度 / "
          f"長さ {len_half:.1f} px(核長 15 px の {100 * len_half / 15:.0f} %)しかない。")
    print("     角度がずれると核の台紙そのものがすれ違うので、破綻は角度の方が急。")

    print("\n=== 4b. 核を推定する場合(真値を一切見ない)===")
    print(f"  {'真の核':>18}{'推定した核':>18}{'推定核で':>10}{'既知なら':>10}{'差':>8}")
    ok_est = 0
    for L, a in ((9.0, 0.0), (15.0, 20.0), (21.0, 70.0), (25.0, 135.0)):
        k_t = psf_line(L, a)
        ob, _ = add_noise(blur_circular(gt, k_t), 40.0, np.random.default_rng(SEED + 5))
        eL, ea = estimate_line_kernel(ob)
        p_e, _, _ = wiener_best(ob, psf_line(eL, ea), gt)
        p_t, _, _ = wiener_best(ob, k_t, gt)
        ok_est += int(p_t - p_e < 1.0)
        print(f"  {f'{L:.0f} px {a:.0f} 度':>18}{f'{eL:.1f} px {ea:.1f} 度':>18}"
              f"{p_e:>10.2f}{p_t:>10.2f}{p_t - p_e:>8.2f}")
    print("  → 対数スペクトルの逆変換(2 次元ケプストラム)で読むと、SNR 40 dB では")
    print("     4 件とも当たり、既知の核との差は 1 dB 未満で済む。ただしこれは")
    print("     **直線ブレという形を仮定できているから**であって、折れ線の手ブレでは")
    print("     零線が単純な縞にならず同じ手は使えない。")
    print(f"  {'SNR [dB]':>9}{'推定した核':>18}{'ゼロ点':>9}{'推定核で':>10}"
          f"{'既知なら':>10}{'差':>8}")
    est_noise = {}
    for snr in (40.0, 30.0, 20.0, 15.0):
        ob, _ = add_noise(blurred, snr, np.random.default_rng(SEED + 6))
        eL, ea = estimate_line_kernel(ob)
        p_e, _, _ = wiener_best(ob, psf_line(eL, ea), gt)
        p_t, _, _ = wiener_best(ob, k_ref, gt)
        p_0 = psnr(gt, ob)
        est_noise[snr] = (eL, ea, p_e, p_t, p_0)
        print(f"  {snr:>9.0f}{f'{eL:.1f} px {ea:.1f} 度':>18}{p_0:>9.2f}"
              f"{p_e:>10.2f}{p_t:>10.2f}{p_t - p_e:>8.2f}")
    print("  → 雑音が増えると零線が埋もれて推定が外れ、外れた瞬間に 4 章の許容範囲を")
    print("     突き抜けて **ゼロ点を割る**。核の推定と雑音は独立でなく、")
    print("     **雑音が核推定を壊し、壊れた核が復元を殺す** 二段構えで死ぬ。")

    print("\n=== 5. リンギング —— 縁の悪化は境界条件で決まる ===")
    print("  (核は厳密に既知・SNR 40 dB。nsr を固定して条件をそろえる)")
    print(f"  {'ブレの掛け方':<20}{'nsr':>9}{'PSNR':>8}{'縁の誤差':>11}"
          f"{'内部の誤差':>12}{'比':>7}{'エッジ超過 [%]':>15}")
    ring = {}
    for label, obsx in (("循環(モデル一致)", blur_circular(gt, k_ref)),
                        ("反射(モデル不一致)", blur_padded(gt, k_ref))):
        o, _ = add_noise(obsx, 40.0, np.random.default_rng(SEED + 3))
        for nsr in (5e-5, 5e-4, 5e-3):
            est = fs.cx_wiener_deconvolve(o, k_ref, nsr=nsr)
            err = np.abs(est - gt)
            m = np.zeros_like(err, bool)
            m[:8, :] = m[-8:, :] = m[:, :8] = m[:, -8:] = True
            e_edge = float(err[m].mean()); e_in = float(err[~m].mean())
            band = (slice(50, 100), slice(112, 132))     # 矩形の右エッジのすぐ外
            contrast = 0.75 - float(gt[band].max())
            over = 100.0 * float(est[band].max() - gt[band].max()) / contrast
            ring[(label, nsr)] = (e_edge / e_in, over)
            print(f"  {label:<20}{nsr:>9.0e}{psnr(gt, est):>8.2f}{e_edge:>11.4f}"
                  f"{e_in:>12.4f}{e_edge / e_in:>7.2f}{over:>15.1f}")
    print("  → モデルが一致していれば縁の誤差は内部より **小さい**(比 0.74)。現実の")
    print("     ブレ(画面外から画が流れ込む)を循環モデルで戻すと 1.80 へ反転する。")
    print("     復元が下手なのではなく **モデルが縁で嘘をつく** —— 縁だけ壊れる。")
    print("     エッジ超過は正則化を強めれば消えるが、消した分だけ鮮鋭さも消える")
    print("     (nsr 5e-5 と 5e-3 の PSNR 差がその値段)。")
    print("     なお fs.cx_wiener_deconvolve は [0,1] に切り詰めるので、負側の")
    print("     アンダーシュートはこの数字に出てこない(道具の穴 e)。")

    print("\n=== 6. 回転ブレは 1 枚の核では書けない ===")
    rgt = scene_rotation(256, 70)
    rot = blur_rotational(rgt, 6.0, n=41)
    k_arc = psf_arc(70.0, 6.0)
    approx = blur_circular(rgt, k_arc)                   # 1 枚の核で書いたつもりの前向き
    o_rot, _ = add_noise(rot, 40.0, np.random.default_rng(SEED + 4))
    est_rot = fs.cx_wiener_deconvolve(o_rot, k_arc, nsr=5e-4)
    cy = cx = 128
    spots = (("核を作った場所(右)", cy, cx + 70),
             ("反対側(左)", cy, cx - 70),
             ("直交する側(上)", cy - 70, cx),
             ("回転中心(ほぼ無ブレ)", cy, cx))
    print(f"  {'場所':<24}{'前向きの一致':>14}{'観測':>9}{'復元':>9}{'差':>8}")
    deltas = {}
    for label, y, x in spots:
        sl = (slice(y - 16, y + 17), slice(x - 16, x + 17))
        fit = psnr(np.clip(rot[sl], 0, 1), approx[sl])
        p0 = psnr(rgt[sl], o_rot[sl])
        p1 = psnr(rgt[sl], est_rot[sl])
        deltas[label] = p1 - p0
        fit_s = "> 99" if fit > 99.0 else f"{fit:.2f}"    # 中心は両方とも無ブレで発散
        print(f"  {label:<24}{fit_s:>14}{p0:>9.2f}{p1:>9.2f}{p1 - p0:>8.2f}")
    print("  → 「前向きの一致」= 本物の回転ブレと 1 枚の核の畳み込みがどれだけ同じか。")
    print("     核を作った場所だけ合っていて、他は合っていない = **シフト不変でない**。")
    print("     その結果、同じ 1 枚の核で全画面を戻すと核を作った場所は良くなり、")
    print("     反対側と直交側は **戻すどころか悪化** する。ほぼブレていない中心では")
    print("     リンギングを足すだけなので最も大きく壊れる。区画に切って場所ごとの")
    print("     核を当てるしかない —— 「ブレ除去」を一括りにできない境目がここ。")

    print("\n=== 7. 速度(この機械での実測)===")
    for n in (256, 512, 1024):
        big = np.resize(gt, (n, n))
        kk = psf_line(15, 20.0)
        bb = blur_circular(big, kk)
        t0 = time.perf_counter()
        fs.cx_wiener_deconvolve(bb, kk, nsr=1e-4)
        t_w = 1e3 * (time.perf_counter() - t0)
        t0 = time.perf_counter()
        fs.op.unsharp(np.clip(bb, 0, 1), a=0.5, b=0.5)
        t_u = 1e3 * (time.perf_counter() - t0)
        t0 = time.perf_counter()
        estimate_line_kernel(bb)
        t_e = 1e3 * (time.perf_counter() - t0)
        print(f"  {f'{n}x{n}':<12}Wiener(核既知) {t_w:>7.1f} ms   "
              f"アンシャープ {t_u:>7.1f} ms   核の推定 {t_e:>7.1f} ms")
    print("  → 復元 1 回は FFT 2 回ぶんで、画素数に対してほぼ n log n。核の推定も")
    print("     FFT 1 回ぶんなので、**核が直線だと仮定できるなら推定は無料に近い**。")
    print("     高くつくのは仮定が置けないとき(形も含めた総当たり)。")

    # ---- 自己検査(速さは assert しない)-------------------------------------
    # (1) 核が完全に既知・無雑音・循環モデルなら、ほぼ完全に戻る
    p_clean, _, _ = wiener_best(blurred, k_ref, gt)
    assert p_clean > 45.0, f"無雑音・核既知で {p_clean:.1f} dB しか戻らない"
    # (2) 雑音があると上限が落ち、取り分が縮む(SNR 20 dB < 40 dB)
    assert gains[20.0] < gains[40.0], "雑音を増やしたのに取り分が縮まない"
    assert gains[20.0] < 3.0, f"SNR 20 dB での取り分 {gains[20.0]:.2f} dB は大きすぎる"
    # (3) 核が正しければゼロ点に勝ち、大きくずらせば負ける
    p_true, _, _ = wiener_best(obs40, k_ref, gt)
    assert p_true > p_uns40 and p_true > p_null40, "核既知でもゼロ点に勝てていない"
    p_bad, _, _ = wiener_best(obs40, psf_line(15, 20.0 + 45.0), gt)
    assert p_bad < p_null40, "45 度ずらしても『何もしない』に負けない = 前提が怪しい"
    assert ang_break_uns is not None and ang_break_null is not None, "破綻点が出ていない"
    assert ang_break_uns <= ang_break_null, "アンシャープより先に『何もしない』に負けた"
    assert len_break_null is not None and len_break_null < 8.0, "長さの破綻点が出ていない"
    # (4) 核を推定した場合: 雑音が軽ければ既知に肉薄し、重ければ壊れる
    assert ok_est >= 3, f"4 件中 {ok_est} 件しか推定が当たっていない"
    assert est_noise[40.0][3] - est_noise[40.0][2] < 1.0, \
        "SNR 40 dB で推定核が既知に肉薄しない"
    assert est_noise[15.0][2] < est_noise[15.0][4], \
        "SNR 15 dB で推定が外れてもゼロ点を割らない = 二段構えが出ていない"
    # (5) 核はどれも総和 1・非負(前向きモデルが明るさを変えないこと)
    for name, k in kernels.items():
        assert abs(float(k.sum()) - 1.0) < 1e-12, f"{name} の総和が 1 でない"
        assert float(k.min()) >= 0.0, f"{name} に負の重みがある"
    assert abs(float(blur_circular(gt, k_ref).mean() - gt.mean())) < 1e-9, \
        "循環ブレが平均輝度を変えた"
    # (6) リンギング: 非循環ブレは縁だけ壊れる / 正則化を強めると超過が減る
    assert ring[("反射(モデル不一致)", 5e-4)][0] > ring[("循環(モデル一致)", 5e-4)][0], \
        "モデル不一致でも縁が悪化しない"
    assert ring[("循環(モデル一致)", 5e-3)][1] < ring[("循環(モデル一致)", 5e-5)][1], \
        "正則化を強めてもオーバーシュートが減らない"
    # (7) 回転ブレ: 核を作った場所は良くなり、他は悪くなる(シフト不変でない)
    assert deltas["核を作った場所(右)"] > 1.0, "核を作った場所で改善しない"
    assert deltas["反対側(左)"] < 0.0, "反対側が悪化しない = シフト不変に見える"
    assert deltas["直交する側(上)"] < 0.0, "直交側が悪化しない = シフト不変に見える"
    # (6) 道具の側の fail-closed(壊れた入力を黙って通さないこと)
    for bad in ({"nsr": 0.0}, {"nsr": -1.0}):
        try:
            fs.cx_wiener_deconvolve(blurred, k_ref, **bad)
            raise AssertionError(f"nsr={bad['nsr']} が素通りした")
        except ValueError:
            pass
    try:
        fs.cx_wiener_deconvolve(blurred, np.ones((300, 300)) / 9e4, nsr=1e-3)
        raise AssertionError("画像より大きい核が素通りした")
    except ValueError:
        pass
    try:
        fs.cx_wiener_deconvolve(blurred, np.zeros((5, 5)), nsr=1e-3)
        raise AssertionError("総和 0 の核が素通りした")
    except ValueError:
        pass
    print("\nPASS")


if __name__ == "__main__":
    main()
