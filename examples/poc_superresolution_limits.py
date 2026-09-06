# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""超解像は情報を増やすのか —— 真値を持ったまま縮小して、戻して、数える。

EXTEND: 実写真でやるなら ``Scene.render`` を差し替える。ただし**実写真では真値が
無い**ので、手順は必ず「高解像で撮った 1 枚を真値とみなし、そこから縮小して観測を
作る」向きにすること(縮小の仕方 —— 面積平均か、間引きか、レンズのぼけを噛ませるか
—— で結論が変わるので、``down_box`` / ``camera_optical`` のどちらに寄せたかを必ず
書き添える)。複数フレームの節は連写(手持ちの微小ぶれ)がそのまま使える。実機の
フレームは並進だけでなく回転もするので、``fullseye.astrostack.align_frames`` で回転を
戻してから ``drizzle_resample`` に渡すこと(drizzle は回転を受け付けない)。

この PoC が示すこと:

1. **単一画像の拡大は情報を増やさない。** bicubic を零点に置くと、Lanczos-3 も
   五次スプラインも **PSNR で 0.1 dB 前後しか動かない**。分解能(縞の変調度)で
   見ると差はもっと露骨で、**どれも低解像側のナイキストで揃って死ぬ**。
   「上回らない」というのがこの節の結果である。
2. **既知のぼけを戻すのは、情報を増やすのとは別のことである。** 撮像の模擬が
   面積平均だと分かっているとき、その順モデルを使う反復逆投影(IBP)は bicubic を
   **数 dB 上回る**。ただし上回るのは**低解像側のナイキストより粗い縞だけ**で、
   細かい側は 1 本も戻らない。「戻す」と「増やす」の境目がそこに見える。
3. **見た目の指標と忠実度の指標は逆を向く。** アンシャープを掛けると勾配エネルギー
   (鮮鋭に見えるかの指標)は真値を追い越すのに、PSNR も SSIM も下がる。
   片方だけ出すと、いくらでも「良く」できてしまう。
4. **複数フレームは、標本化が足りていないときだけ本当に増やす。** 副画素ずれの
   ある 4/9/16 枚を drizzle で合成すると、**標本化不足(σ=0.30 低解像画素)では
   単一画像の拡大を大きく上回り、ナイキストより細かい縞の変調度が 0 から立ち
   上がる**。同じ枚数でも**十分標本化されている(σ=0.85)条件では、上回らない**。
   増えているのは枚数ではなく「格子がずれていること」である。
5. **ずれの符号を間違えると、例外も出さずに二重像になる。** 推定したずれをそのまま
   渡すか符号を反転するかで PSNR が二桁 dB 変わる。数字を並べて確かめる。

★ この PoC が出した道具の穴(op 本体は直していない):

(a) **2-D 画像を任意倍率でリサイズする op が台帳に無い。** 実際に使えたのは 3-D 用の
    ``vol_resize`` / ``volume_downsample`` で、``img[None]`` と ``factor=(1, s, s)`` で
    2-D を通した。2-D レジストリ側の ``zoom_image_factor`` / ``zoom_image_size`` は
    つまみが ``a``/``b`` ∈ [0,1] でキャンバスサイズ固定の進化 op なので、「倍率 4 で
    拡大して 4 倍の配列を得る」という最も普通の要求に答えられない。
(b) **Lanczos が無い。** ``gfx2d`` の補間は nearest / bilinear / bicubic の 3 つだけで、
    ``"lanczos"`` は「unknown value」で弾かれる(テストがその挙動を固定している)。
    この PoC では分離可能な Lanczos-3 を自前で書いた —— 拡大の比較で最も引き合いに
    出される核が無いのは、比較のたびに各自が書く羽目になる。
(c) **σ を指定する 2-D のガウス畳み込みが無い。** 撮像のぼけを作るのに使えたのは
    ``vol_fft_lowpass(vol, cutoff)`` で、``cutoff = 1/(2*pi*sigma)`` の関係が
    docstring のどこにも書かれていない(伝達関数 ``exp(-f^2/(2c^2))`` から導いた)。
    「レンズのぼけを σ 画素で掛けたい」から出発すると、この op には辿り着けない。
