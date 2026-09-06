# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""超解像は情報を増やすのか —— 真値を持ったまま縮小して、戻して、数える。

EXTEND: 実写真でやるなら :class:`Scene` を差し替える。ただし**実写真には真値が無い**
ので、手順は必ず「高解像で撮った 1 枚を真値とみなし、そこから縮小して観測を作る」
向きにすること。縮小の仕方(面積平均か、間引きか、レンズのぼけを噛ませるか)で
結論が変わるので、``down_box`` と ``camera``(= レンズのぼけ + 点標本化)のどちらに
寄せたかを必ず書き添える。複数フレームの節は連写(手持ちの微小ぶれ)がそのまま
使えるが、実機のフレームは並進だけでなく回転もするので
``fullseye.astrostack.align_frames`` で回転を戻してから ``drizzle_resample`` に渡す
こと(drizzle は回転を受け付けない)。

結論を先に書く。

1. **単一画像の拡大では bicubic の零点を上回れない。** nearest / bilinear /
   五次スプライン / Lanczos-3 を倍率 2・3・4 で総当たりして、零点を上回れたのは
   **最大 +0.036 dB**(下振れは −0.67 dB)。分解能(縞の変調度)で見ても
   **全部が低解像側のナイキストで揃って死ぬ**。「勝てなかった」がこの節の結果で
   あり、拡大の核を選び直すことに投じる労力の上限がここに出ている。
2. **既知のぼけを戻すのは、情報を増やすのとは別のことである。** 撮像の模擬が面積
   平均だと分かっているとき、その順モデルだけを使う反復逆投影(IBP)は、周期 12
   真値画素の変調度を **0.78 → 0.96**、周期 16 を **0.89 → 1.00** に戻す。ところが
   **PSNR はほとんど動かない(倍率 4 で −0.01 dB)**。指標の選び方ひとつで、この
   改善は無かったことになる。そして**ナイキストより細かい列は 1 本も戻らない**。
3. **見た目の指標と忠実度の指標は逆を向く。** アンシャープを強く掛けると勾配
   エネルギーは真値と一致するところまで上がるのに(比 1.00)、PSNR は
   **1.57 dB 落ちる**。弱く掛けると PSNR だけ下がって SSIM は上がる —— 3 つの数字
   が三様の答えを返すので、1 つだけ出す報告はいくらでも作れる。
4. **複数フレームは、標本化が足りていないときだけ本当に増やす。** 副画素ずれのある
   16 枚を drizzle で合成すると、標本化不足(σ = 0.30 低解像画素)では
   **+13.96 dB**(ずれを真値で与えれば +18.33 dB —— 差の 4.4 dB が位置合わせの
   代価)、ナイキストより細かい周期 6 の変調度が **0.03 → 0.38** に立ち上がる
   (レンズが許す上限は 0.46 なので、その 8 割まで届いている)。
   十分に標本化された条件(σ = 0.85)では PSNR が +5.79 dB 上がるのに、
   **分解能の列は小数第 2 位まで 1 つも動かない** —— 上がったぶんは情報ではなく、
   既に見えない大きさの誤差がさらに小さくなっただけである。分解能の表を併記
   しないと、この 2 つは PSNR では区別できない。
5. **ずれの符号を間違えると、例外も出さずに二重像になる。** 符号を反転しただけで
   PSNR が二桁 dB 落ちる。数字を並べないと気づけない。

★ この PoC が出した道具の穴(op 本体は直していない):

(a) **2-D 画像を任意倍率でリサイズする op が台帳に無い。** 実際に使えたのは 3-D 用の
    ``vol_resize`` / ``volume_downsample`` で、``img[None]`` と ``factor=(1, s, s)`` で
    2-D を通した。2-D レジストリ側の ``zoom_image_factor`` / ``zoom_image_size`` は
    つまみが ``a``/``b`` ∈ [0,1] でキャンバスサイズ固定の進化 op なので、「倍率 4 で
    拡大して 4 倍の配列を得る」という最も普通の要求に答えられない。
(b) **Lanczos が無い。** ``gfx2d`` の補間は nearest / bilinear / bicubic の 3 つだけで、
    ``"lanczos"`` は「unknown value」で弾かれる(テストがその挙動を固定している)。
    拡大の比較で最もよく引き合いに出される核が無いので、ここでは自前で書いた。