(d) **``fullseye.ledger.drizzle_resample`` は 2 つある返り値の片方を捨てる。**
    実体は ``(sci, wht)`` を返し docstring も「見る / 測るときは ``sci/wht`` を使え」と
    明記しているのに、台帳の入口を通ると ``sci`` だけが返る(実測: 返り値は ``sci``
    と bit 一致、``wht`` は取れない)。``fullseye.astrostack.drizzle_resample`` を直接
    呼べば両方取れるが、台帳の入口しか知らないと**正しい使い方が構造的にできない**。
(e) **``sci/wht`` は入力の階調に戻らない。** 実測で ``sci/wht`` は元の明るさの
    ``1/(pixfrac*scale)^2`` 倍になる(pixfrac=1, scale=2 で 0.2500、pixfrac=0.5,
    scale=2 で 1.0000、pixfrac=0.4, scale=2 で 1.5625 —— いずれも式と一致)。
    docstring には保存則の話はあるが**この換算式が無い**ので、そのまま PSNR を
    取ると「合成が失敗した」ように見える。
(f) **``fullseye.op.sobel_amp`` は出力を正規化するので、鮮鋭度の絶対量に使えない。**
    実測: 画像のコントラストを半分にしても勾配の平均は **1.0000 倍**(生の Sobel なら
    0.5 倍)。「どちらが鮮鋭か」を数字で言いたいだけなのに使えず、この PoC では
    差分で勾配エネルギーを自前計算した。no-reference の鮮鋭度指標(Tenengrad、
    ラプラシアン分散など)も、画像の MTF を測る op(スラントエッジ法、変調度)も
    台帳に無い —— ``psf_to_mtf`` は PSF を持っている前提で、画像からは測れない。
"""
from __future__ import annotations

import time

import numpy as np

import fullseye as fs

# --------------------------------------------------------------------------- #
# 真値の設計                                                                    #
# --------------------------------------------------------------------------- #
N = 480                                  # 真値の一辺 [画素]
BAR_PERIODS = (24, 16, 12, 8, 6, 4, 3)   # 正弦バー群の周期 [真値画素]
BAR_W = 48                               # 1 群の幅(全周期が整数回入る)
BAR_X0 = 40
BAR_R0, BAR_R1 = 32, 128
BAR_AMP = 0.4
POINT_SEPS = (4.0, 6.0, 8.0, 12.0, 16.0)


def _soft_band(t, a, b, w=1.0):
    """``[a, b)`` を 1、外を 0 にする滑らかな窓(端は tanh で ~2w 画素)。"""
    return 0.5 * (np.tanh((t - a) / w) - np.tanh((t - b) / w))


def _blob(y, x, cy, cx, sigma):
    return np.exp(-((y - cy) ** 2 + (x - cx) ** 2) / (2.0 * sigma ** 2))


def _rect(y, x, r0, r1, c0, c1, w=0.8):
    return _soft_band(y, r0, r1, w) * _soft_band(x, c0, c1, w)


class Scene:
    """連続量として定義した真値。**任意の副画素ずれで厳密に標本化できる**。

    ここが PoC の土台である。真値を配列で持って補間でずらすと、比較したい相手
    (補間)を真値の側にも混ぜてしまう。縞・点・文字風は閉形式、テクスチャは
    フーリエ係数を固定して位相ランプでずらす(帯域制限してあるので厳密)。
    """

    def __init__(self, n=N, seed=7):
        self.n = n
        rng = np.random.default_rng(seed)
        ky = np.fft.fftfreq(n)[:, None]
        kx = np.fft.fftfreq(n)[None, :]
        f = np.hypot(ky, kx)
        amp = np.zeros_like(f)
        nz = f > 0
        amp[nz] = f[nz] ** -1.6
        amp[f > 0.35] = 0.0              # ナイキストの手前で切る = 帯域制限
        amp[0, 0] = 0.0
        self._spec = amp * np.exp(1j * rng.uniform(0.0, 2.0 * np.pi, (n, n)))
        base = np.real(np.fft.ifft2(self._spec))
        self._tex_gain = 0.12 / float(base.std())

    def _texture(self, dy, dx):
        n = self.n
        ky = np.fft.fftfreq(n)[:, None]
        kx = np.fft.fftfreq(n)[None, :]
        ramp = np.exp(2j * np.pi * (ky * dy + kx * dx))
        return np.real(np.fft.ifft2(self._spec * ramp)) * self._tex_gain

    def _glyphs(self, y, x):
        """文字風 —— 直線と細い隙間。太さ 4 画素の行と 2 画素の行を並べる。"""
        m = np.zeros_like(y + x)
        for row, (r, hgt, th) in enumerate(((222.0, 26.0, 4.0), (262.0, 26.0, 2.0))):
            for i in range(8):
                c = 40.0 + i * 52.0
                m = np.maximum(m, _rect(y, x, r, r + hgt, c, c + th))          # 縦棒
                m = np.maximum(m, _rect(y, x, r, r + th, c, c + 20.0))          # 上
                m = np.maximum(m, _rect(y, x, r + hgt / 2 - th / 2,
                                        r + hgt / 2 + th / 2, c, c + 15.0))     # 中
                m = np.maximum(m, _rect(y, x, r + hgt - th, r + hgt,
                                        c, c + 20.0))                           # 下
        return 0.35 * m

    def render(self, dy=0.0, dx=0.0):
        """連続座標 ``(row + dy, col + dx)`` で真値を標本化する。"""
        n = self.n
        y = np.arange(n, dtype=np.float64)[:, None] + dy
        x = np.arange(n, dtype=np.float64)[None, :] + dx
        img = np.full((n, n), 0.5)

        band = _soft_band(y, BAR_R0, BAR_R1)
        bars = np.zeros((n, n))
        for gi, p in enumerate(BAR_PERIODS):
            c0 = BAR_X0 + gi * BAR_W
            bars += _soft_band(x, c0, c0 + BAR_W) * np.cos(2.0 * np.pi * (x - c0) / p)
        img = img + BAR_AMP * band * bars

        for i, sep in enumerate(POINT_SEPS):
            cx = 70.0 + i * 84.0
            img = img + 0.42 * (_blob(y, x, 175.0, cx - sep / 2, 1.0)
                                + _blob(y, x, 175.0, cx + sep / 2, 1.0))

        img = img + self._glyphs(y, x)

        gate = _soft_band(y, 312.0, 468.0, 1.5) * _soft_band(x, 20.0, 460.0, 1.5)
        img = img + gate * self._texture(dy, dx)
        return img


# --------------------------------------------------------------------------- #
# 撮像の模擬 と 拡大の手法                                                       #
# --------------------------------------------------------------------------- #
def down_box(hr, s):
    """撮像の模擬 —— ``s x s`` の面積平均(帯域制限)+ 間引き。台帳 op を 2-D で使う。"""
    return np.asarray(fs.ledger.volume_downsample(hr[None], (1, s, s), mode="mean"))[0]


def up_spline(lr, s, order):
    """スプライン拡大。``order`` 0=nearest / 1=bilinear / 3=bicubic / 5=五次。"""
    out = fs.ledger.vol_resize(lr[None], factor=(1.0, float(s), float(s)), order=order)
    return np.asarray(out)[0]


def _lanczos_matrix(n_in, n_out, s, a=3):
    j = np.arange(n_out, dtype=np.float64)
    u = (j + 0.5) / s - 0.5                       # 出力画素中心が指す入力座標
    t = u[:, None] - np.arange(n_in, dtype=np.float64)[None, :]
    w = np.sinc(t) * np.sinc(t / a)
    w[np.abs(t) >= a] = 0.0
    return w / w.sum(axis=1, keepdims=True)       # 縁の切り詰めはここで吸収


def up_lanczos(lr, s, a=3):
    """分離可能 Lanczos-3。台帳に無いので自前(道具の穴 (b))。"""
    wy = _lanczos_matrix(lr.shape[0], lr.shape[0] * s, s, a)
    wx = _lanczos_matrix(lr.shape[1], lr.shape[1] * s, s, a)
    return wy @ lr @ wx.T


def up_sharpened(lr, s):
    """bicubic に鮮鋭化を掛ける —— 「良く見える」側の代表。"""
    return np.asarray(fs.op.unsharp(np.clip(up_spline(lr, s, 3), 0.0, 1.0)))


def up_ibp(lr, s, iters=8, gain=1.0):
    """反復逆投影 —— **順モデル(面積平均)を知っている**ことだけを使う。

    情報を増やしているのではなく、既知のぼけを戻している。低解像側のナイキスト
    より細かい成分は順モデルの零点に落ちているので、何回回しても戻らない。
    """
    est = up_spline(lr, s, 3)
    for _ in range(iters):
        est = est + gain * up_spline(lr - down_box(est, s), s, 3)
    return np.clip(est, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# 測る                                                                          #
# --------------------------------------------------------------------------- #
def gradient_energy(img):
    """勾配エネルギー = 「鮮鋭に見えるか」の指標。自前(道具の穴 (f))。"""
    a = np.clip(np.asarray(img, np.float64), 0.0, 1.0)[8:-8, 8:-8]
    gy = np.diff(a, axis=0)[:, :-1]
    gx = np.diff(a, axis=1)[:-1, :]
    return float(np.mean(np.hypot(gy, gx)))


def bar_amplitudes(img):
    """正弦バー群の各周期での振幅(ロックイン検波)。→ 長さ 7 の配列。"""
    prof = np.asarray(img)[BAR_R0 + 12:BAR_R1 - 12, :].mean(axis=0)
    out = np.empty(len(BAR_PERIODS))
    for gi, p in enumerate(BAR_PERIODS):
        c0 = BAR_X0 + gi * BAR_W
        seg = prof[c0:c0 + BAR_W]
        xs = np.arange(c0, c0 + BAR_W, dtype=np.float64)
        out[gi] = 2.0 * abs(np.mean(seg * np.exp(-2j * np.pi * xs / p)))
    return out


def modulation(img, ref_amp):
    """真値の振幅で割った変調度。1.0 = 真値どおり、0.0 = 縞が消えた。"""
    return bar_amplitudes(img) / ref_amp


def resolved_period(mod, threshold=0.20):
    """変調度が閾値以上で残っている**最も細かい周期** [真値画素]。"""
    ok = [p for p, m in zip(BAR_PERIODS, mod) if m >= threshold]
    return min(ok) if ok else float("nan")


def fid(a, b):
    """(PSNR [dB], SSIM)。縁は比較から外す(FFT の周期性と縁の外挿を避ける)。"""
    a = np.clip(np.asarray(a, np.float64), 0.0, 1.0)[16:-16, 16:-16]
    b = np.clip(np.asarray(b, np.float64), 0.0, 1.0)[16:-16, 16:-16]
    return float(fs.psnr(a, b, data_range=1.0)), float(fs.ssim(a, b, data_range=1.0))


# --------------------------------------------------------------------------- #
# 複数フレームの撮像 —— レンズのぼけ + 点標本化                                   #
# --------------------------------------------------------------------------- #
def optical_blur(hr, sigma_hr):
    """σ [真値画素] のガウスぼけ。``vol_fft_lowpass`` の cutoff = 1/(2 pi sigma)。"""
    cutoff = 1.0 / (2.0 * np.pi * sigma_hr)
    return np.asarray(fs.ledger.vol_fft_lowpass(hr[None], cutoff))[0]


def capture(scene, s, sigma_lr, ddy, ddx):
    """1 枚撮る。標本位置は ``i*s + (s-1)/2 + ddy``(drizzle の格子中心の規約)。"""
    hr = scene.render((s - 1) / 2.0 + ddy, (s - 1) / 2.0 + ddx)
    blur = optical_blur(hr, sigma_lr * s)
    return np.asarray(fs.ledger.volume_downsample(blur[None], (1, s, s), mode="stride"))[0]


def dither_offsets(n_frames, s, seed=3):
    """1 低解像画素を ``m x m`` に割る格子 + 微小ジッタ。単位は真値画素。"""
    m = int(round(np.sqrt(n_frames)))
    rng = np.random.default_rng(seed)
    offs = []
    for a in range(m):
        for b in range(m):
            offs.append((s * (a + 0.5) / m - s / 2.0 + rng.uniform(-0.15, 0.15),
                         s * (b + 0.5) / m - s / 2.0 + rng.uniform(-0.15, 0.15)))
    offs[0] = (0.0, 0.0)                       # 基準フレームはずらさない
    return offs, m


def drizzle_image(frames, shifts, scale, pixfrac):
    """``(sci, wht)`` から**見るための画像**を作る。換算は道具の穴 (e)。"""
    sci, wht = fs.astrostack.drizzle_resample(list(frames), shifts=shifts,
                                              scale=scale, pixfrac=pixfrac)
    cover = wht > 1e-9
    img = np.zeros_like(sci)
    img[cover] = sci[cover] / wht[cover] * (pixfrac * scale) ** 2
    return img, wht


def estimate_shifts(frames, window=48):
    """フレーム 0 に対するずれを相互相関で測る。→ ``(N, 2)`` [低解像画素]。"""
    out = np.zeros((len(frames), 2))
    for k in range(1, len(frames)):
        flow, _info = fs.ledger.piv_cross_correlate(frames[0], frames[k],
                                                    window=window, overlap=0.5)
        out[k, 0] = float(np.median(flow[0]))
        out[k, 1] = float(np.median(flow[1]))
    return out


# --------------------------------------------------------------------------- #
def main():
    t_start = time.perf_counter()
    scene = Scene()
    truth = scene.render(0.0, 0.0)
    ref_amp = bar_amplitudes(truth)
    print("=== 0. 真値 ===")
    print(f"  {N}x{N}、値域 [{truth.min():.3f}, {truth.max():.3f}]"
          f"(飽和なし = 縮小と拡大が線形のまま比較できる)")
    print(f"  正弦バー群の周期 {BAR_PERIODS} 真値画素、振幅 {BAR_AMP}")
    print(f"  真値での実測振幅 {np.array2string(ref_amp, precision=3)}"
          f"(全群でほぼ {BAR_AMP} = 物差しとして使える)")

    print("\n=== 1. 単一画像の拡大 —— bicubic の零点を上回れるか ===")
    print("  撮像の模擬 = s x s の面積平均(アンチエイリアスあり)。戻して真値と比べる。")
    methods = (
        ("nearest",            lambda lr, s: up_spline(lr, s, 0)),
        ("bilinear",           lambda lr, s: up_spline(lr, s, 1)),
        ("bicubic(零点)",      lambda lr, s: up_spline(lr, s, 3)),
        ("五次スプライン",      lambda lr, s: up_spline(lr, s, 5)),
        ("Lanczos-3(自前)",   lambda lr, s: up_lanczos(lr, s)),
        ("bicubic+鮮鋭化",     up_sharpened),
        ("IBP(順モデル既知)",  lambda lr, s: up_ibp(lr, s)),
    )
    recon = {}
    print(f"  {'倍率':>4}{'手法':>20}{'PSNR [dB]':>12}{'零点との差':>12}"
          f"{'SSIM':>9}{'零点との差':>12}")
    for s in (2, 3, 4):
        lr = down_box(truth, s)
        null_psnr = null_ssim = None
        for name, fn in methods:
            out = fn(lr, s)
            recon[(s, name)] = out
            p, ss = fid(truth, out)
            if name.startswith("bicubic("):
                null_psnr, null_ssim = p, ss
            dp = "" if null_psnr is None else f"{p - null_psnr:+12.3f}"
            ds = "" if null_ssim is None else f"{ss - null_ssim:+12.4f}"
            print(f"  {s:>4}{name:>20}{p:>12.3f}{dp}{ss:>9.4f}{ds}")
        print(f"       低解像 {lr.shape[0]}x{lr.shape[1]}、"
              f"低解像側のナイキスト = 周期 {2 * s} 真値画素")
    print("  → 補間核を替えても PSNR は零点の周りで 0.1 dB 程度しか動かない。")
    print("     動いているのは (a) 鮮鋭化 —— **下**へ、(b) IBP —— 上へ。")
    print("     IBP が上がるのは順モデル(面積平均)を知っているからで、")
    print("     補間核の工夫とは別の理由による。")

    print("\n=== 2. 分解能の実測 —— 縞はどこまで分離するか(変調度)===")
    s = 4
    lr = down_box(truth, s)
    print(f"  倍率 {s}、低解像側のナイキスト = 周期 {2 * s} 真値画素")
    header = "".join(f"{p:>7}" for p in BAR_PERIODS)
    print(f"  {'手法':>20}{header}{'分離限界':>10}")
    print(f"  {'真値':>20}" + "".join(f"{v:>7.2f}" for v in np.ones(len(BAR_PERIODS)))
          + f"{min(BAR_PERIODS):>10}")
    mods = {}
    for name, _fn in methods:
        m = modulation(recon[(s, name)], ref_amp)
        mods[name] = m
        print(f"  {name:>20}" + "".join(f"{v:>7.2f}" for v in m)
              + f"{resolved_period(m):>10}")
    print("  → 周期 8(= 2s)より細かい列は、どの手法でも 0 のまま。")
    print("     IBP は周期 8〜12 の**落ちていた変調を戻す**が、周期 6 以下は戻せない。")
    print("     鮮鋭化は全部の列を持ち上げる —— 縞が無いところにも縞を作るので、")
    print("     この列を見て「分解能が上がった」と言ってはいけない。")

    print("\n=== 3. 「鮮鋭に見える」と「情報が増えた」は別 ===")
    print(f"  {'手法':>20}{'勾配エネルギー':>16}{'真値比':>9}{'PSNR [dB]':>12}{'SSIM':>9}")
    g_truth = gradient_energy(truth)
    print(f"  {'真値':>20}{g_truth:>16.5f}{1.0:>9.2f}{'—':>12}{'—':>9}")
    for name in ("bicubic(零点)", "bicubic+鮮鋭化", "IBP(順モデル既知)"):
        out = recon[(s, name)]
        g = gradient_energy(out)
        p, ss = fid(truth, out)
        print(f"  {name:>20}{g:>16.5f}{g / g_truth:>9.2f}{p:>12.3f}{ss:>9.4f}")
    gb = gradient_energy(recon[(s, "bicubic(零点)")])
    gs = gradient_energy(recon[(s, "bicubic+鮮鋭化")])
    pb, sb = fid(truth, recon[(s, "bicubic(零点)")])
    ps, ss_ = fid(truth, recon[(s, "bicubic+鮮鋭化")])
    print(f"  → 鮮鋭化で勾配エネルギーは {gs / gb:.2f} 倍(真値を {gs / g_truth:.2f} 倍で追い越す)、")
    print(f"     同じ操作で PSNR は {ps - pb:+.2f} dB、SSIM は {ss_ - sb:+.4f}。")
    print("     **二つの指標が逆を向く**。片方だけ出す報告は、この操作で自由に作れる。")

    print("\n=== 4. 複数フレーム —— 標本化が足りているかで結論が変わる ===")
    print("  撮像の模擬 = レンズのぼけ(σ)+ 点標本化。基準は「レンズを通った像を")
    print("  真値の格子で完全に標本化したもの」= 合成が到達しうる上限。")
    regimes = (("標本化不足", 0.30), ("十分に標本化", 0.85))
    multi = {}
    for label, sigma_lr in regimes:
        band_limited = optical_blur(scene.render(0.0, 0.0), sigma_lr * s)
        bl_amp = bar_amplitudes(band_limited)
        print(f"\n  --- {label}(σ = {sigma_lr:.2f} 低解像画素 "
              f"= {sigma_lr * s:.2f} 真値画素、FWHM {2.355 * sigma_lr:.2f} 低解像画素)---")
        frame0 = capture(scene, s, sigma_lr, 0.0, 0.0)
        single = up_spline(frame0, s, 3)
        p0, s0 = fid(band_limited, single)
        print(f"  {'合成':>22}{'枚数':>5}{'pixfrac':>9}{'PSNR [dB]':>12}"
              f"{'単一比':>9}{'SSIM':>9}{'ずれ推定誤差':>14}")
        print(f"  {'単一画像 bicubic':>22}{1:>5}{'—':>9}{p0:>12.3f}{0.0:>+9.2f}{s0:>9.4f}{'—':>14}")
        for n_frames in (4, 9, 16):
            offs, m = dither_offsets(n_frames, s)
            frames = [capture(scene, s, sigma_lr, dy, dx) for dy, dx in offs]
            truth_shifts = np.array([[-dy / s, -dx / s] for dy, dx in offs])
            est = estimate_shifts(frames)
            err = float(np.max(np.abs(est - truth_shifts)))
            pixfrac = min(1.0, 1.3 / m)
            img, wht = drizzle_image(frames, est, s, pixfrac)
            p, ss = fid(band_limited, img)
            multi[(label, n_frames)] = (img, bl_amp, wht)
            print(f"  {'drizzle(推定ずれ)':>22}{n_frames:>5}{pixfrac:>9.3f}"
                  f"{p:>12.3f}{p - p0:>+9.2f}{ss:>9.4f}{err:>14.4f}")
            if n_frames == 16:
                naive = up_spline(np.mean(frames, axis=0), s, 3)
                pn, sn = fid(band_limited, naive)
                print(f"  {'ずれを無視して平均':>22}{n_frames:>5}{'—':>9}"
                      f"{pn:>12.3f}{pn - p0:>+9.2f}{sn:>9.4f}{'—':>14}")
        img16, bl_amp16, _w = multi[(label, 16)]
        print(f"  {'周期 [真値画素]':>22}" + "".join(f"{p:>7}" for p in BAR_PERIODS))
        print(f"  {'単一画像 bicubic':>22}"
              + "".join(f"{v:>7.2f}" for v in modulation(single, bl_amp)))
        print(f"  {'drizzle 16 枚':>22}"
              + "".join(f"{v:>7.2f}" for v in modulation(img16, bl_amp)))
    print("\n  → 標本化不足では drizzle がナイキストより細かい列を立ち上げる。")
    print("     十分に標本化されている条件では、同じ 16 枚でもほとんど動かない ——")
    print("     レンズが既に落とした成分は、何枚撮っても戻らないため。")
    print("     ずれを無視して平均すると像は逆に鈍る(同じずれを解像度に変えるのが drizzle)。")

    print("\n=== 5. ずれの符号を間違えると、例外も出さずに二重像になる ===")
    sigma_lr = 0.30
    band_limited = optical_blur(scene.render(0.0, 0.0), sigma_lr * s)
    offs, m = dither_offsets(16, s)
    frames = [capture(scene, s, sigma_lr, dy, dx) for dy, dx in offs]
    est = estimate_shifts(frames)
    pixfrac = min(1.0, 1.3 / m)
    good, _w = drizzle_image(frames, est, s, pixfrac)
    bad, _w = drizzle_image(frames, -est, s, pixfrac)
    zero, _w = drizzle_image(frames, np.zeros_like(est), s, pixfrac)
    for label, im in (("正しい符号", good), ("符号を反転", bad), ("ずれを渡さない", zero)):
        p, ss = fid(band_limited, im)
        print(f"  {label:>16}{p:>12.3f} dB{ss:>10.4f}")
    print("  → 反転しても例外は出ない。数字を並べないと気づけない。")

    print("\n=== 6. 速度(この機械での実測)===")
    lr = down_box(truth, 4)
    print(f"  入力 {lr.shape[0]}x{lr.shape[1]} → 出力 {N}x{N}(倍率 4)")
    for label, fn in (("nearest", lambda: up_spline(lr, 4, 0)),
                      ("bilinear", lambda: up_spline(lr, 4, 1)),
                      ("bicubic", lambda: up_spline(lr, 4, 3)),
                      ("五次スプライン", lambda: up_spline(lr, 4, 5)),
                      ("Lanczos-3(自前)", lambda: up_lanczos(lr, 4)),
                      ("bicubic+鮮鋭化", lambda: up_sharpened(lr, 4)),
                      ("IBP 8 回", lambda: up_ibp(lr, 4))):
        t0 = time.perf_counter()
        fn()
        print(f"  {label:<20}{1e3 * (time.perf_counter() - t0):>9.1f} ms")
    t0 = time.perf_counter()
    drizzle_image(frames, est, 4, pixfrac)
    t_dr = 1e3 * (time.perf_counter() - t0)
    t0 = time.perf_counter()
    estimate_shifts(frames)
    t_piv = 1e3 * (time.perf_counter() - t0)
    print(f"  {'drizzle 16 枚':<20}{t_dr:>9.1f} ms  (120x120 x16 → 480x480)")
    print(f"  {'ずれ推定 15 対':<20}{t_piv:>9.1f} ms  (相互相関、窓 48)")

    # ---- 自己検査(速さは assert しない)-------------------------------------
    # 真値そのものが物差しとして成立している
    assert 0.0 < truth.min() and truth.max() < 1.0, "真値が飽和している"
    assert np.all(np.abs(ref_amp - BAR_AMP) < 0.02), "真値のバー振幅が設計値からずれた"

    # 定数画像はどの手法でも定数のまま(縁も含めて)
    const = np.full((30, 30), 0.37)
    for order in (0, 1, 3, 5):
        assert np.allclose(up_spline(const, 4, order), 0.37, atol=1e-9), \
            f"定数画像が order={order} で定数でなくなった"
    assert np.allclose(up_lanczos(const, 4), 0.37, atol=1e-9), "Lanczos で定数が崩れた"

    # 面積平均 → nearest 拡大 は格子が揃っている(ブロック定数が厳密に往復する)
    blocky = np.repeat(np.repeat(np.arange(9.0).reshape(3, 3) / 9.0, 4, 0), 4, 1)
    assert np.allclose(up_spline(down_box(blocky, 4), 4, 0), blocky, atol=1e-12), \
        "面積平均と拡大の格子がずれている(半画素のずれ)"

    # 零点を「補間核の工夫」で上回れていないこと自体を検査に固定する
    p_null = fid(truth, recon[(4, "bicubic(零点)")])[0]
    for name in ("nearest", "bilinear", "五次スプライン", "Lanczos-3(自前)"):
        assert fid(truth, recon[(4, name)])[0] - p_null < 0.5, \
            f"{name} が零点を 0.5 dB 超えた —— 結論を書き換えること"
    # 順モデルを知っている IBP だけは上回る
    assert fid(truth, recon[(4, "IBP(順モデル既知)")])[0] - p_null > 1.0, \
        "IBP が零点を上回らない(順モデルの向きを疑う)"

    # 見た目と忠実度が逆を向く
    assert gs > gb and ps < pb and ss_ < sb, "鮮鋭化で二つの指標が逆を向かなかった"
    assert gs > g_truth, "鮮鋭化が真値の勾配エネルギーを超えなかった"

    # 低解像側のナイキストより細かい縞は、単一画像ではどの手法でも戻らない
    fine = [i for i, p in enumerate(BAR_PERIODS) if p < 2 * 4]
    for name in ("bicubic(零点)", "五次スプライン", "Lanczos-3(自前)", "IBP(順モデル既知)"):
        assert max(mods[name][i] for i in fine) < 0.20, \
            f"{name} がナイキストより細かい縞を作った(偽の情報を疑う)"

    # drizzle: 単一フレーム・ずれ 0 なら総フラックスが保存する
    sci, wht = fs.astrostack.drizzle_resample([frames[0]], shifts=None,
                                              scale=4, pixfrac=1.0)
    assert abs(sci.sum() / frames[0].sum() - 1.0) < 1e-9, "drizzle が総フラックスを保存しない"
    assert abs(float(wht[40, 40]) - 1.0) < 1e-12, "pixfrac=1・ずれ 0 で内部の重みが 1 でない"

    # 複数フレームは「標本化が足りていないとき**だけ**」効く
    bl_under = optical_blur(scene.render(0.0, 0.0), 0.30 * 4)
    bl_well = optical_blur(scene.render(0.0, 0.0), 0.85 * 4)
    g_under = (fid(bl_under, multi[("標本化不足", 16)][0])[0]
               - fid(bl_under, up_spline(capture(scene, 4, 0.30, 0.0, 0.0), 4, 3))[0])
    g_well = (fid(bl_well, multi[("十分に標本化", 16)][0])[0]
              - fid(bl_well, up_spline(capture(scene, 4, 0.85, 0.0, 0.0), 4, 3))[0])
    assert g_under > 3.0, f"標本化不足で複数フレームの利得が出ない({g_under:.2f} dB)"
    assert g_under > 2.0 * max(g_well, 0.1), \
        f"十分標本化の側でも同じだけ得をしている(不足 {g_under:.2f} / 十分 {g_well:.2f} dB)"

    # 符号を間違えると壊れる(例外は出ない)
    assert fid(band_limited, good)[0] - fid(band_limited, bad)[0] > 5.0, \
        "ずれの符号を反転しても結果が変わらない —— 合成が効いていない疑い"

    print(f"\n所要 {time.perf_counter() - t_start:.1f} 秒")
    print("PASS")


if __name__ == "__main__":
    main()