(c) **σ を指定する 2-D のガウス畳み込みが無い。** 撮像のぼけに使えたのは
    ``vol_fft_lowpass(vol, cutoff)`` で、``cutoff = 1/(2*pi*sigma)`` の対応が
    docstring のどこにも書かれていない(伝達関数 ``exp(-f^2/(2c^2))`` から導いた)。
    「レンズのぼけを σ 画素で掛けたい」から出発すると、この op には辿り着けない。
(d) ★**台帳の入口は、複数返す op の 2 番目以降を捨てる。** 実測 2 件:
    ``fullseye.ledger.drizzle_resample`` は ``(sci, wht)`` のうち ``sci`` だけを返し
    (返り値は ``sci`` と bit 一致)、``fullseye.ledger.piv_cross_correlate`` は
    ``(flow, info)`` のうち ``flow`` だけを返す。**後者は例外を出さずに嘘の値を作る**
    —— ``flow, info = fs.ledger.piv_cross_correlate(...)`` と書くと ``(2, R, C)`` の
    配列が第 1 軸で開かれて ``flow`` が ``(R, C)`` の **dy 成分だけ**になり、
    ``flow[1]`` が「dx」ではなく「dy の 2 行目」になる。この PoC は最初その形で
    書いてしまい、ずれの推定誤差 0.74 低解像画素(正しくは 0.14)で複数フレーム合成
    が単一画像に負けた。drizzle の方は ``sci`` の docstring が「見る / 測るときは
    ``sci/wht`` を使え」と明記しているのに、台帳の入口からは ``wht`` に到達できない。
    ``fullseye.astrostack.drizzle_resample`` を直接呼べば両方取れる。
(e) **``sci/wht`` は入力の階調に戻らない。** 実測で元の明るさの ``1/(pixfrac*scale)^2``
    倍になる(pixfrac=1・scale=2 で 0.2500、pixfrac=0.5・scale=2 で 1.0000、
    pixfrac=0.4・scale=2 で 1.5625 —— いずれも式と一致)。docstring には保存則の話は
    あるがこの換算式が無いので、そのまま PSNR を取ると合成が失敗したように見える。
(f) **``fullseye.op.sobel_amp`` は出力を正規化するので鮮鋭度の絶対量に使えない。**
    実測: 画像のコントラストを半分にしても勾配の平均は **1.0000 倍**(生の Sobel なら
    0.5 倍)。この PoC では差分で勾配エネルギーを自前計算した。no-reference の鮮鋭度
    指標(Tenengrad、ラプラシアン分散)も、**画像から** MTF や分解能を測る op も台帳に
    無い —— ``psf_to_mtf`` は PSF を持っている前提で、撮れた画像からは測れない。
(g) **``fullseye.op.xsitk_laplacian_sharpen`` はつまみが死んでいる。** ``a``/``b`` を
    0.0 から 1.0 まで振っても出力の標準偏差が 0.38338 のまま動かない(``unsharp`` は
    0.116 → 0.284、``cv_sharpen`` は 0.116 → 0.413 と動く)。
(h) **``piv_cross_correlate`` は窓によっては静かに NaN を返す。** 実測で 16 窓中 2 窓
    (標本化不足・ずれ 0.67 低解像画素の対)。例外も警告も出ないので、集約は
    ``np.nanmedian`` にしないと全体が NaN に落ちる。
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
BAR_W = 48                               # 1 群の幅(全周期が整数回入る = 漏れなし)
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
    (補間)を真値の側にも混ぜてしまい、何を測っているのか分からなくなる。
    縞・点・文字風は閉形式、自然画像風のテクスチャはフーリエ係数を固定して
    位相ランプでずらす(ナイキストの手前で帯域制限してあるので厳密)。
    """

    def __init__(self, n=N, seed=7):
        self.n = n
        rng = np.random.default_rng(seed)
        ky = np.fft.fftfreq(n)[:, None]
        kx = np.fft.fftfreq(n)[None, :]
        f = np.hypot(ky, kx)
        amp = np.zeros_like(f)
        nz = f > 0
        amp[nz] = f[nz] ** -1.6                   # 自然画像に近い 1/f 型
        amp[f > 0.35] = 0.0                       # 帯域制限(位相ランプが厳密になる)
        amp[0, 0] = 0.0
        self._spec = amp * np.exp(1j * rng.uniform(0.0, 2.0 * np.pi, (n, n)))
        self._tex_gain = 0.12 / float(np.real(np.fft.ifft2(self._spec)).std())

    def _texture(self, dy, dx):
        n = self.n
        ky = np.fft.fftfreq(n)[:, None]
        kx = np.fft.fftfreq(n)[None, :]
        ramp = np.exp(2j * np.pi * (ky * dy + kx * dx))
        return np.real(np.fft.ifft2(self._spec * ramp)) * self._tex_gain

    def _glyphs(self, y, x):
        """文字風 —— 直線と細い隙間。太さ 4 画素の行と 2 画素の行を並べる。"""
        m = np.zeros_like(y + x)
        for r, hgt, th in ((222.0, 26.0, 4.0), (262.0, 26.0, 2.0)):
            for i in range(8):
                c = 40.0 + i * 52.0
                m = np.maximum(m, _rect(y, x, r, r + hgt, c, c + th))            # 縦棒
                m = np.maximum(m, _rect(y, x, r, r + th, c, c + 20.0))            # 上
                m = np.maximum(m, _rect(y, x, r + hgt / 2 - th / 2,
                                        r + hgt / 2 + th / 2, c, c + 15.0))       # 中
                m = np.maximum(m, _rect(y, x, r + hgt - th, r + hgt, c, c + 20.0))  # 下
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
        return img + gate * self._texture(dy, dx)


# --------------------------------------------------------------------------- #
# 撮像の模擬 と 拡大の手法                                                       #
# --------------------------------------------------------------------------- #
def down_box(hr, s):
    """撮像の模擬 —— ``s x s`` の面積平均(帯域制限)+ 間引き。台帳 op を 2-D で使う。"""
    return np.asarray(fs.ledger.volume_downsample(hr[None], (1, s, s), mode="mean"))[0]


def up_spline(lr, s, order):
    """スプライン拡大。``order`` 0=nearest / 1=bilinear / 3=bicubic / 5=五次。

    ``vol_resize`` は ``grid_mode=True``(セル意味論)なので、``down_box`` の
    ブロックと**格子が揃う**。半画素ずれていないことは末尾の自己検査で確かめる。
    """
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


def up_sharpened(lr, s, strength=0.9):
    """bicubic に鮮鋭化を掛ける —— 「良く見える」側の代表。"""
    return sharpen(up_spline(lr, s, 3), strength)


def sharpen(img, strength):
    return np.asarray(fs.op.unsharp(np.clip(img, 0.0, 1.0), a=strength))


def up_ibp(lr, s, iters=12, gain=1.0):
    """反復逆投影 —— **順モデル(面積平均)を知っている**ことだけを使う。

    情報を増やしているのではなく、既知のぼけを戻している。低解像側のナイキスト
    より細かい成分は順モデルの零空間に落ちているので、何回回しても戻らない。
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
        xs = np.arange(c0, c0 + BAR_W, dtype=np.float64)
        out[gi] = 2.0 * abs(np.mean(prof[c0:c0 + BAR_W] * np.exp(-2j * np.pi * xs / p)))
    return out


def modulation(img, ref_amp):
    """真値の振幅で割った変調度。1.0 = 真値どおり、0.0 = 縞が消えた。"""
    return bar_amplitudes(img) / ref_amp


def resolved_period(mod, threshold=0.20):
    """変調度が閾値以上で残っている**最も細かい周期** [真値画素]。"""
    ok = [p for p, m in zip(BAR_PERIODS, mod) if m >= threshold]
    return min(ok) if ok else 0


def fid(a, b):
    """(PSNR [dB], SSIM)。縁 16 画素は比較から外す(FFT の周期性と外挿を避ける)。"""
    a = np.clip(np.asarray(a, np.float64), 0.0, 1.0)[16:-16, 16:-16]
    b = np.clip(np.asarray(b, np.float64), 0.0, 1.0)[16:-16, 16:-16]
    return float(fs.psnr(a, b, data_range=1.0)), float(fs.ssim(a, b, data_range=1.0))


def bar_row(label, values, width=20):
    return f"  {label:>{width}}" + "".join(f"{v:>7.2f}" for v in values)


# --------------------------------------------------------------------------- #
# 複数フレームの撮像 —— レンズのぼけ + 点標本化                                   #
# --------------------------------------------------------------------------- #
def optical_blur(hr, sigma_hr):
    """σ [真値画素] のガウスぼけ。``vol_fft_lowpass`` の cutoff = 1/(2 pi sigma)。"""
    cutoff = 1.0 / (2.0 * np.pi * sigma_hr)
    return np.asarray(fs.ledger.vol_fft_lowpass(hr[None], cutoff))[0]


def capture(scene, s, sigma_lr, ddy=0.0, ddx=0.0):
    """1 枚撮る。標本位置は ``i*s + (s-1)/2 + ddy``(drizzle の格子中心の規約)。

    この ``(s-1)/2`` を落とすと、合成した像が真値に対して半画素ずれる ——
    例外は出ず、PSNR だけが静かに落ちる。
    """
    hr = scene.render((s - 1) / 2.0 + ddy, (s - 1) / 2.0 + ddx)
    blur = optical_blur(hr, sigma_lr * s)
    return np.asarray(fs.ledger.volume_downsample(blur[None], (1, s, s), mode="stride"))[0]


def band_limited_truth(scene, s, sigma_lr):
    """レンズを通った像を真値の格子で完全に標本化したもの = 合成が到達しうる上限。"""
    return optical_blur(scene.render(0.0, 0.0), sigma_lr * s)


def dither_offsets(n_frames, s, seed=3):
    """1 低解像画素を ``m x m`` に割る格子 + 微小ジッタ。単位は真値画素。"""
    m = int(round(np.sqrt(n_frames)))
    rng = np.random.default_rng(seed)
    offs = [(0.0, 0.0)]
    for a in range(m):
        for b in range(m):
            if a == 0 and b == 0:
                continue
            offs.append((s * a / m + rng.uniform(-0.12, 0.12),
                         s * b / m + rng.uniform(-0.12, 0.12)))
    return offs, m


def true_shifts(offs, s):
    """drizzle の ``shifts`` = フレームの中身が基準からどれだけずれているか。"""
    return np.array([[-dy / s, -dx / s] for dy, dx in offs])


def estimate_shifts(frames, window=48):
    """相互相関でフレーム 0 に対するずれを測る。→ ``(N, 2)`` [低解像画素]。

    ★ ``fs.ledger.piv_cross_correlate`` は ``(flow, info)`` の **flow だけ**を返す
    (道具の穴 (d))。``flow, info = ...`` と書くと ``(2, R, C)`` が第 1 軸で開かれ、
    ``flow`` が dy 成分だけになる —— 例外は出ず、値だけが嘘になる。
    ★ 窓によっては NaN が返る(道具の穴 (h))ので ``nanmedian`` で集約する。
    """
    out = np.zeros((len(frames), 2))
    for k in range(1, len(frames)):
        flow = np.asarray(fs.ledger.piv_cross_correlate(frames[0], frames[k],
                                                        window=window, overlap=0.5))
        out[k, 0] = float(np.nanmedian(flow[0]))
        out[k, 1] = float(np.nanmedian(flow[1]))
    return out


def drizzle_image(frames, shifts, scale, pixfrac):
    """``(sci, wht)`` から**見るための画像**を作る。換算は道具の穴 (e)。"""
    sci, wht = fs.astrostack.drizzle_resample(list(frames), shifts=shifts,
                                              scale=scale, pixfrac=pixfrac)
    cover = wht > 1e-9
    img = np.zeros_like(sci)
    img[cover] = sci[cover] / wht[cover] * (pixfrac * scale) ** 2
    return img, wht


# --------------------------------------------------------------------------- #
def main():
    t_start = time.perf_counter()
    scene = Scene()
    truth = scene.render(0.0, 0.0)
    ref_amp = bar_amplitudes(truth)

    print("=== 0. 真値 —— 何を物差しにするか ===")
    print(f"  {N}x{N}、値域 [{truth.min():.3f}, {truth.max():.3f}]"
          f"(飽和なし = 縮小も拡大も線形のまま比べられる)")
    print(f"  中身: 正弦バー群 {BAR_PERIODS} 真値画素 / 点の対 {POINT_SEPS} 画素間隔 /")
    print("        文字風(太さ 4 と 2 画素)/ 1/f 型のテクスチャ")
    print(f"  真値で測ったバー振幅 {np.array2string(ref_amp, precision=3)}"
          f"(設計値 {BAR_AMP} = 物差しとして使える)")

    print("\n=== 1. 単一画像の拡大 —— bicubic の零点を上回れるか ===")
    print("  撮像の模擬 = s x s の面積平均(アンチエイリアスあり)。戻して真値と比べる。")
    methods = (
        ("nearest", lambda lr, s: up_spline(lr, s, 0)),
        ("bilinear", lambda lr, s: up_spline(lr, s, 1)),
        ("bicubic(零点)", lambda lr, s: up_spline(lr, s, 3)),
        ("五次スプライン", lambda lr, s: up_spline(lr, s, 5)),
        ("Lanczos-3(自前)", lambda lr, s: up_lanczos(lr, s)),
        ("bicubic+鮮鋭化", lambda lr, s: up_sharpened(lr, s, 0.9)),
        ("IBP(順モデル既知)", lambda lr, s: up_ibp(lr, s)),
    )
    recon = {}
    print(f"  {'倍率':>4}{'手法':>20}{'PSNR [dB]':>12}{'零点差':>10}"
          f"{'SSIM':>9}{'零点差':>10}")
    worst_kernel_gain = -9.9
    for s in (2, 3, 4):
        lr = down_box(truth, s)
        for name, fn in methods:
            recon[(s, name)] = fn(lr, s)
        null_p, null_s = fid(truth, recon[(s, "bicubic(零点)")])
        for name, _fn in methods:
            p, ss = fid(truth, recon[(s, name)])
            print(f"  {s:>4}{name:>20}{p:>12.3f}{p - null_p:+10.3f}"
                  f"{ss:>9.4f}{ss - null_s:+10.4f}")
            if name in ("nearest", "bilinear", "五次スプライン", "Lanczos-3(自前)"):
                worst_kernel_gain = max(worst_kernel_gain, p - null_p)
        print(f"       低解像 {lr.shape[0]}x{lr.shape[1]}、"
              f"低解像側のナイキスト = 周期 {2 * s} 真値画素")
    print(f"  → 補間核を替えて稼げた最大は {worst_kernel_gain:+.3f} dB。**上回れない**。")
    print("     鮮鋭化は倍率 2 で -1.57 dB。倍率 3・4 では ±0.1 dB しか動かないが、")
    print("     それは元がぼけているほど「盛った」ぶんが誤差に埋もれるからで、")
    print("     良くなったのではない(節 2 と節 3 でそこを分ける)。")
    print("     IBP だけが別の理由で動く —— 補間の工夫ではなく順モデルを知っている。")

    print("\n=== 2. 分解能の実測 —— 縞はどこまで分離するか(変調度)===")
    s = 4
    print(f"  倍率 {s}、低解像側のナイキスト = 周期 {2 * s} 真値画素。"
          "1.00 = 真値どおり、0.00 = 縞が消えた。")
    print(f"  {'手法':>20}" + "".join(f"{p:>7}" for p in BAR_PERIODS) + f"{'分離限界':>10}")
    print(bar_row("真値", np.ones(len(BAR_PERIODS))) + f"{min(BAR_PERIODS):>10}")
    mods = {}
    for name, _fn in methods:
        m = modulation(recon[(s, name)], ref_amp)
        mods[name] = m
        print(bar_row(name, m) + f"{resolved_period(m):>10}")
    print("  → 周期 8(= 2s)より細かい列は、鮮鋭化を除いてどれも 0 のまま。")
    print("     IBP は周期 12〜24 の**落ちていた変調を戻す**(0.78 → 0.96 等)が、")
    print("     周期 6 以下は 1 本も戻らない —— 順モデルの零空間に落ちているため。")
    print("     鮮鋭化は縞が消えている列まで持ち上げる。これは分解能ではなく")
    print("     **無い縞を作っている**ので、この行を根拠にしてはいけない。")
    p_ibp = fid(truth, recon[(s, "IBP(順モデル既知)")])[0]
    p_nul = fid(truth, recon[(s, "bicubic(零点)")])[0]
    print(f"  ★ 同じ IBP を PSNR で見ると {p_ibp - p_nul:+.3f} dB —— "
          "**改善がほとんど見えない**。")
    print("     忠実度の指標は「戻った」ことを検出しない。分解能は別に測る必要がある。")

    print("\n=== 3. 「鮮鋭に見える」と「情報が増えた」は別 ===")
    s2 = 2
    base = up_spline(down_box(truth, s2), s2, 3)
    g_truth = gradient_energy(truth)
    print(f"  倍率 {s2}、bicubic に鮮鋭化を段階的に掛ける。真値の勾配エネルギー"
          f" = {g_truth:.5f}")
    print(f"  {'鮮鋭化の強さ':>14}{'勾配エネルギー':>16}{'真値比':>9}"
          f"{'PSNR [dB]':>12}{'SSIM':>9}")
    ladder = []
    for strength in (None, 0.1, 0.3, 0.5, 0.7, 0.9):
        out = base if strength is None else sharpen(base, strength)
        g = gradient_energy(out)
        p, ss = fid(truth, out)
        ladder.append((strength, g, p, ss))
        tag = "なし(零点)" if strength is None else f"a = {strength:.1f}"
        print(f"  {tag:>14}{g:>16.5f}{g / g_truth:>9.2f}{p:>12.3f}{ss:>9.4f}")
    g0, p0_, s0_ = ladder[0][1], ladder[0][2], ladder[0][3]
    gL, pL, sL = ladder[-1][1], ladder[-1][2], ladder[-1][3]
    print(f"  → 一番強く掛けたところで勾配エネルギーは真値と一致する(比 {gL / g_truth:.2f})のに、")
    print(f"     PSNR は {pL - p0_:+.2f} dB、SSIM は {sL - s0_:+.4f}。**逆を向く**。")
    print(f"     弱く掛けた a=0.1〜0.5 の帯では PSNR は下がるのに SSIM は上がる ——")
    print("     3 つの数字が三様なので、1 つだけ出す報告はいくらでも作れる。")

    print("\n=== 4. 複数フレーム —— 標本化が足りているかで結論が変わる ===")
    print("  撮像の模擬 = レンズのぼけ(σ)+ 点標本化。副画素ずれのあるフレームを")
    print("  drizzle で合成する。比較の基準は「レンズを通った像を真値の格子で")
    print("  完全に標本化したもの」= どんな合成でもこれ以上にはならない上限。")
    multi = {}
    for label, sigma_lr in (("標本化不足", 0.30), ("十分に標本化", 0.85)):
        blt = band_limited_truth(scene, s, sigma_lr)
        single = up_spline(capture(scene, s, sigma_lr), s, 3)
        p0, ss0 = fid(blt, single)
        print(f"\n  --- {label}(σ = {sigma_lr:.2f} 低解像画素、"
              f"FWHM {2.355 * sigma_lr:.2f} 低解像画素)---")
        print(f"  {'合成':>22}{'枚数':>5}{'pixfrac':>9}{'PSNR [dB]':>12}"
              f"{'単一比':>9}{'SSIM':>9}{'ずれ推定誤差':>13}")
        print(f"  {'単一画像 bicubic':>22}{1:>5}{'—':>9}{p0:>12.3f}"
              f"{0.0:>+9.2f}{ss0:>9.4f}{'—':>13}")
        for n_frames in (4, 9, 16):
            offs, m = dither_offsets(n_frames, s)
            frames = [capture(scene, s, sigma_lr, dy, dx) for dy, dx in offs]
            tsh = true_shifts(offs, s)
            est = estimate_shifts(frames)
            err = float(np.max(np.abs(est - tsh)))
            pixfrac = max(0.4, 1.2 / m)
            img, wht = drizzle_image(frames, est, s, pixfrac)
            p, ss = fid(blt, img)
            print(f"  {'drizzle(推定ずれ)':>22}{n_frames:>5}{pixfrac:>9.3f}"
                  f"{p:>12.3f}{p - p0:>+9.2f}{ss:>9.4f}{err:>13.4f}")
            if n_frames == 16:
                ideal, _w = drizzle_image(frames, tsh, s, pixfrac)
                pi_, si_ = fid(blt, ideal)
                print(f"  {'drizzle(真のずれ)':>22}{n_frames:>5}{pixfrac:>9.3f}"
                      f"{pi_:>12.3f}{pi_ - p0:>+9.2f}{si_:>9.4f}{0.0:>13.4f}")
                naive = up_spline(np.mean(frames, axis=0), s, 3)
                pn, sn = fid(blt, naive)
                print(f"  {'ずれを無視して平均':>22}{n_frames:>5}{'—':>9}"
                      f"{pn:>12.3f}{pn - p0:>+9.2f}{sn:>9.4f}{'—':>13}")
                multi[label] = (img, single, blt, p - p0,
                                float(wht[20:-20, 20:-20].min()))
        img16, single1, blt, gain, wmin = multi[label]
        print(f"  {'周期 [真値画素]':>22}" + "".join(f"{p:>7}" for p in BAR_PERIODS))
        print(bar_row("上限(帯域制限)", modulation(blt, ref_amp), 22))
        print(bar_row("単一画像 bicubic", modulation(single1, ref_amp), 22))
        print(bar_row("drizzle 16 枚", modulation(img16, ref_amp), 22))
        print(f"  (被覆の最小 wht = {wmin:.3f} —— 0 なら穴が空いている)")
    print("\n  → 標本化不足では drizzle がナイキスト(周期 8)より細かい列を")
    print("     0 から立ち上げる。これは本当に増えている。")
    print("  → 十分に標本化されていると PSNR は上がるのに、**分解能の列は動かない**。")
    print("     既に見えない大きさの誤差がさらに小さくなっただけで、情報ではない。")
    print("     PSNR だけ見ていると、この 2 つを取り違える。")
    print("  → ずれを無視して平均すると像は鈍る。同じずれを解像度に変えるのが drizzle。")
    print("  → 標本化不足の側は**位置合わせも難しい**(推定誤差が数倍)。")
    print("     増やせる条件は、同時に測りにくい条件でもある。")

    print("\n=== 5. ずれの符号を間違えると、例外も出さずに二重像になる ===")
    sigma_lr = 0.30
    blt = band_limited_truth(scene, s, sigma_lr)
    offs, m = dither_offsets(16, s)
    frames = [capture(scene, s, sigma_lr, dy, dx) for dy, dx in offs]
    est = estimate_shifts(frames)
    pixfrac = max(0.4, 1.2 / m)
    good, _w = drizzle_image(frames, est, s, pixfrac)
    bad, _w = drizzle_image(frames, -est, s, pixfrac)
    zero, wz = drizzle_image(frames, np.zeros_like(est), s, pixfrac)
    for lab, im in (("正しい符号", good), ("符号を反転", bad), ("ずれを渡さない", zero)):
        p, ss = fid(blt, im)
        print(f"  {lab:>16}{p:>12.3f} dB{ss:>10.4f}")
    print(f"  (「渡さない」は被覆も崩れる: 最小 wht = {wz[20:-20, 20:-20].min():.3f})")
    print("  → 反転しても例外は出ない。数字を並べないと気づけない。")

    print("\n=== 6. 速度(この機械での実測)===")
    lr = down_box(truth, 4)
    print(f"  入力 {lr.shape[0]}x{lr.shape[1]} → 出力 {N}x{N}(倍率 4、float64)")
    for lab, fn in (("nearest", lambda: up_spline(lr, 4, 0)),
                    ("bilinear", lambda: up_spline(lr, 4, 1)),
                    ("bicubic", lambda: up_spline(lr, 4, 3)),
                    ("五次スプライン", lambda: up_spline(lr, 4, 5)),
                    ("Lanczos-3(自前)", lambda: up_lanczos(lr, 4)),
                    ("bicubic+鮮鋭化", lambda: up_sharpened(lr, 4)),
                    ("IBP 12 回", lambda: up_ibp(lr, 4))):
        t0 = time.perf_counter()
        fn()
        print(f"  {lab:<20}{1e3 * (time.perf_counter() - t0):>9.1f} ms")
    t0 = time.perf_counter()
    drizzle_image(frames, est, 4, pixfrac)
    print(f"  {'drizzle 16 枚':<20}{1e3 * (time.perf_counter() - t0):>9.1f} ms"
          "  (120x120 x16 → 480x480)")
    t0 = time.perf_counter()
    estimate_shifts(frames)
    print(f"  {'ずれ推定 15 対':<20}{1e3 * (time.perf_counter() - t0):>9.1f} ms"
          "  (相互相関、窓 48)")

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

    # 面積平均 → nearest 拡大 で格子が揃っている(半画素ずれていない)
    blocky = np.repeat(np.repeat(np.arange(9.0).reshape(3, 3) / 9.0, 4, 0), 4, 1)
    assert np.allclose(up_spline(down_box(blocky, 4), 4, 0), blocky, atol=1e-12), \
        "面積平均と拡大の格子がずれている(半画素のずれ)"

    # (1) 補間核の工夫では零点を上回れない —— 結論そのものを検査に固定する
    for s_ in (2, 3, 4):
        p_null = fid(truth, recon[(s_, "bicubic(零点)")])[0]
        for name in ("nearest", "bilinear", "五次スプライン", "Lanczos-3(自前)"):
            assert fid(truth, recon[(s_, name)])[0] - p_null < 0.20, \
                f"倍率 {s_} で {name} が零点を 0.2 dB 超えた —— 結論を書き換えること"

    # (2) IBP は分解能を戻すが PSNR はほとんど動かない
    assert mods["IBP(順モデル既知)"][2] - mods["bicubic(零点)"][2] > 0.10, \
        "IBP が周期 12 の変調を戻していない(順モデルの向きを疑う)"
    assert abs(p_ibp - p_nul) < 0.5, \
        "IBP の PSNR が大きく動いた —— 『指標が検出しない』という結論を書き換えること"

    # (3) ナイキストより細かい縞は、単一画像ではどの手法でも戻らない(鮮鋭化を除く)
    fine = [i for i, p in enumerate(BAR_PERIODS) if p < 2 * 4]
    for name in ("bicubic(零点)", "五次スプライン", "Lanczos-3(自前)", "IBP(順モデル既知)"):
        assert max(mods[name][i] for i in fine) < 0.20, \
            f"{name} がナイキストより細かい縞を作った(偽の情報を疑う)"

    # (4) 見た目と忠実度が逆を向く
    assert gL > g0 and pL < p0_ and sL < s0_, "鮮鋭化で二つの指標が逆を向かなかった"
    assert gL / g_truth > 0.95, "鮮鋭化しても勾配エネルギーが真値に届かなかった"
    assert any(g > g0 and p < p0_ and ss > s0_ for _st, g, p, ss in ladder[1:]), \
        "PSNR が下がるのに SSIM が上がる帯が消えた(3 指標が三様、という結論の根拠)"

    # (5) drizzle: 単一フレーム・ずれ 0 なら総フラックスが保存する
    sci, wht = fs.astrostack.drizzle_resample([frames[0]], shifts=None,
                                              scale=4, pixfrac=1.0)
    assert abs(sci.sum() / frames[0].sum() - 1.0) < 1e-9, "drizzle が総フラックスを保存しない"
    assert abs(float(wht[40, 40]) - 1.0) < 1e-12, "pixfrac=1・ずれ 0 で内部の重みが 1 でない"
    # 階調の換算式 (pixfrac*scale)^2 —— 道具の穴 (e)
    one = np.full((24, 24), 0.4)
    for pf, sc_ in ((1.0, 2), (0.5, 2), (0.4, 2)):
        im, _w = drizzle_image([one], None, sc_, pf)
        assert abs(float(im[10:-10, 10:-10].mean()) - 0.4) < 1e-9, \
            f"pixfrac={pf}, scale={sc_} で階調が元に戻らない"

    # (6) 複数フレームは「標本化が足りていないとき**だけ**」情報を増やす
    gain_under = multi["標本化不足"][3]
    img_u, single_u, _blt_u, _g, wmin_u = multi["標本化不足"]
    img_w, single_w, _blt_w, _g2, wmin_w = multi["十分に標本化"]
    assert wmin_u > 0.0 and wmin_w > 0.0, "drizzle の被覆に穴がある(pixfrac が小さすぎ)"
    assert gain_under > 10.0, f"標本化不足で複数フレームの利得が出ない({gain_under:.2f} dB)"
    fine_u = max(modulation(img_u, ref_amp)[i] for i in fine)
    fine_u0 = max(modulation(single_u, ref_amp)[i] for i in fine)
    assert fine_u > 0.25 and fine_u > 3.0 * fine_u0, \
        f"標本化不足でもナイキスト超えの縞が立たない({fine_u0:.2f} → {fine_u:.2f})"
    # 十分に標本化されている側は、分解能が動かない(PSNR は上がってもよい)
    d_well = np.max(np.abs(modulation(img_w, ref_amp) - modulation(single_w, ref_amp)))
    assert d_well < 0.05, \
        f"十分標本化の側で分解能が動いた({d_well:.3f}) —— 結論を書き換えること"

    # (7) 符号を間違えると壊れる(例外は出ない)
    assert fid(blt, good)[0] - fid(blt, bad)[0] > 5.0, \
        "ずれの符号を反転しても結果が変わらない —— 合成が効いていない疑い"

    print(f"\n所要 {time.perf_counter() - t_start:.1f} 秒")
    print("PASS")


if __name__ == "__main__":
    main()
